"""Ingest converted Markdown filings into Supabase source_documents.

Run from the backend directory with:
    uv run python ../data/ingest_source_documents.py --dry-run
    uv run python ../data/ingest_source_documents.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.database.supabase import get_service_role_client

DATA_DIR = Path(__file__).resolve().parent
MARKDOWN_DIR = DATA_DIR / "markdown"
MANIFEST_PATH = MARKDOWN_DIR / "manifest.json"
COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest converted filings into Supabase source_documents."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate files and print the planned count without writing to Supabase.",
    )
    return parser.parse_args()


def load_records() -> list[dict[str, Any]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []

    for filing in manifest.get("filings", []):
        markdown_path = MARKDOWN_DIR / filing["local_path"]
        if not markdown_path.is_file():
            raise FileNotFoundError(f"Markdown file not found: {markdown_path}")

        report_date = filing.get("report_date")
        records.append(
            {
                "ticker": filing["ticker"],
                "cik": filing["cik"],
                "company_name": COMPANY_NAMES.get(filing["ticker"]),
                "form": filing["form"],
                "filing_date": filing["filing_date"],
                "report_date": report_date,
                "fiscal_year": int(report_date[:4]) if report_date else None,
                "accession_number": filing["accession_number"],
                "primary_document": filing["primary_document"],
                "markdown_content": markdown_path.read_text(encoding="utf-8"),
                "ingested_at": datetime.now(UTC).isoformat(),
            }
        )

    return records


async def ingest_records(records: list[dict[str, Any]]) -> None:
    client = await get_service_role_client()
    existing = await client.table("source_documents").select(
        "id, accession_number"
    ).in_("accession_number", [record["accession_number"] for record in records]).execute()
    existing_ids = {
        row["accession_number"]: row["id"] for row in existing.data or []
    }
    for record in records:
        record["id"] = existing_ids.get(record["accession_number"], str(uuid.uuid4()))

    response = await client.table("source_documents").upsert(
        records,
        on_conflict="accession_number",
        returning="minimal",
    ).execute()
    print(f"Upserted {len(records)} source document(s).")
    if response.data:
        print(f"Supabase returned {len(response.data)} row(s).")


async def main(dry_run: bool) -> None:
    records = load_records()
    print(f"Validated {len(records)} Markdown filing(s).")
    if dry_run:
        print("Dry run complete; no database changes were made.")
        return
    await ingest_records(records)


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(main(args.dry_run))
