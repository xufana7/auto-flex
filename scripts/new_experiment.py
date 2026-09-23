#!/usr/bin/env python3
"""Create a unique YYYY-MM-DD_expNN experiment directory."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Workspace directory that will contain the experiment folder")
    parser.add_argument("--date", help="Override date for testing, in YYYY-MM-DD format")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    stamp = args.date or date.today().isoformat()
    date.fromisoformat(stamp)
    pattern = re.compile(rf"^{re.escape(stamp)}_exp(\d+)$")
    used = {
        int(match.group(1))
        for item in root.iterdir()
        if item.is_dir() and (match := pattern.match(item.name))
    }
    number = next(candidate for candidate in range(1, 1000) if candidate not in used)
    suffix = f"{number:02d}"
    folder = root / f"{stamp}_exp{suffix}"
    folder.mkdir()
    payload = {
        "experiment_id": suffix,
        "directory": str(folder),
        "plan": str(folder / f"exp_{suffix}.md"),
        "protocol": str(folder / f"protocol_{suffix}.py"),
        "live_log": str(folder / f"live_run_{suffix}.log"),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
