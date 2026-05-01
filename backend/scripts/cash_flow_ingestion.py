#!/usr/bin/env python3
"""Transform and optionally upload external cash deposit/withdrawal data.

Cash movements are stored separately from trades so portfolio reconstruction can
track funding flows without treating them as buys/sells of risk assets.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from db import PersonalDB

EIGHT_DP = Decimal("0.00000001")
ALLOWED_FLOW_TYPES = {"DEPOSIT", "WITHDRAWAL"}


def parse_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def quantize_decimal(value: Optional[Decimal]) -> Optional[Decimal]:
    if value is None:
        return None
    return value.quantize(EIGHT_DP, rounding=ROUND_HALF_UP)


def parse_datetime(value: str) -> datetime:
    text = value.strip()
    if not text:
        raise ValueError("executed_at is required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_tags(value: str) -> list[str]:
    if not value.strip():
        return ["external_cash_flow"]
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            tags = [str(item).strip() for item in parsed if str(item).strip()]
        else:
            tags = [segment.strip() for segment in value.split(",") if segment.strip()]
    except json.JSONDecodeError:
        tags = [segment.strip() for segment in value.split(",") if segment.strip()]
    if "external_cash_flow" not in tags:
        tags.append("external_cash_flow")
    return tags


def cash_flow_row_to_normalized(row: dict[str, str]) -> dict[str, Any]:
    flow_type = (row.get("flow_type") or "").strip().upper()
    asset = (row.get("asset") or "").strip().upper()
    amount = parse_decimal(row.get("amount"))
    if flow_type not in ALLOWED_FLOW_TYPES:
        raise ValueError(f"Unsupported flow_type {flow_type!r}. Allowed: {sorted(ALLOWED_FLOW_TYPES)}")
    if not asset:
        raise ValueError(f"Missing asset in row: {row}")
    if amount is None or amount <= 0:
        raise ValueError(f"Amount must be positive in row: {row}")

    executed_at = parse_datetime(row.get("executed_at") or "")
    notes = (row.get("notes") or "").strip() or None
    reference = (row.get("reference") or "").strip() or None
    source_platform = (row.get("source_platform") or "manual").strip() or "manual"

    return {
        "asset": asset,
        "flow_type": flow_type,
        "amount": float(quantize_decimal(amount)),
        "executed_at": executed_at.isoformat(),
        "source_platform": source_platform,
        "reference": reference,
        "notes": notes,
        "tags": normalize_tags(row.get("tags") or ""),
    }


def transform_cash_flows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not any((value or "").strip() for value in row.values()):
            continue
        normalized.append(cash_flow_row_to_normalized(row))
    return normalized


def write_output(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".json":
        output_path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return

    headers = ["asset", "flow_type", "amount", "executed_at", "source_platform", "reference", "notes", "tags"]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for record in records:
            row = dict(record)
            row["tags"] = json.dumps(row.get("tags", []), ensure_ascii=False)
            writer.writerow(row)


async def upload_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    db = PersonalDB()
    uploaded = []
    for record in records:
        uploaded.append(await db.create_cash_transaction(record))
    return uploaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Source CSV path")
    parser.add_argument("--output", type=Path, help="Write normalized records to CSV or JSON")
    parser.add_argument("--upload", action="store_true", help="Upload normalized records to personal Supabase")
    return parser


def main() -> int:
    load_dotenv(BACKEND_DIR / ".env")
    args = build_parser().parse_args()
    records = transform_cash_flows(args.input)

    if args.output:
        write_output(records, args.output)
        print(f"Wrote {len(records)} normalized cash flows to {args.output}")

    if args.upload:
        uploaded = asyncio.run(upload_records(records))
        print(f"Uploaded {len(uploaded)} cash flows to personal Supabase")
    else:
        print(f"Prepared {len(records)} cash flows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
