"""
Portfolio computation helpers.

Keeps dmd-trading usable in isolation by deriving open positions directly
from the local `trades` table when a precomputed `positions` snapshot has
not been populated yet.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from db import personal_db


ZERO = Decimal("0")
POSITION_TYPE_BY_TIMEFRAME = {
    "position": "core",
    "swing": "trading",
    "day_trade": "trading",
}


def _to_decimal(value: Any) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _infer_position_type(trade: dict) -> str | None:
    timeframe = (trade.get("timeframe") or "").strip().lower()
    return POSITION_TYPE_BY_TIMEFRAME.get(timeframe) or "unclassified"


async def compute_positions_from_trades() -> list[dict]:
    """Build current positions from the local trades table only."""
    trades = await personal_db.get_all_trades_for_portfolio()
    grouped: dict[str, dict[str, Any]] = defaultdict(dict)

    for trade in trades:
        asset = (trade.get("asset") or "").upper().strip()
        if not asset:
            continue

        side = (trade.get("side") or "").upper().strip()
        quantity = _to_decimal(trade.get("quantity"))
        price = _to_decimal(trade.get("price"))
        if quantity <= ZERO or price <= ZERO or side not in {"BUY", "SELL"}:
            continue

        position = grouped.setdefault(
            asset,
            {
                "asset": asset,
                "quantity": ZERO,
                "total_cost_basis": ZERO,
                "avg_entry_price": None,
                "first_entry_date": None,
                "last_trade_date": None,
                "number_of_trades": 0,
                "position_type": None,
                "target_allocation_pct": None,
            },
        )

        current_qty = _to_decimal(position["quantity"])
        current_cost = _to_decimal(position["total_cost_basis"])

        if side == "BUY":
            new_qty = current_qty + quantity
            new_cost = current_cost + (quantity * price)
            position["quantity"] = new_qty
            position["total_cost_basis"] = new_cost
            position["avg_entry_price"] = (new_cost / new_qty) if new_qty > ZERO else None
            position["first_entry_date"] = position["first_entry_date"] or trade.get("executed_at")
        else:
            if current_qty <= ZERO:
                continue
            sell_qty = min(quantity, current_qty)
            avg_cost = (current_cost / current_qty) if current_qty > ZERO else ZERO
            new_qty = current_qty - sell_qty
            new_cost = current_cost - (avg_cost * sell_qty)
            position["quantity"] = new_qty
            position["total_cost_basis"] = new_cost if new_qty > ZERO else ZERO
            position["avg_entry_price"] = (new_cost / new_qty) if new_qty > ZERO else None

        position["last_trade_date"] = trade.get("executed_at")
        position["number_of_trades"] += 1
        position["position_type"] = position.get("position_type") or _infer_position_type(trade)

    open_positions: list[dict] = []
    for position in grouped.values():
        quantity = _to_decimal(position["quantity"])
        if quantity <= ZERO:
            continue

        total_cost_basis = _to_decimal(position["total_cost_basis"])
        avg_entry_price = position.get("avg_entry_price")
        open_positions.append(
            {
                "asset": position["asset"],
                "quantity": float(quantity),
                "avg_entry_price": float(avg_entry_price) if avg_entry_price is not None else None,
                "total_cost_basis": float(total_cost_basis),
                "first_entry_date": position.get("first_entry_date"),
                "last_trade_date": position.get("last_trade_date"),
                "number_of_trades": position.get("number_of_trades"),
                "current_price": None,
                "current_value": None,
                "unrealized_pnl": None,
                "unrealized_pnl_pct": None,
                "allocation_pct": None,
                "position_type": position.get("position_type") or "unclassified",
                "target_allocation_pct": position.get("target_allocation_pct"),
                "source": "computed_from_trades",
            }
        )

    return sorted(open_positions, key=lambda item: item["asset"])


async def get_portfolio_positions() -> tuple[list[dict], str]:
    """Prefer the local positions snapshot, fallback to computed trades."""
    positions = await personal_db.get_positions()
    if positions:
        for position in positions:
            position.setdefault("source", "positions_table")
        return positions, "positions_table"

    computed = await compute_positions_from_trades()
    return computed, "computed_from_trades"
