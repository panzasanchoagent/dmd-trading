#!/usr/bin/env python3
"""Transform and optionally upload personal trading data into the Trading Journal DB.

Supports:
- IBKR activity exports with auto-FX rows
- Manual CSV template based on David's YTD trade log format

The normalized output shape targets the personal `trades` table and adds
`source_platform` for provenance.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable, Optional

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from db import PersonalDB


USD = "USD"
EIGHT_DP = Decimal("0.00000001")
FOUR_DP = Decimal("0.0001")


@dataclass
class FxQuote:
    base: str
    quote: str
    rate: Decimal
    executed_at: datetime
    raw_symbol: str


def parse_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def quantize_decimal(value: Optional[Decimal], places: Decimal = EIGHT_DP) -> Optional[Decimal]:
    if value is None:
        return None
    return value.quantize(places, rounding=ROUND_HALF_UP)


def parse_ibkr_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d, %H:%M:%S").replace(tzinfo=timezone.utc)


def parse_manual_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%d/%m/%Y %H:%M").replace(tzinfo=timezone.utc)


def clean_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if "." in symbol:
        left, right = symbol.split(".", 1)
        if len(right) == 1:
            return left
    return symbol


def parse_fx_symbol(symbol: str, currency_hint: str) -> Optional[tuple[str, str]]:
    symbol = symbol.strip().upper()
    currency_hint = currency_hint.strip().upper()
    if "." in symbol:
        base, quote = symbol.split(".", 1)
        return base, quote
    if len(symbol) == 6:
        return symbol[:3], symbol[3:]
    if currency_hint and "." in currency_hint:
        return tuple(currency_hint.split(".", 1))
    return None


def load_ibkr_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def build_fx_quotes(rows: Iterable[dict[str, str]]) -> list[FxQuote]:
    quotes: list[FxQuote] = []
    for row in rows:
        if row.get("Asset Category") != "Forex":
            continue
        quantity = parse_decimal(row.get("Quantity"))
        rate = parse_decimal(row.get("T. Price"))
        executed_at_raw = row.get("Date/Time", "")
        parsed_pair = parse_fx_symbol(row.get("Symbol", ""), row.get("Currency", ""))
        if quantity in (None, Decimal("0")) or rate is None or not executed_at_raw or not parsed_pair:
            continue
        base, quote = parsed_pair
        quotes.append(
            FxQuote(
                base=base,
                quote=quote,
                rate=rate,
                executed_at=parse_ibkr_datetime(executed_at_raw),
                raw_symbol=row.get("Symbol", ""),
            )
        )
    return sorted(quotes, key=lambda item: item.executed_at)


def find_latest_direct_rate(
    fx_quotes: list[FxQuote],
    *,
    base: str,
    quote: str,
    at_or_before: datetime,
) -> Optional[Decimal]:
    chosen: Optional[FxQuote] = None
    for item in fx_quotes:
        if item.executed_at > at_or_before:
            break
        if item.base == base and item.quote == quote:
            chosen = item
    if chosen:
        return chosen.rate
    return None


def find_nearest_direct_rate(
    fx_quotes: list[FxQuote],
    *,
    base: str,
    quote: str,
    target_time: datetime,
    max_seconds: int = 300,
) -> Optional[Decimal]:
    best: Optional[FxQuote] = None
    best_delta: Optional[float] = None
    for item in fx_quotes:
        if item.base != base or item.quote != quote:
            continue
        delta = abs((item.executed_at - target_time).total_seconds())
        if delta > max_seconds:
            continue
        if best is None or delta < (best_delta or float('inf')):
            best = item
            best_delta = delta
    return best.rate if best else None


def find_fx_to_usd(currency: str, executed_at: datetime, fx_quotes: list[FxQuote]) -> tuple[Optional[Decimal], Optional[str]]:
    currency = currency.upper()
    if currency == USD:
        return Decimal("1"), "identity"

    direct = find_nearest_direct_rate(fx_quotes, base=currency, quote=USD, target_time=executed_at) or find_latest_direct_rate(
        fx_quotes, base=currency, quote=USD, at_or_before=executed_at
    )
    if direct is not None:
        return direct, f"{currency}.USD"

    inverse = find_nearest_direct_rate(fx_quotes, base=USD, quote=currency, target_time=executed_at) or find_latest_direct_rate(
        fx_quotes, base=USD, quote=currency, at_or_before=executed_at
    )
    if inverse is not None and inverse != 0:
        return Decimal("1") / inverse, f"inverse USD.{currency}"

    gbp_usd = find_nearest_direct_rate(fx_quotes, base="GBP", quote=USD, target_time=executed_at) or find_latest_direct_rate(
        fx_quotes, base="GBP", quote=USD, at_or_before=executed_at
    )
    if gbp_usd is not None:
        ccy_gbp = find_nearest_direct_rate(fx_quotes, base=currency, quote="GBP", target_time=executed_at) or find_latest_direct_rate(
            fx_quotes, base=currency, quote="GBP", at_or_before=executed_at
        )
        if ccy_gbp is not None:
            return ccy_gbp * gbp_usd, f"{currency}.GBP x GBP.USD"

        gbp_ccy = find_nearest_direct_rate(fx_quotes, base="GBP", quote=currency, target_time=executed_at) or find_latest_direct_rate(
            fx_quotes, base="GBP", quote=currency, at_or_before=executed_at
        )
        if gbp_ccy is not None and gbp_ccy != 0:
            return gbp_usd / gbp_ccy, f"GBP.USD / GBP.{currency}"

    return None, None


def ibkr_trade_to_normalized(row: dict[str, str], fx_quotes: list[FxQuote]) -> dict[str, Any]:
    quantity = parse_decimal(row.get("Quantity"))
    price_local = parse_decimal(row.get("T. Price"))
    fee_local = parse_decimal(row.get("Comm/Fee"))
    executed_at = parse_ibkr_datetime(row["Date/Time"])
    currency = row["Currency"].upper()

    if quantity is None or quantity == 0 or price_local is None:
        raise ValueError(f"Invalid IBKR trade row: {row}")

    side = "BUY" if quantity > 0 else "SELL"
    quantity_abs = abs(quantity)
    fx_to_usd, fx_source = find_fx_to_usd(currency, executed_at, fx_quotes)
    if fx_to_usd is None:
        raise ValueError(
            f"Missing FX conversion path for {row['Symbol']} {currency} at {row['Date/Time']}"
        )

    price_usd = price_local * fx_to_usd
    fee_usd = abs(fee_local or Decimal("0")) * fx_to_usd

    notes = [
        f"Imported from IBKR {row['Asset Category']} export",
        f"Original trade currency: {currency}",
        f"Original price: {quantize_decimal(price_local)} {currency}",
    ]
    if currency != USD:
        notes.append(f"FX conversion: {fx_source} -> {quantize_decimal(fx_to_usd, FOUR_DP)} USD/{currency}")
    if fee_local:
        notes.append(f"Original fee: {abs(fee_local)} {currency}")

    tags = ["imported", "ibkr", f"asset_category:{row['Asset Category'].lower()}"]
    if currency != USD:
        tags.append(f"original_ccy:{currency}")

    return {
        "asset": clean_symbol(row["Symbol"]),
        "side": side,
        "quantity": float(quantize_decimal(quantity_abs)),
        "price": float(quantize_decimal(price_usd)),
        "quote_currency": USD,
        "executed_at": executed_at.isoformat(),
        "source_platform": "ibkr",
        "entry_rationale": " | ".join(notes),
        "tags": tags,
        "metadata": {
            "source_trade": {
                "symbol": row["Symbol"],
                "asset_category": row["Asset Category"],
                "trade_currency": currency,
                "trade_price_local": str(price_local),
                "quantity_signed": str(quantity),
                "fee_local": str(fee_local or Decimal("0")),
                "fx_to_usd": str(quantize_decimal(fx_to_usd, FOUR_DP)),
                "fx_source": fx_source,
                "proceeds_local": row.get("Proceeds"),
                "basis_local": row.get("Basis"),
                "realized_pnl_local": row.get("Realized P/L"),
                "code": row.get("Code"),
            },
            "fee_usd": str(quantize_decimal(fee_usd)),
        },
    }


def transform_ibkr(path: Path) -> list[dict[str, Any]]:
    rows = load_ibkr_rows(path)
    fx_quotes = build_fx_quotes(rows)
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if row.get("Asset Category") != "Stocks":
            continue
        normalized.append(ibkr_trade_to_normalized(row, fx_quotes))
    return normalized


def manual_trade_to_normalized(row: dict[str, str]) -> dict[str, Any]:
    trade_id = (row.get("ID") or "").strip()
    symbol = (row.get("Symbol") or "").strip().upper()
    side_raw = (row.get("Ask / Bid") or "").strip().upper()
    from_amount = parse_decimal(row.get("From Amount"))
    to_amount = parse_decimal(row.get("To Amount"))
    quote_price = parse_decimal(row.get("Quote Price"))
    settlement_status = (row.get("settlement_status") or "").strip()

    if not symbol or not side_raw:
        raise ValueError(f"Missing symbol or side in manual row: {row}")
    if "_" not in symbol:
        raise ValueError(f"Expected market symbol like BTC_USDT, got: {symbol}")
    asset, quote_ccy = symbol.split("_", 1)

    side_map = {"ASK": "BUY", "BID": "SELL"}
    if side_raw not in side_map:
        raise ValueError(f"Unexpected side value {side_raw!r} in row: {row}")
    side = side_map[side_raw]

    if side == "BUY":
        quantity = to_amount
    else:
        quantity = from_amount

    if quantity is None or quote_price is None:
        raise ValueError(f"Missing quantity or quote price in manual row: {row}")

    notes = [
        "Imported from manual trade template",
        f"Settlement status: {settlement_status or 'UNKNOWN'}",
    ]
    if trade_id:
        notes.append(f"Manual trade ID: {trade_id}")
    if from_amount is not None and to_amount is not None:
        notes.append(f"From {from_amount} {row.get('From Coin','').strip()} to {to_amount} {row.get('To Coin','').strip()}")

    return {
        "asset": asset,
        "side": side,
        "quantity": float(quantize_decimal(abs(quantity))),
        "price": float(quantize_decimal(quote_price)),
        "quote_currency": quote_ccy,
        "executed_at": parse_manual_datetime(row["DONE timestamp UTC"]).isoformat(),
        "source_platform": "manual",
        "entry_rationale": " | ".join(notes),
        "tags": ["imported", "manual-template", f"settlement:{(settlement_status or 'unknown').lower()}"],
        "metadata": {
            "source_trade": {
                "id": trade_id or None,
                "symbol": symbol,
                "from_amount": str(from_amount) if from_amount is not None else None,
                "from_coin": row.get("From Coin"),
                "to_amount": str(to_amount) if to_amount is not None else None,
                "to_coin": row.get("To Coin"),
                "template_side": side_raw,
                "settlement_status": settlement_status or None,
            }
        },
    }


def transform_manual(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not any((value or "").strip() for value in row.values()):
            continue
        normalized.append(manual_trade_to_normalized(row))
    return normalized


def json_ready(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def convert(value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {k: convert(v) for k, v in value.items()}
        if isinstance(value, list):
            return [convert(v) for v in value]
        return value

    return [convert(record) for record in records]


def csv_ready(records: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    headers = [
        "asset",
        "side",
        "quantity",
        "price",
        "quote_currency",
        "executed_at",
        "source_platform",
        "entry_rationale",
        "tags",
        "metadata",
    ]
    rows = []
    for record in json_ready(records):
        row = dict(record)
        row["tags"] = json.dumps(row.get("tags", []), ensure_ascii=False)
        row["metadata"] = json.dumps(row.get("metadata", {}), ensure_ascii=False)
        rows.append(row)
    return headers, rows


def write_output(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".json":
        output_path.write_text(json.dumps(json_ready(records), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return

    headers, rows = csv_ready(records)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def strip_metadata_for_upload(record: dict[str, Any], include_source_platform: bool = True) -> dict[str, Any]:
    payload = {k: v for k, v in record.items() if k != "metadata"}
    if not include_source_platform:
        payload.pop("source_platform", None)
    return payload


def table_has_column(db: PersonalDB, table_name: str, column_name: str) -> bool:
    try:
        db.client.table(table_name).select(column_name).limit(1).execute()
        return True
    except Exception as exc:
        if column_name in str(exc) and "does not exist" in str(exc):
            return False
        raise


async def upload_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    db = PersonalDB()
    include_source_platform = table_has_column(db, "trades", "source_platform")
    uploaded = []
    for record in records:
        uploaded.append(await db.create_trade(strip_metadata_for_upload(record, include_source_platform=include_source_platform)))
    return uploaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["ibkr", "manual"], help="Input format to transform")
    parser.add_argument("input", type=Path, help="Source CSV path")
    parser.add_argument("--output", type=Path, help="Write normalized records to CSV or JSON")
    parser.add_argument("--upload", action="store_true", help="Upload normalized records to personal Supabase")
    return parser


def main() -> int:
    load_dotenv(BACKEND_DIR / ".env")
    args = build_parser().parse_args()

    if args.mode == "ibkr":
        records = transform_ibkr(args.input)
    else:
        records = transform_manual(args.input)

    if args.output:
        write_output(records, args.output)
        print(f"Wrote {len(records)} normalized trades to {args.output}")

    if args.upload:
        import asyncio

        uploaded = asyncio.run(upload_records(records))
        print(f"Uploaded {len(uploaded)} trades to personal Supabase")
    else:
        print(f"Prepared {len(records)} normalized trades")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
