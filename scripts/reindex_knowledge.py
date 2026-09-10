"""Replace one indexed knowledge source with current local embeddings.

Use only after reviewing the source and before activating a representation
change. This script deletes and rebuilds rows for the selected source only.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import delete, func, select

from app.core.database import get_session
from app.models.rag_documents import RagDocument
from app.services.ai_service import process_and_embed_document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        nargs="?",
        default="knowledge/p-m-solutions-general-knowledge.pt-BR.md",
        help="Path to the approved knowledge source",
    )
    parser.add_argument("--language", default="pt", choices=("pt", "es", "en"))
    return parser.parse_args()


async def reindex(source_path: Path, language: str) -> None:
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    source_name = source_path.name
    async for db in get_session():
        before = await db.scalar(
            select(func.count()).select_from(RagDocument).where(RagDocument.source == source_name)
        )
        await db.execute(delete(RagDocument).where(RagDocument.source == source_name))
        await db.commit()
        inserted = await process_and_embed_document(
            source_path.read_bytes(), source_name, language, db
        )
        after = await db.scalar(
            select(func.count()).select_from(RagDocument).where(RagDocument.source == source_name)
        )
        print(f"source={source_name}")
        print(f"replaced_rows={before}")
        print(f"inserted_chunks={inserted}")
        print(f"source_rows_after={after}")
        return


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(reindex(Path(arguments.source), arguments.language))
