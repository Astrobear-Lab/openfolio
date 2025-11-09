"""Database utilities for ETL pipeline"""
import os
import psycopg2
from psycopg2.extras import execute_values, Json
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict, Any, Optional

load_dotenv()

def get_connection():
    """Get database connection"""
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def upsert_macro_series(conn, code: str, name: str, source: str = "FRED", freq: str = "M") -> int:
    """Upsert macro series and return ID"""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO macro_series (code, name, source, freq)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name, source = EXCLUDED.source, freq = EXCLUDED.freq
            RETURNING id
            """,
            (code, name, source, freq)
        )
        return cur.fetchone()[0]

def upsert_macro_points(conn, series_id: int, points: List[Dict[str, Any]]):
    """Bulk upsert macro points"""
    if not points:
        return

    with conn.cursor() as cur:
        values = [
            (
                series_id,
                p["date"],
                p["value"],
                p.get("revision_of"),
                Json(p.get("raw_json", {})),
                p.get("url"),
            )
            for p in points
        ]

        execute_values(
            cur,
            """
            INSERT INTO macro_points (series_id, ts, value, revision_of, raw_json, url)
            VALUES %s
            ON CONFLICT (series_id, ts, revision_of) DO UPDATE
            SET value = EXCLUDED.value, raw_json = EXCLUDED.raw_json, url = EXCLUDED.url
            """,
            values,
            template="(%s, %s, %s, COALESCE(%s, %s), %s, %s)"
        )
    conn.commit()

def upsert_macro_features(conn, date, features: Dict[str, Any]):
    """Upsert macro features for a date"""
    with conn.cursor() as cur:
        for feature, data in features.items():
            cur.execute(
                """
                INSERT INTO macro_features_daily (date, feature, value, details_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (date, feature) DO UPDATE
                SET value = EXCLUDED.value, details_json = EXCLUDED.details_json
                """,
                (date, feature, data.get("value"), Json(data.get("details", {})))
            )
    conn.commit()

def upsert_regime(conn, date, regime_data: Dict[str, Any]):
    """Upsert regime classification"""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO macro_regime_daily
            (date, growth_z, inflation_z, liquidity_z, rates_z, regime, details_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE
            SET growth_z = EXCLUDED.growth_z,
                inflation_z = EXCLUDED.inflation_z,
                liquidity_z = EXCLUDED.liquidity_z,
                rates_z = EXCLUDED.rates_z,
                regime = EXCLUDED.regime,
                details_json = EXCLUDED.details_json
            """,
            (
                date,
                regime_data.get("growth_z"),
                regime_data.get("inflation_z"),
                regime_data.get("liquidity_z"),
                regime_data.get("rates_z"),
                regime_data.get("regime"),
                Json(regime_data.get("details", {}))
            )
        )
    conn.commit()

def upsert_prices(conn, prices: List[Dict[str, Any]]):
    """Bulk upsert price data"""
    if not prices:
        return

    with conn.cursor() as cur:
        values = [
            (
                p["ticker"],
                p["date"],
                p.get("open"),
                p.get("high"),
                p.get("low"),
                p.get("close"),
                p.get("adj_close"),
                p.get("volume"),
                p.get("source", "yfinance"),
                Json(p.get("raw_json", {}))
            )
            for p in prices
        ]

        execute_values(
            cur,
            """
            INSERT INTO prices_daily
            (ticker, date, open, high, low, close, adj_close, volume, source, raw_json)
            VALUES %s
            ON CONFLICT (ticker, date) DO UPDATE
            SET open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                close = EXCLUDED.close, adj_close = EXCLUDED.adj_close,
                volume = EXCLUDED.volume, raw_json = EXCLUDED.raw_json
            """,
            values
        )
    conn.commit()

def upsert_sector_scores(conn, date, scores: List[Dict[str, Any]]):
    """Upsert sector scores"""
    with conn.cursor() as cur:
        for score in scores:
            cur.execute(
                """
                INSERT INTO sector_scores (date, sector, score, components_json)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (date, sector) DO UPDATE
                SET score = EXCLUDED.score, components_json = EXCLUDED.components_json
                """,
                (date, score["sector"], score["score"], Json(score.get("components", {})))
            )
    conn.commit()

def upsert_ai_weights(conn, date: datetime, agent_id: int, weights: Dict[str, Dict[str, Any]]):
    """Upsert AI agent weights (including CASH)"""
    with conn.cursor() as cur:
        for ticker, data in weights.items():
            cur.execute(
                """
                INSERT INTO ai_weights_history (date, agent_id, ticker, weight, reason_json)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (date, agent_id, ticker) DO UPDATE
                SET weight = EXCLUDED.weight, reason_json = EXCLUDED.reason_json
                """,
                (date, agent_id, ticker, data["weight"], Json(data.get("reason", {})))
            )
    conn.commit()

def upsert_ai_performance(conn, date: datetime, agent_id: int, perf: Dict[str, Any]):
    """Upsert AI agent performance metrics"""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ai_performance
            (date, agent_id, nav, cash_weight, pnl_daily, sharpe, mdd, benchmark_return)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date, agent_id) DO UPDATE
            SET nav = EXCLUDED.nav, cash_weight = EXCLUDED.cash_weight,
                pnl_daily = EXCLUDED.pnl_daily, sharpe = EXCLUDED.sharpe,
                mdd = EXCLUDED.mdd, benchmark_return = EXCLUDED.benchmark_return
            """,
            (
                date, agent_id,
                perf.get("nav"),
                perf.get("cash_weight"),
                perf.get("pnl_daily"),
                perf.get("sharpe"),
                perf.get("mdd"),
                perf.get("benchmark_return")
            )
        )
    conn.commit()

def upsert_decision_log(conn, date: datetime, stage: str, agent: str, log: Dict[str, Any]):
    """Upsert decision log"""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO decision_logs
            (date, stage, agent, input_ref, computed_ref, decision, rationale_md)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date, stage, agent) DO UPDATE
            SET input_ref = EXCLUDED.input_ref,
                computed_ref = EXCLUDED.computed_ref,
                decision = EXCLUDED.decision,
                rationale_md = EXCLUDED.rationale_md
            """,
            (
                date, stage, agent,
                Json(log.get("input_ref", {})),
                Json(log.get("computed_ref", {})),
                Json(log.get("decision", {})),
                log.get("rationale_md", "")
            )
        )
    conn.commit()
