"""Local-vector/Groq-generation RAG service for P&M Solutions."""
from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
from collections.abc import AsyncGenerator, Iterable

import httpx
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.prompts import PM_CHAT_SYSTEM_PROMPT
from app.core.settings import settings

# The reference chat resolves the response language from the visitor's message.
SUPPORTED_LANGUAGES = frozenset({"en", "es", "pt"})
ACTIVE_LANGUAGES = SUPPORTED_LANGUAGES
AUTO_LANGUAGE = "auto"
SUPPORTED_EXTENSIONS = frozenset({".pdf", ".md", ".txt"})
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 150
EMBEDDING_BATCH_SIZE = 64
LOCAL_EMBEDDING_MODEL = "local-hashed-ngrams-v1"
LOCAL_EMBEDDING_DIMENSIONS = 768

GREETING_MESSAGES = {
    "en": "Hello. I’m the P&M Solutions chatbot. Ask me about our company, solutions, or how to contact us.",
    "es": "Hola. Soy el chatbot de P&M Solutions. Preguntame sobre la empresa, nuestras soluciones o cómo contactarnos.",
    "pt": "Olá. Sou o chatbot da P&M Solutions. Pergunte sobre a empresa, nossas soluções ou como entrar em contato.",
}
NO_CONTEXT_MESSAGES = {
    "en": "I don’t have that information in the current P&M Solutions knowledge base. Please use the contact form on this website for a direct answer.",
    "es": "No tengo esa información en la base de conocimiento actual de P&M Solutions. Usá el formulario de contacto del sitio para recibir una respuesta directa.",
    "pt": "Não tenho essa informação na base de conhecimento atual da P&M Solutions. Use o formulário de contato do site para receber uma resposta direta.",
}
OFF_TOPIC_MESSAGES = {
    "en": "I’m here to answer questions about P&M Solutions, our approved solutions, and how to contact us.",
    "es": "Estoy aquí para responder preguntas sobre P&M Solutions, nuestras soluciones aprobadas y cómo contactarnos.",
    "pt": "Estou aqui para responder perguntas sobre a P&M Solutions, nossas soluções aprovadas e como entrar em contato.",
}
ERROR_MESSAGES = {
    "en": "I’m having trouble connecting right now. Please try again or use the contact form on this website.",
    "es": "Estoy teniendo problemas para conectarme. Intentá nuevamente o usá el formulario de contacto del sitio.",
    "pt": "Estou com dificuldades para me conectar. Tente novamente ou use o formulário de contato do site.",
}

_THINK_OPEN = "<think>"
_THINK_CLOSE = "</think>"


def _suffix_prefix_length(value: str, marker: str) -> int:
    """Return the length of a suffix that may start a split marker."""
    for length in range(min(len(value), len(marker) - 1), 0, -1):
        if value.endswith(marker[:length]):
            return length
    return 0


class _ReasoningFilter:
    """Hide Qwen reasoning tags while preserving streamed answer text."""

    def __init__(self) -> None:
        self._pending = ""
        self._inside_reasoning = False

    def feed(self, text: str) -> str:
        self._pending += text
        output: list[str] = []
        while self._pending:
            marker = _THINK_CLOSE if self._inside_reasoning else _THINK_OPEN
            index = self._pending.find(marker)
            if index >= 0:
                if not self._inside_reasoning:
                    output.append(self._pending[:index])
                    self._inside_reasoning = True
                self._pending = self._pending[index + len(marker):]
                if marker == _THINK_CLOSE:
                    self._inside_reasoning = False
                continue

            possible_marker = _suffix_prefix_length(self._pending, marker)
            if self._inside_reasoning:
                self._pending = self._pending[-possible_marker:] if possible_marker else ""
            elif possible_marker:
                output.append(self._pending[:-possible_marker])
                self._pending = self._pending[-possible_marker:]
            else:
                output.append(self._pending)
                self._pending = ""
            break
        return "".join(output)

    def finish(self) -> str:
        """Flush ordinary text but never flush an unterminated thought."""
        if self._inside_reasoning:
            self._pending = ""
            return ""
        output = self._pending
        self._pending = ""
        return output


class UnsupportedLanguageError(ValueError):
    def __init__(self, language: str):
        self.language = language
        super().__init__(f"Unsupported language: {language}")


class ChatbotNotConfiguredError(RuntimeError):
    """Raised when the chatbot is enabled without a Groq key."""


def detect_language(text: str) -> str:
    """Detect the visitor's language without requiring a UI selector."""
    lowered = text.lower()
    scores = {"pt": 0, "es": 0, "en": 0}
    markers = {
        "pt": (" você ", " não ", " como ", " soluções", " empresa", " contato", " podem ", " para ", "ção", "ões", "á", "ã", "õ"),
        "es": (" qué ", " cómo ", " empresa", " soluciones", " contacto", " pueden ", " para ", "ción", "ñ", "¿", "¡"),
        "en": (" the ", " what ", " how ", " company", " solutions", " contact", " can ", " do ", " are ", " is "),
    }
    padded = f" {lowered} "
    for language, language_markers in markers.items():
        scores[language] = sum(padded.count(marker) for marker in language_markers)
    return max(scores, key=lambda item: scores[item]) if max(scores.values()) else "pt"


def resolve_language(language: str, query: str) -> str:
    normalized = language.lower().strip()
    if normalized == AUTO_LANGUAGE:
        return detect_language(query)
    return validate_language(normalized)


def validate_language(language: str) -> str:
    normalized = language.lower().strip()
    if normalized not in ACTIVE_LANGUAGES:
        raise UnsupportedLanguageError(normalized)
    return normalized


def is_greeting(query: str) -> bool:
    normalized = query.lower().strip().rstrip("!.?")
    return normalized in {
        "hi", "hello", "hey", "hola", "olá", "ola",
        "good morning", "good afternoon", "good evening",
        "buenos dias", "buenas tardes", "buenas noches",
        "bom dia", "boa tarde", "boa noite",
    }


def should_block_query(query: str) -> bool:
    indicators = (
        "weather", "recipe", "movie recommendation", "sports score", "bitcoin price",
        "latest news", "clima", "receta", "película", "pelicula", "marcador",
        "precio del bitcoin", "noticias", "previsão do tempo", "previsao do tempo",
        "receita", "filme", "placar", "preço do bitcoin", "preco do bitcoin",
    )
    lowered = query.lower()
    return any(indicator in lowered for indicator in indicators)


def _require_groq() -> tuple[str, str]:
    key = (settings.groq_api_key or "").strip()
    if not settings.enable_chatbot or not key:
        raise ChatbotNotConfiguredError("P&M chatbot is not configured.")
    return key, settings.groq_base_url.rstrip("/")


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _hashed_features(text: str) -> list[str]:
    normalized = re.sub(r"[^\wÀ-ÿ]+", " ", text.lower(), flags=re.UNICODE).strip()
    words = normalized.split()
    features = words + [f"{left}_{right}" for left, right in zip(words, words[1:])]
    for word in words:
        features.extend(word[index:index + 3] for index in range(max(0, len(word) - 2)))
    return features


def _embed_sync(values: list[str], prefix: str = "") -> list[list[float]]:
    """Build deterministic unit vectors without loading a neural model.

    The 768-slot contract is retained for pgvector compatibility. Stable hashing
    keeps document and query representations identical across processes.
    """
    result: list[list[float]] = []
    for value in values:
        vector = [0.0] * settings.embedding_dimensions
        for feature in _hashed_features(f"{prefix}{value}"):
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest, "big") % settings.embedding_dimensions
            vector[bucket] += 1.0
        norm = math.sqrt(sum(component * component for component in vector))
        if norm:
            vector = [component / norm for component in vector]
        result.append(vector)
    return result


def get_embeddings_sync(values: list[str]) -> list[list[float]]:
    return _embed_sync(values)


async def get_embeddings(texts: Iterable[str]) -> list[list[float]]:
    values = [text.strip() for text in texts if text.strip()]
    if not values:
        return []
    return get_embeddings_sync(values)


async def get_embedding(text: str) -> list[float]:
    if not text.strip():
        return []
    return get_embeddings_sync([text.strip()])[0]


async def retrieve_documents(db: AsyncSession, query_vector: list[float], language: str):
    from app.models.rag_documents import RagDocument

    result = await db.execute(
        select(RagDocument)
        .where(RagDocument.language == language)
        .where(RagDocument.active.is_(True))
        .order_by(RagDocument.embedding.cosine_distance(query_vector))
        .limit(settings.retrieval_k)
    )
    return result.scalars().all()


def _context(docs) -> str:
    return "\n\n---\n\n".join(
        f"Source: {doc.source}\n{doc.content}" for doc in docs
    )


def _history_messages(history) -> list[dict[str, str]]:
    return [
        {"role": message.role, "content": message.content}
        for message in (history or [])
    ]


def _language_instruction(language: str) -> str:
    return {
        "pt": "Brazilian Portuguese",
        "es": "Spanish",
        "en": "English",
    }[language]


def _chat_payload(query: str, context: str, history, language: str = "pt") -> dict:
    messages = [{
        "role": "system",
        "content": PM_CHAT_SYSTEM_PROMPT.format(
            context=context,
            response_language=_language_instruction(language),
        ),
    }]
    messages.extend(_history_messages(history))
    messages.append({"role": "user", "content": query})
    return {
        "model": settings.primary_llm,
        "messages": messages,
        "temperature": 0.2,
        "stream": True,
        "reasoning_format": "hidden",
    }


async def stream_groq_chat(
    query: str, context: str, history, language: str = "pt"
) -> AsyncGenerator[str, None]:
    api_key, base_url = _require_groq()
    reasoning_filter = _ReasoningFilter()
    emitted_visible_text = False
    async with httpx.AsyncClient(timeout=settings.chat_timeout_seconds) as client, client.stream(
        "POST",
        f"{base_url}/chat/completions",
        headers=_headers(api_key),
        json=_chat_payload(query, context, history, language),
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                event = json.loads(payload)
            except (ValueError, TypeError):
                continue
            delta = (event.get("choices") or [{}])[0].get("delta", {}).get("content")
            if delta:
                visible = reasoning_filter.feed(delta)
                if visible:
                    emitted_visible_text = True
                    yield visible
        visible = reasoning_filter.finish()
        if visible:
            emitted_visible_text = True
            yield visible
        if not emitted_visible_text:
            raise RuntimeError("Groq returned no visible answer.")


async def stream_chat_response(
    query: str,
    language: str,
    db: AsyncSession,
    chat_history=None,
) -> AsyncGenerator[str, None]:
    selected_language = resolve_language(language, query)
    if is_greeting(query) and not chat_history:
        yield GREETING_MESSAGES[selected_language]
        return
    if should_block_query(query):
        yield OFF_TOPIC_MESSAGES[selected_language]
        return

    try:
        query_vector = await get_embedding(query)
        # The approved source is Portuguese; the model translates supported facts
        # when the visitor writes in English or Spanish.
        docs = await retrieve_documents(db, query_vector, "pt")
        if not docs:
            yield NO_CONTEXT_MESSAGES[selected_language]
            return
        reply_parts: list[str] = []
        async for chunk in stream_groq_chat(query, _context(docs), chat_history, selected_language):
            reply_parts.append(chunk)
            yield chunk
    except UnsupportedLanguageError:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"P&M chatbot error: {type(exc).__name__}: {exc}")
        yield ERROR_MESSAGES[selected_language]


async def get_chat_response(query: str, language: str, db: AsyncSession, chat_history=None) -> str:
    chunks: list[str] = []
    async for chunk in stream_chat_response(query, language, db, chat_history):
        chunks.append(chunk)
    return "".join(chunks)


def extract_document_text(file_bytes: bytes, filename: str) -> str:
    if len(file_bytes) > MAX_DOCUMENT_BYTES:
        raise ValueError("Document exceeds the 20 MB limit.")
    extension = os.path.splitext(filename)[1].lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only PDF, Markdown, and TXT documents are supported.")
    if extension == ".pdf":
        if not file_bytes.startswith(b"%PDF-"):
            raise ValueError("PDF content does not match its extension.")
        reader = PdfReader(io.BytesIO(file_bytes))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Text documents must be valid UTF-8.") from exc
    text = text.strip()
    if not text:
        raise ValueError("Document contains no extractable text.")
    return text


def split_text(text: str) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
            if boundary > start + CHUNK_SIZE // 2:
                end = boundary + (1 if text[boundary] == "\n" else 2)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


async def process_and_embed_document(
    file_bytes: bytes,
    filename: str,
    language: str,
    db: AsyncSession,
) -> int:
    from app.models.rag_documents import RagDocument

    selected_language = validate_language(language)
    text = extract_document_text(file_bytes, filename)
    chunks = split_text(text)
    vectors: list[list[float]] = []
    for index in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        vectors.extend(await get_embeddings(chunks[index:index + EMBEDDING_BATCH_SIZE]))
    for chunk, vector in zip(chunks, vectors, strict=True):
        db.add(RagDocument(
            source=os.path.basename(filename),
            content=chunk,
            language=selected_language,
            embedding=vector,
            active=True,
        ))
    await db.commit()
    return len(chunks)
