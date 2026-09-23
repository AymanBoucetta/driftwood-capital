"""Chunk Markdown filings, create OpenAI embeddings, and upsert document_chunks.

Run from backend/ after reviewing the one-chunk result:
    uv run python ../data/chunk_and_embed.py --test-one
    uv run python ../data/chunk_and_embed.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import tiktoken
from docling.chunking import HierarchicalChunker, HybridChunker
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
from openai import AsyncOpenAI

from app.config import settings
from app.database.supabase import get_service_role_client

DATA_DIR = Path(__file__).resolve().parent
MARKDOWN_DIR = DATA_DIR / "markdown"
MANIFEST_PATH = MARKDOWN_DIR / "manifest.json"
CHUNK_TOKEN_LIMIT = 6000
EMBEDDING_BATCH_SIZE = 32
CHUNK_NAMESPACE = uuid.UUID("f2a8f3f4-2a31-4d1c-9d2d-3a15c82d1e11")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--test-one",
        action="store_true",
        help="Embed and upsert only the first chunk of the first filing.",
    )
    return parser.parse_args()


def load_manifest() -> list[dict[str, Any]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return manifest.get("filings", [])


def create_chunker() -> tuple[HierarchicalChunker, HybridChunker]:
    encoding = tiktoken.encoding_for_model(settings.openai_embedding_model)
    tokenizer = OpenAITokenizer(tokenizer=encoding, max_tokens=CHUNK_TOKEN_LIMIT)
    return (
        HierarchicalChunker(always_emit_headings=True),
        HybridChunker(
            tokenizer=tokenizer,
            repeat_table_header=True,
            merge_peers=True,
            always_emit_headings=True,
        ),
    )


def get_page(chunk: Any) -> str | None:
    pages = {
        str(provenance.page_no)
        for item in chunk.meta.doc_items
        for provenance in item.prov
        if provenance.page_no is not None
    }
    return ",".join(sorted(pages, key=int)) if pages else None


def chunk_metadata(chunk: Any, filing: dict[str, Any], hierarchical_count: int) -> dict[str, Any]:
    metadata = {
        "ticker": filing["ticker"],
        "cik": filing["cik"],
        "form": filing["form"],
        "fiscal_year": int(filing["report_date"][:4]),
        "accession_number": filing["accession_number"],
        "source_file": filing["local_path"],
        "chunker": "HybridChunker",
        "hierarchical_chunk_count": hierarchical_count,
        "headings": chunk.meta.headings or [],
        "captions": chunk.meta.model_dump(mode="json", by_alias=True).get("captions", []),
    }
    return metadata


def build_chunks(
    filing: dict[str, Any],
    converter: DocumentConverter,
    hierarchical: HierarchicalChunker,
    hybrid: HybridChunker,
) -> list[dict[str, Any]]:
    source_path = MARKDOWN_DIR / filing["local_path"]
    document = converter.convert(source_path).document
    hierarchical_count = sum(1 for _ in hierarchical.chunk(document))
    chunks: list[dict[str, Any]] = []

    for chunk_index, chunk in enumerate(hybrid.chunk(document)):
        text = hybrid.contextualize(chunk)
        token_count = hybrid.tokenizer.count_tokens(text)
        if token_count > CHUNK_TOKEN_LIMIT:
            raise ValueError(
                f"Chunk exceeds token limit: {filing['local_path']}[{chunk_index}] "
                f"has {token_count} tokens"
            )

        metadata = chunk_metadata(chunk, filing, hierarchical_count)
        chunks.append(
            {
                "id": str(uuid.uuid5(CHUNK_NAMESPACE, f"{filing['accession_number']}:{chunk_index}")),
                "document_id": None,
                "chunk_index": chunk_index,
                "page": get_page(chunk),
                "section": (chunk.meta.headings or [None])[-1],
                "text_content": text,
                "token_count": token_count,
                "chunk_metadata": metadata,
                "accession_number": filing["accession_number"],
            }
        )

    return chunks


async def source_document_ids(client: Any, filings: Iterable[dict[str, Any]]) -> dict[str, str]:
    accessions = [filing["accession_number"] for filing in filings]
    response = await client.table("source_documents").select("id, accession_number").in_(
        "accession_number", accessions
    ).execute()
    return {row["accession_number"]: row["id"] for row in response.data or []}


async def embed_chunks(client: AsyncOpenAI, chunks: list[dict[str, Any]]) -> None:
    for offset in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
        batch = chunks[offset : offset + EMBEDDING_BATCH_SIZE]
        response = await client.embeddings.create(
            model=settings.openai_embedding_model,
            input=[chunk["text_content"] for chunk in batch],
            dimensions=settings.openai_embedding_dimensions,
        )
        for chunk, embedding in zip(batch, response.data, strict=True):
            if len(embedding.embedding) != settings.openai_embedding_dimensions:
                raise ValueError(
                    f"Expected {settings.openai_embedding_dimensions} dimensions, "
                    f"got {len(embedding.embedding)}"
                )
            chunk["embedding"] = embedding.embedding


async def run(*, dry_run: bool, test_one: bool) -> None:
    filings = load_manifest()
    converter = DocumentConverter()
    hierarchical, hybrid = create_chunker()
    all_chunks: list[dict[str, Any]] = []

    selected_filings = filings[:1] if test_one else filings
    for filing in selected_filings:
        chunks = build_chunks(filing, converter, hierarchical, hybrid)
        all_chunks.extend(chunks[:1] if test_one else chunks)
        print(f"{filing['local_path']}: {len(chunks)} hybrid chunks")

    print(f"Prepared {len(all_chunks)} chunk(s).")
    if dry_run:
        return

    service_client = await get_service_role_client()
    document_ids = await source_document_ids(service_client, selected_filings)
    for chunk in all_chunks:
        chunk["document_id"] = document_ids[chunk.pop("accession_number")]

    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    await embed_chunks(openai_client, all_chunks)
    payload = [
        {key: value for key, value in chunk.items() if key != "accession_number"}
        for chunk in all_chunks
    ]
    await service_client.table("document_chunks").upsert(
        payload,
        on_conflict="document_id,chunk_index",
        returning="minimal",
    ).execute()
    print(f"Upserted {len(payload)} embedded chunk(s).")


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(run(dry_run=arguments.dry_run, test_one=arguments.test_one))
