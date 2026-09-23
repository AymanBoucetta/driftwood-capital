"""Convert downloaded SEC HTML filings to Markdown with Docling.

Run from the repository root with:
    uv run --project backend python data/convert_to_markdown.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter


DATA_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = DATA_DIR / "downloads"
DEFAULT_OUTPUT_DIR = DATA_DIR / "markdown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert SEC HTML filings to Markdown with Docling."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing the downloaded HTML files and manifest.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where mirrored Markdown files and manifest are written.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reconvert files even when the destination already exists.",
    )
    return parser.parse_args()


def load_manifest(input_dir: Path) -> dict[str, Any]:
    manifest_path = input_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def convert_filings(
    input_dir: Path,
    output_dir: Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    source_manifest = load_manifest(input_dir)
    converter = DocumentConverter()
    converted_filings: list[dict[str, Any]] = []

    for filing in source_manifest.get("filings", []):
        source_relative = Path(filing["local_path"])
        source_path = input_dir / source_relative
        output_relative = source_relative.with_suffix(".md")
        output_path = output_dir / output_relative
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.exists() and not force:
            print(f"Skipping existing {output_relative}")
        else:
            print(f"Converting {source_relative} -> {output_relative}")
            document = converter.convert(source_path).document
            output_path.write_text(
                document.export_to_markdown(),
                encoding="utf-8",
            )

        converted_filing = dict(filing)
        converted_filing["source_local_path"] = filing["local_path"]
        converted_filing["local_path"] = output_relative.as_posix()
        converted_filing["source_format"] = source_path.suffix.lstrip(".").lower()
        converted_filing["output_format"] = "markdown"
        converted_filings.append(converted_filing)

    output_manifest = dict(source_manifest)
    output_manifest["generated_from"] = "downloads/manifest.json"
    output_manifest["output_format"] = "markdown"
    output_manifest["converted_count"] = len(converted_filings)
    output_manifest["filings"] = converted_filings
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        json.dumps(output_manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_manifest


def main() -> None:
    args = parse_args()
    result = convert_filings(args.input_dir, args.output_dir, force=args.force)
    print(f"Converted {result['converted_count']} filing(s) to {args.output_dir}")
    print(f"Manifest: {args.output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
