#!/usr/bin/env python3
"""Retrieve relevant Flex API documentation chunks from the local BM25 index."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

from build_rag_index import tokenize


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--index", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    index_path = Path(args.index).resolve()
    data = json.loads(index_path.read_text(encoding="utf-8"))
    source = Path(data["source"])
    if not source.is_absolute():
        source = index_path.parent / source
    if not source.exists() or hashlib.sha256(source.read_bytes()).hexdigest() != data["source_sha256"]:
        raise SystemExit("RAG index is stale or its source is missing; rebuild it with build_rag_index.py.")
    chunks = data["chunks"]
    query_terms = Counter(tokenize(args.query))
    document_count = len(chunks)
    average_length = sum(chunk["length"] for chunk in chunks) / max(1, document_count)
    document_frequency = {
        term: sum(1 for chunk in chunks if term in chunk["terms"])
        for term in query_terms
    }
    scored = []
    k1, b = 1.5, 0.75
    for chunk in chunks:
        score = 0.0
        for term, query_weight in query_terms.items():
            frequency = chunk["terms"].get(term, 0)
            if not frequency:
                continue
            df = document_frequency[term]
            inverse_frequency = math.log(1 + (document_count - df + 0.5) / (df + 0.5))
            denominator = frequency + k1 * (1 - b + b * chunk["length"] / max(1, average_length))
            score += query_weight * inverse_frequency * (frequency * (k1 + 1) / denominator)
        if score > 0:
            scored.append((score, chunk))
    results = [
        {
            "score": round(score, 4),
            "heading": chunk["heading"],
            "lines": [chunk["start_line"], chunk["end_line"]],
            "text": chunk["text"],
        }
        for score, chunk in sorted(scored, key=lambda item: item[0], reverse=True)[: max(1, args.top_k)]
    ]
    if args.json:
        print(json.dumps({"query": args.query, "results": results}, ensure_ascii=False, indent=2))
    else:
        for position, result in enumerate(results, start=1):
            print(f"## Result {position} | score={result['score']} | lines={result['lines'][0]}-{result['lines'][1]}")
            print(f"### {result['heading']}")
            print(result["text"].rstrip())
            print()
    return 0 if results else 2


if __name__ == "__main__":
    raise SystemExit(main())
