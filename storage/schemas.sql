CREATE TABLE raw_trades (
    ts_event TIMESTAMPTZ NOT NULL,
    ts_recv TIMESTAMPTZ,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    trade_id TEXT,
    price NUMERIC NOT NULL,
    size_base NUMERIC NOT NULL,
    notional_quote NUMERIC NOT NULL,
    raw_side TEXT,
    aggressor_side TEXT,
    classification_method TEXT,
    classification_confidence NUMERIC,
    source TEXT NOT NULL,
    inserted_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY(exchange, symbol, trade_id)
);

CREATE TABLE l2_snapshots (
    ts_event TIMESTAMPTZ NOT NULL,
    ts_recv TIMESTAMPTZ,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    best_bid NUMERIC NOT NULL,
    best_ask NUMERIC NOT NULL,
    bid_size_1 NUMERIC NOT NULL,
    ask_size_1 NUMERIC NOT NULL,
    bids JSONB NOT NULL,
    asks JSONB NOT NULL,
    microprice NUMERIC,
    imbalance_5 NUMERIC,
    imbalance_20 NUMERIC,
    spread_bps NUMERIC,
    sequence_id TEXT,
    inserted_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE feature_snapshots (
    ts_event TIMESTAMPTZ NOT NULL,
    instrument TEXT NOT NULL,
    cvd NUMERIC,
    delta_velocity NUMERIC,
    delta_acceleration NUMERIC,
    vpin NUMERIC,
    kyle_lambda NUMERIC,
    microprice NUMERIC,
    book_imbalance NUMERIC,
    absorption TEXT,
    spoof_regime TEXT,
    iceberg_side TEXT,
    whale_pressure NUMERIC,
    regime TEXT,
    alpha_strength NUMERIC,
    alpha_confidence NUMERIC,
    reason_codes JSONB,
    PRIMARY KEY(ts_event, instrument)
);

CREATE TABLE whale_events (
    ts_event TIMESTAMPTZ NOT NULL,
    instrument TEXT NOT NULL,
    event_type TEXT NOT NULL,
    side TEXT,
    size_usd NUMERIC,
    z_score NUMERIC,
    cluster_id INT,
    spoof_score NUMERIC,
    kq_modifier INT,
    details JSONB,
    PRIMARY KEY(ts_event, instrument, event_type)
);

CREATE TABLE experiment_runs (
    run_id UUID PRIMARY KEY,
    strategy_name TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    instrument TEXT NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    config_json JSONB NOT NULL,
    config_hash TEXT NOT NULL,
    data_source TEXT NOT NULL,
    git_commit TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
