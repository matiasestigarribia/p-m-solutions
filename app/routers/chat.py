"""Public P&M Solutions chatbot API."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import enforce_chat_rate_limit
from app.core.settings import settings
from app.schemas.chat import ChatRequestSchema
from app.services.ai_service import (
    ChatbotNotConfiguredError,
    UnsupportedLanguageError,
    get_chat_response,
    stream_chat_response,
)

router = APIRouter()


async def _store_incoming_message(db: AsyncSession, payload: ChatRequestSchema):
    """Persist every accepted client message before response generation."""
    from app.models.chat_logs import ChatLog

    chat_log = ChatLog(
        user_message=payload.message,
        bot_reply="",
        language=payload.language.lower().strip(),
    )
    try:
        db.add(chat_log)
        await db.commit()
        return chat_log
    except Exception as exc:  # noqa: BLE001
        print(f"P&M chat message logging failed: {type(exc).__name__}: {exc}")
        try:
            await db.rollback()
        except Exception as rollback_exc:  # noqa: BLE001
            print(f"P&M chat message rollback failed: {type(rollback_exc).__name__}: {rollback_exc}")
        return None


async def _store_bot_reply(db: AsyncSession, chat_log, reply: str) -> None:
    """Attach the generated, fallback, or error reply to the received message."""
    if chat_log is None:
        return
    try:
        chat_log.bot_reply = reply
        db.add(chat_log)
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        print(f"P&M chat reply logging failed: {type(exc).__name__}: {exc}")
        try:
            await db.rollback()
        except Exception as rollback_exc:  # noqa: BLE001
            print(f"P&M chat reply rollback failed: {type(rollback_exc).__name__}: {rollback_exc}")


def _ensure_enabled() -> None:
    if not settings.enable_chatbot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot is unavailable.")
    if not settings.enable_database:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Chatbot knowledge base is unavailable.")


async def get_chat_session():
    _ensure_enabled()
    from app.core.database import get_session

    async for session in get_session():
        yield session


@router.post("/", status_code=status.HTTP_200_OK)
async def ask_chatbot(
    request: Request,
    payload: ChatRequestSchema,
    db: Annotated[AsyncSession, Depends(get_chat_session)],
):
    _ensure_enabled()
    enforce_chat_rate_limit(request)
    chat_log = await _store_incoming_message(db, payload)
    try:
        reply = await get_chat_response(
            payload.message, payload.language, db, payload.chat_history
        )
        await _store_bot_reply(db, chat_log, reply)
        return {"reply": reply}
    except UnsupportedLanguageError as exc:
        await _store_bot_reply(
            db,
            chat_log,
            "O idioma solicitado ainda não está disponível no chatbot da P&M Solutions.",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "unsupported_language", "supported_languages": sorted({"en", "es", "pt"}), "requested_language": exc.language},
        ) from exc
    except ChatbotNotConfiguredError as exc:
        await _store_bot_reply(
            db,
            chat_log,
            "O chatbot está temporariamente indisponível. Use o formulário de contato do site.",
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Chatbot is not configured.") from exc


@router.post("/stream/")
async def stream_chatbot(
    request: Request,
    payload: ChatRequestSchema,
    db: Annotated[AsyncSession, Depends(get_chat_session)],
):
    _ensure_enabled()
    enforce_chat_rate_limit(request)
    chat_log = await _store_incoming_message(db, payload)

    async def events():
        reply_parts: list[str] = []
        try:
            async for chunk in stream_chat_response(
                payload.message,
                payload.language,
                db,
                payload.chat_history,
            ):
                reply_parts.append(chunk)
                safe = chunk.replace("\n", "\\n")
                yield f"data: {safe}\n\n"
        except UnsupportedLanguageError as exc:
            reply_parts.append(
                "O idioma solicitado ainda não está disponível no chatbot da P&M Solutions."
            )
            yield f"data: [ERROR] Unsupported language: {exc.language}\n\n"
        except ChatbotNotConfiguredError:
            reply_parts.append(
                "O chatbot está temporariamente indisponível. Use o formulário de contato do site."
            )
            yield "data: [ERROR] Chatbot is not configured.\n\n"
        except (RuntimeError, ValueError):
            reply_parts.append(
                "O chatbot está temporariamente indisponível. Use o formulário de contato do site."
            )
            yield "data: [ERROR] The chatbot is temporarily unavailable.\n\n"
        finally:
            await _store_bot_reply(db, chat_log, "".join(reply_parts).strip())
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
