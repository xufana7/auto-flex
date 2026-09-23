#!/usr/bin/env python3
"""Build a compact BM25 index for the bundled Flex API Markdown."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*|\d+(?:\.\d+)*|[\u4e00-\u9fff]+")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in TOKEN_RE.findall(text.lower()):
        tokens.append(raw)
        if re.fullmatch(r"[\u4e00-\u9fff]+", raw):
            tokens.extend(raw[index : index + 2] for index in range(max(0, len(raw) - 1)))
    return tokens


def chunk_markdown(text: str, max_chars: int) -> list[dict]:
    lines = text.splitlines()
    chunks: list[dict] = []
    headings: list[str] = []
    buffer: list[str] = []
    start_line = 1

    def flush(end_line: int) -> None:
        nonlocal buffer, start_line
        body = "\n".join(buffer).strip()
        if body:
            chunks.append({
                "heading": " > ".join(headings) or "Document",
                "start_line": start_line,
                "end_line": end_line,
                "text": body,
            })
        buffer = []

    for line_number, line in enumerate(lines, start=1):
        heading = HEADING_RE.match(line)
        if heading:
            flush(line_number - 1)
            level = len(heading.group(1))
            headings[:] = headings[: level - 1]
            headings.append(heading.group(2))
            buffer = [line]
            start_line = line_number
            continue
        projected = sum(len(item) + 1 for item in buffer) + len(line)
        if buffer and projected > max_chars and not line.startswith("```"):
            flush(line_number - 1)
            start_line = line_number
        buffer.append(line)
    flush(len(lines))
    return chunks


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("document")
    parser.add_argument("index")
    parser.add_argument("--max-chars", type=int, default=2400)
    args = parser.parse_args()

    document = Path(args.document).resolve()
    output = Path(args.index).resolve()
    raw = document.read_bytes()
    text = raw.decode("utf-8-sig")
    chunks = chunk_markdown(text, args.max_chars)
    for chunk in chunks:
        terms = tokenize(chunk["heading"] + "\n" + chunk["text"])
        chunk["length"] = len(terms)
        chunk["terms"] = dict(Counter(terms))
    source_reference = document.name if document.parent == output.parent else str(document)
    payload = {
        "format": "auto-flex-bm25-v1",
        "source": source_reference,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"index": str(output), "chunks": len(chunks), "source_sha256": payload["source_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
