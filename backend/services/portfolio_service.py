"""
Portfolio reconstruction helpers.

Keeps dmd-trading usable in isolation by rebuilding portfolio state from the
local database only:
- `positions` are treated as seeded starting positions
- `trades` are treated as transactional deltas after those starting positions

This mirrors the clarified LiquidPortfolioJobs-style architecture without
referencing another repo at runtime.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from db import personal_db


ZERO = Decimal("0")
POSITION_TYPE_BY_TIMEFRAME = {
    "position": "core",
    "swing": "trading",
    "day_trade": "trading",
}


class PortfolioDataGap(Exception):
    """Raised when portfolio reconstruction needs data that is not available."""


@dataclass
class ClosedCycle:
    asset: str
    entry_date: Optional[str] = None
    avg_entry_price: Decimal = ZERO
    total_bought: Decimal = ZERO
    entry_cost_basis: Decimal = ZERO
    exit_date: Optional[str] = None
    avg_exit_price: Decimal = ZERO
    total_sold: Decimal = ZERO
    exit_proceeds: Decimal = ZERO
    realized_pnl: Decimal = ZERO
    realized_pnl_pct: Optional[Decimal] = None
    holding_period_days: Optional[int] = None
    number_of_trades: int = 0
    strategy: Optional[str] = None
    win_loss: Optional[str] = None


@dataclass
class AssetLedger:
    asset: str
    quantity: Decimal = ZERO
    total_cost_basis: Decimal = ZERO
    first_entry_date: Optional[str] = None
    last_trade_date: Optional[str] = None
    number_of_trades: int = 0
    position_type: Optional[str] = None
    target_allocation_pct: Optional[Decimal] = None
    active_cycle: ClosedCycle | None = None
    closed_cycles: list[ClosedCycle] = field(default_factory=list)


@dataclass
class PortfolioReconstruction:
    positions: list[dict]
    closed_positions: list[dict]
    source: str
    seed_positions_count: int
    trades_count: int


def _to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _to_float(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _to_iso(value: Any) -> Optional[str]:
    dt = _parse_datetime(value)
    return dt.isoformat() if dt else None


def _infer_position_type(record: dict) -> str | None:
    timeframe = (record.get("timeframe") or "").strip().lower()
    explicit_type = (record.get("position_type") or "").strip().lower()
    return explicit_type or POSITION_TYPE_BY_TIMEFRAME.get(timeframe) or "unclassified"


def _ensure_cycle(ledger: AssetLedger) -> ClosedCycle:
    if ledger.active_cycle is None:
        ledger.active_cycle = ClosedCycle(asset=ledger.asset)
    return ledger.active_cycle


def _apply_buy(ledger: AssetLedger, quantity: Decimal, price: Decimal, executed_at: Optional[str], record: dict) -> None:
    if quantity <= ZERO or price <= ZERO:
        return

    ledger.quantity += quantity
    ledger.total_cost_basis += quantity * price
    ledger.first_entry_date = ledger.first_entry_date or executed_at
    ledger.last_trade_date = executed_at or ledger.last_trade_date
    ledger.number_of_trades += 1
    ledger.position_type = ledger.position_type or _infer_position_type(record)
    if record.get("target_allocation_pct") is not None:
        ledger.target_allocation_pct = _to_decimal(record.get("target_allocation_pct"))

    cycle = _ensure_cycle(ledger)
    cycle.entry_date = cycle.entry_date or executed_at
    cycle.entry_cost_basis += quantity * price
    cycle.total_bought += quantity
    cycle.avg_entry_price = (cycle.entry_cost_basis / cycle.total_bought) if cycle.total_bought > ZERO else ZERO
    cycle.number_of_trades += 1
    cycle.strategy = cycle.strategy or record.get("strategy")


def _finalize_cycle(ledger: AssetLedger, executed_at: Optional[str]) -> None:
    cycle = ledger.active_cycle
    if not cycle or cycle.total_sold <= ZERO:
        ledger.active_cycle = None if ledger.quantity <= ZERO else cycle
        return

    cycle.exit_date = executed_at or cycle.exit_date
    cycle.avg_exit_price = (cycle.exit_proceeds / cycle.total_sold) if cycle.total_sold > ZERO else ZERO
    cycle.realized_pnl_pct = (
        (cycle.realized_pnl / cycle.entry_cost_basis) * Decimal("100")
        if cycle.entry_cost_basis > ZERO else None
    )
    if cycle.realized_pnl > ZERO:
        cycle.win_loss = "win"
    elif cycle.realized_pnl < ZERO:
        cycle.win_loss = "loss"
    else:
        cycle.win_loss = "breakeven"

    entry_dt = _parse_datetime(cycle.entry_date)
    exit_dt = _parse_datetime(cycle.exit_date)
    if entry_dt and exit_dt:
        cycle.holding_period_days = (exit_dt.date() - entry_dt.date()).days

    ledger.closed_cycles.append(cycle)
    ledger.active_cycle = None


def _apply_sell(ledger: AssetLedger, quantity: Decimal, price: Decimal, executed_at: Optional[str], record: dict) -> None:
    if quantity <= ZERO or price <= ZERO or ledger.quantity <= ZERO:
        return

    sell_qty = min(quantity, ledger.quantity)
    avg_cost = (ledger.total_cost_basis / ledger.quantity) if ledger.quantity > ZERO else ZERO
    realized_cost = avg_cost * sell_qty
    realized_proceeds = sell_qty * price

    ledger.quantity -= sell_qty
    ledger.total_cost_basis -= realized_cost
    if ledger.quantity <= ZERO:
        ledger.quantity = ZERO
        ledger.total_cost_basis = ZERO

    ledger.last_trade_date = executed_at or ledger.last_trade_date
    ledger.number_of_trades += 1
    ledger.position_type = ledger.position_type or _infer_position_type(record)

    cycle = _ensure_cycle(ledger)
    cycle.exit_date = executed_at or cycle.exit_date
    cycle.total_sold += sell_qty
    cycle.exit_proceeds += realized_proceeds
    cycle.realized_pnl += realized_proceeds - realized_cost
    cycle.number_of_trades += 1
    cycle.strategy = cycle.strategy or record.get("strategy")

    if ledger.quantity <= ZERO:
        _finalize_cycle(ledger, executed_at)


def _serialize_closed_cycle(cycle: ClosedCycle) -> dict:
    return {
        "asset": cycle.asset,
        "entry_date": cycle.entry_date,
        "avg_entry_price": _to_float(cycle.avg_entry_price),
        "total_bought": _to_float(cycle.total_bought),
        "entry_cost_basis": _to_float(cycle.entry_cost_basis),
        "exit_date": cycle.exit_date,
        "avg_exit_price": _to_float(cycle.avg_exit_price),
        "total_sold": _to_float(cycle.total_sold),
        "exit_proceeds": _to_float(cycle.exit_proceeds),
        "realized_pnl": _to_float(cycle.realized_pnl),
        "realized_pnl_pct": _to_float(cycle.realized_pnl_pct),
        "holding_period_days": cycle.holding_period_days,
        "number_of_trades": cycle.number_of_trades,
        "strategy": cycle.strategy,
        "win_loss": cycle.win_loss,
        "source": "reconstructed_from_positions_and_trades",
    }


async def reconstruct_portfolio_state() -> PortfolioReconstruction:
    seed_positions = await personal_db.list_position_seeds()
    trades = await personal_db.get_all_trades_for_portfolio()

    ledgers: dict[str, AssetLedger] = {}

    for seed in seed_positions:
        asset = (seed.get("asset") or "").upper().strip()
        quantity = _to_decimal(seed.get("quantity"))
        price = _to_decimal(seed.get("avg_entry_price"))
        if not asset or quantity <= ZERO or price <= ZERO:
            continue

        ledger = ledgers.setdefault(asset, AssetLedger(asset=asset))
        seed_record = {
            "position_type": seed.get("position_type"),
            "strategy": seed.get("strategy"),
            "target_allocation_pct": seed.get("target_allocation_pct"),
        }
        executed_at = _to_iso(seed.get("first_entry_date") or seed.get("last_trade_date") or seed.get("updated_at"))
        _apply_buy(ledger, quantity, price, executed_at, seed_record)
        ledger.number_of_trades = max(ledger.number_of_trades, int(seed.get("number_of_trades") or 1))

    for trade in trades:
        asset = (trade.get("asset") or "").upper().strip()
        side = (trade.get("side") or "").upper().strip()
        quantity = _to_decimal(trade.get("quantity"))
        price = _to_decimal(trade.get("price"))
        if not asset or side not in {"BUY", "SELL"}:
            continue

        ledger = ledgers.setdefault(asset, AssetLedger(asset=asset))
        executed_at = _to_iso(trade.get("executed_at"))
        if side == "BUY":
            _apply_buy(ledger, quantity, price, executed_at, trade)
        else:
            _apply_sell(ledger, quantity, price, executed_at, trade)

    positions: list[dict] = []
    closed_positions: list[dict] = []

    for ledger in ledgers.values():
        for cycle in ledger.closed_cycles:
            closed_positions.append(_serialize_closed_cycle(cycle))

        if ledger.quantity <= ZERO:
            continue

        avg_entry_price = (ledger.total_cost_basis / ledger.quantity) if ledger.quantity > ZERO else None
        positions.append(
            {
                "asset": ledger.asset,
                "quantity": float(ledger.quantity),
                "avg_entry_price": _to_float(avg_entry_price),
                "total_cost_basis": _to_float(ledger.total_cost_basis),
                "first_entry_date": ledger.first_entry_date,
                "last_trade_date": ledger.last_trade_date,
                "number_of_trades": ledger.number_of_trades,
                "current_price": None,
                "current_value": None,
                "unrealized_pnl": None,
                "unrealized_pnl_pct": None,
                "allocation_pct": None,
                "position_type": ledger.position_type or "unclassified",
                "target_allocation_pct": _to_float(ledger.target_allocation_pct),
                "source": "reconstructed_from_positions_and_trades",
            }
        )

    source = "trades_only"
    if seed_positions and trades:
        source = "positions_plus_trades"
    elif seed_positions:
        source = "positions_only"

    positions.sort(key=lambda item: item["asset"])
    closed_positions.sort(key=lambda item: item.get("exit_date") or "", reverse=True)

    return PortfolioReconstruction(
        positions=positions,
        closed_positions=closed_positions,
        source=source,
        seed_positions_count=len(seed_positions),
        trades_count=len(trades),
    )


async def get_portfolio_positions() -> tuple[list[dict], str]:
    reconstruction = await reconstruct_portfolio_state()
    return reconstruction.positions, reconstruction.source


async def get_reconstructed_closed_positions() -> tuple[list[dict], str]:
    reconstruction = await reconstruct_portfolio_state()
    return reconstruction.closed_positions, reconstruction.source


async def compute_daily_nav_history(days: int = 90) -> tuple[list[dict], str]:
    reconstruction = await reconstruct_portfolio_state()
    positions = reconstruction.positions

    if not positions:
        return [], reconstruction.source

    assets = [position["asset"] for position in positions]
    price_history = await personal_db.get_stock_price_history(assets=assets, days=days)
    if not price_history:
        raise PortfolioDataGap(
            "No local stock_ohlcv price history is available. "
            "Create/populate public.stock_ohlcv with symbol, date, close columns to enable daily NAV."
        )

    today = date.today()
    start_date = today - timedelta(days=days - 1)
    dates = [start_date + timedelta(days=offset) for offset in range(days)]

    by_symbol: dict[str, dict[str, Decimal]] = defaultdict(dict)
    for row in price_history:
        symbol = (row.get("symbol") or "").upper()
        row_date = str(row.get("date"))
        close = row.get("close")
        if symbol and row_date and close is not None:
            by_symbol[symbol][row_date] = _to_decimal(close)

    history: list[dict] = []
    latest_seen: dict[str, Decimal] = {}

    for current_date in dates:
        iso_date = current_date.isoformat()
        total_value = ZERO
        priced_assets = 0
        for position in positions:
            symbol = position["asset"]
            if iso_date in by_symbol[symbol]:
                latest_seen[symbol] = by_symbol[symbol][iso_date]
            price = latest_seen.get(symbol)
            if price is None:
                continue
            total_value += _to_decimal(position["quantity"]) * price
            priced_assets += 1

        history.append(
            {
                "date": iso_date,
                "nav": float(total_value),
                "priced_assets": priced_assets,
                "total_assets": len(positions),
            }
        )

    return history, reconstruction.source
