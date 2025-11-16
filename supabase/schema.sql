-- Openfolio Database Schema
-- Run this in Supabase SQL Editor

-- ============================================================
-- (1) Raw Macro Time Series
-- ============================================================
CREATE TABLE IF NOT EXISTS macro_series (
  id BIGSERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  name TEXT,
  source TEXT,
  freq TEXT
);

CREATE TABLE IF NOT EXISTS macro_points (
  series_id BIGINT REFERENCES macro_series(id),
  ts DATE,
  value NUMERIC,
  revision_of DATE,
  raw_json JSONB,
  url TEXT,
  CONSTRAINT macro_points_unique UNIQUE (series_id, ts, revision_of)
);

-- ============================================================
-- (2) Normalized Features + Regime
-- ============================================================
CREATE TABLE IF NOT EXISTS macro_features_daily (
  date DATE,
  feature TEXT,
  value NUMERIC,
  details_json JSONB,
  PRIMARY KEY(date, feature)
);

CREATE TABLE IF NOT EXISTS macro_regime_daily (
  date DATE PRIMARY KEY,
  growth_z NUMERIC,
  inflation_z NUMERIC,
  liquidity_z NUMERIC,
  rates_z NUMERIC,
  regime TEXT,
  details_json JSONB
);

-- ============================================================
-- (3) EOD Prices (Sector ETFs / Individual Stocks)
-- ============================================================
CREATE TABLE IF NOT EXISTS prices_daily (
  ticker TEXT,
  date DATE,
  open NUMERIC,
  high NUMERIC,
  low NUMERIC,
  close NUMERIC,
  adj_close NUMERIC,
  volume BIGINT,
  source TEXT,
  raw_json JSONB,
  PRIMARY KEY(ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_prices_ticker ON prices_daily(ticker);
CREATE INDEX IF NOT EXISTS idx_prices_date ON prices_daily(date);

-- ============================================================
-- (4) Sector Scores
-- ============================================================
CREATE TABLE IF NOT EXISTS sector_scores (
  date DATE,
  sector TEXT,
  score NUMERIC,
  components_json JSONB,
  PRIMARY KEY(date, sector)
);

CREATE INDEX IF NOT EXISTS idx_sector_scores_date ON sector_scores(date);

-- ============================================================
-- (5) Event Documents + NLP
-- ============================================================
CREATE TABLE IF NOT EXISTS event_docs (
  id BIGSERIAL PRIMARY KEY,
  ticker TEXT,
  dt TIMESTAMPTZ,
  type TEXT,
  url TEXT,
  title TEXT,
  body TEXT,
  CONSTRAINT event_docs_unique UNIQUE (ticker, dt, type)
);

CREATE INDEX IF NOT EXISTS idx_events_ticker ON event_docs(ticker);
CREATE INDEX IF NOT EXISTS idx_events_dt ON event_docs(dt);

CREATE TABLE IF NOT EXISTS event_nlp (
  doc_id BIGINT PRIMARY KEY REFERENCES event_docs(id),
  sentiment REAL,
  guidance TEXT,
  surprise_eps REAL,
  topics TEXT[],
  quotes JSONB,
  model TEXT,
  version TEXT
);

-- ============================================================
-- (6) Technical Analysis (Daily)
-- ============================================================
CREATE TABLE IF NOT EXISTS ta_daily (
  ticker TEXT,
  date DATE,
  rsi14 NUMERIC,
  macd NUMERIC,
  macd_signal NUMERIC,
  sma20 NUMERIC,
  sma50 NUMERIC,
  sma200 NUMERIC,
  atr14 NUMERIC,
  flags JSONB,
  PRIMARY KEY(ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_ta_ticker ON ta_daily(ticker);
CREATE INDEX IF NOT EXISTS idx_ta_date ON ta_daily(date);

-- ============================================================
-- (7) Screening Steps + Rankings
-- ============================================================
CREATE TABLE IF NOT EXISTS screening_steps (
  date DATE,
  ticker TEXT,
  step TEXT,
  pass BOOLEAN,
  score NUMERIC,
  evidence_json JSONB,
  PRIMARY KEY(date, ticker, step)
);

CREATE INDEX IF NOT EXISTS idx_screening_date ON screening_steps(date);
CREATE INDEX IF NOT EXISTS idx_screening_ticker ON screening_steps(ticker);

CREATE TABLE IF NOT EXISTS rankings (
  date DATE,
  ticker TEXT,
  total_score NUMERIC,
  components_json JSONB,
  decision TEXT,
  version TEXT,
  PRIMARY KEY(date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_rankings_date ON rankings(date);

-- ============================================================
-- (8) Multi AI Agents + Weights/Performance + Decision Logs
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_agents (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  description TEXT,
  prompt_template TEXT,
  risk_profile TEXT,
  weights_json JSONB
);

CREATE TABLE IF NOT EXISTS ai_weights_history (
  date DATE,
  agent_id INT REFERENCES ai_agents(id),
  ticker TEXT,  -- includes 'CASH'
  weight NUMERIC,
  reason_json JSONB,
  PRIMARY KEY(date, agent_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_ai_weights_date ON ai_weights_history(date);
CREATE INDEX IF NOT EXISTS idx_ai_weights_agent ON ai_weights_history(agent_id);

CREATE TABLE IF NOT EXISTS ai_performance (
  date DATE,
  agent_id INT REFERENCES ai_agents(id),
  nav NUMERIC,
  cash_weight NUMERIC,
  pnl_daily NUMERIC,
  sharpe NUMERIC,
  mdd NUMERIC,
  benchmark_return NUMERIC,
  PRIMARY KEY(date, agent_id)
);

CREATE INDEX IF NOT EXISTS idx_ai_perf_date ON ai_performance(date);
CREATE INDEX IF NOT EXISTS idx_ai_perf_agent ON ai_performance(agent_id);

CREATE TABLE IF NOT EXISTS decision_logs (
  date DATE,
  stage TEXT,
  agent TEXT,
  input_ref JSONB,
  computed_ref JSONB,
  decision JSONB,
  rationale_md TEXT,
  PRIMARY KEY(date, stage, agent)
);

CREATE INDEX IF NOT EXISTS idx_decision_date ON decision_logs(date);

-- ============================================================
-- ADD UNIQUE CONSTRAINTS TO EXISTING TABLES
-- (Run these after initial schema creation if tables already exist)
-- ============================================================

-- Add unique constraint to macro_points table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'macro_points_unique'
        AND conrelid = 'macro_points'::regclass
    ) THEN
        ALTER TABLE macro_points
        ADD CONSTRAINT macro_points_unique UNIQUE (series_id, ts, revision_of);
    END IF;
END $$;

-- Add unique constraint to event_docs table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'event_docs_unique'
        AND conrelid = 'event_docs'::regclass
    ) THEN
        ALTER TABLE event_docs
        ADD CONSTRAINT event_docs_unique UNIQUE (ticker, dt, type);
    END IF;
END $$;
