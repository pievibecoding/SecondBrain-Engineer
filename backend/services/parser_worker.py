from __future__ import annotations

import json
import sys
import time
from importlib import metadata
from pathlib import Path


def _version(package_name: str) -> str | None:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def _docling(path: Path) -> dict:
    started = time.perf_counter()
    from docling.document_converter import DocumentConverter  # type: ignore

    converter = DocumentConverter()
    result = converter.convert(str(path))
    markdown = result.document.export_to_markdown()
    return {
        "status": "ok",
        "text": markdown,
        "metadata": {
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "parser_version": _version("docling"),
        },
    }


def _marker(path: Path) -> dict:
    started = time.perf_counter()
    from marker.converters.pdf import PdfConverter  # type: ignore
    from marker.models import create_model_dict  # type: ignore
    from marker.output import text_from_rendered  # type: ignore

    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(str(path))
    markdown, _metadata, _images = text_from_rendered(rendered)
    return {
        "status": "ok",
        "text": markdown,
        "metadata": {
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "parser_version": _version("marker-pdf"),
        },
    }


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"status": "error", "error": "Usage: parser_worker.py <docling|marker> <path>"}))
        return 2

    parser = sys.argv[1]
    path = Path(sys.argv[2])
    try:
        if parser == "docling":
            result = _docling(path)
        elif parser == "marker":
            result = _marker(path)
        else:
            result = {"status": "error", "error": f"Unsupported parser: {parser}"}
    except Exception as exc:
        result = {"status": "error", "error": str(exc)}

    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
