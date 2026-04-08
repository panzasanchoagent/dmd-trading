-- Starting positions seed template for dmd-trading
-- `positions` is treated as the opening inventory.
-- `trades` should only contain transactional changes AFTER these rows.
-- Replace the example values below before running.

INSERT INTO public.positions (
    asset,
    quantity,
    avg_entry_price,
    total_cost_basis,
    first_entry_date,
    last_trade_date,
    number_of_trades,
    position_type,
    target_allocation_pct,
    updated_at
) VALUES
    (
        'BTC',
        0.50000000,
        62000.00000000,
        31000.00000000,
        '2025-12-31T00:00:00Z',
        '2025-12-31T00:00:00Z',
        1,
        'core',
        25.0000,
        NOW()
    ),
    (
        'ETH',
        10.00000000,
        3200.00000000,
        32000.00000000,
        '2025-12-31T00:00:00Z',
        '2025-12-31T00:00:00Z',
        1,
        'trading',
        15.0000,
        NOW()
    )
ON CONFLICT (asset)
DO UPDATE SET
    quantity = EXCLUDED.quantity,
    avg_entry_price = EXCLUDED.avg_entry_price,
    total_cost_basis = EXCLUDED.total_cost_basis,
    first_entry_date = EXCLUDED.first_entry_date,
    last_trade_date = EXCLUDED.last_trade_date,
    number_of_trades = EXCLUDED.number_of_trades,
    position_type = EXCLUDED.position_type,
    target_allocation_pct = EXCLUDED.target_allocation_pct,
    updated_at = NOW();
