#!/usr/bin/env python3
"""Upload normalized trade records into the personal Trading Journal Supabase DB."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from db import PersonalDB
from scripts.trade_ingestion import table_has_column


def load_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    records = []
    for row in rows:
        row["quantity"] = float(row["quantity"])
        row["price"] = float(row["price"])
        row["tags"] = json.loads(row.get("tags") or "[]")
        row["metadata"] = json.loads(row.get("metadata") or "{}")
        records.append(row)
    return records


async def upload(path: Path) -> int:
    db = PersonalDB()
    include_source_platform = table_has_column(db, "trades", "source_platform")
    records = load_records(path)
    count = 0
    for record in records:
        payload = {k: v for k, v in record.items() if k not in {"metadata"}}
        if not include_source_platform:
            payload.pop("source_platform", None)
        await db.create_trade(payload)
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Normalized CSV or JSON file")
    args = parser.parse_args()

    load_dotenv(BACKEND_DIR / ".env")
    uploaded = asyncio.run(upload(args.input))
    print(f"Uploaded {uploaded} trades from {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
