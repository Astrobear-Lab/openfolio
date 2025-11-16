"""Database utilities for ETL pipeline using Supabase"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# Global Supabase client
_supabase_client: Optional[Client] = None


def get_supabase() -> Client:
    """Get or create Supabase client"""
    global _supabase_client

    if _supabase_client is None:
        # Reload .env to ensure we have latest values
        load_dotenv(override=True)

        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")

        # Debug logging
        logger.debug(f"SUPABASE_URL: {supabase_url[:30]}..." if supabase_url else "None")
        logger.debug(f"SUPABASE_KEY length: {len(supabase_key) if supabase_key else 0}")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "Supabase credentials not found. "
                "Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env"
            )

        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized")

    return _supabase_client


def get_connection():
    """
    Compatibility function for existing code.
    Returns Supabase client instead of psycopg2 connection.
    """
    return get_supabase()


def upsert_macro_series(conn: Client, code: str, name: str, source: str = "FRED", freq: str = "M") -> int:
    """Upsert macro series and return ID"""
    data = {
        "code": code,
        "name": name,
        "source": source,
        "freq": freq
    }

    result = conn.table("macro_series").upsert(data, on_conflict="code").execute()

    if result.data and len(result.data) > 0:
        return result.data[0]["id"]

    # If upsert doesn't return data, fetch the record
    result = conn.table("macro_series").select("id").eq("code", code).execute()
    return result.data[0]["id"] if result.data else None


def upsert_macro_points(conn: Client, series_id: int, points: List[Dict[str, Any]]):
    """Bulk upsert macro points"""
    if not points:
        return

    # Prepare data for Supabase
    data = [
        {
            "series_id": series_id,
            "ts": p["date"].isoformat() if isinstance(p["date"], date) else p["date"],
            "value": p["value"],
            "revision_of": p.get("revision_of"),
            "raw_json": p.get("raw_json", {}),
            "url": p.get("url")
        }
        for p in points
    ]

    # Supabase upsert - automatically handles conflicts
    result = conn.table("macro_points").upsert(data, on_conflict="series_id,ts,revision_of").execute()
    logger.info(f"Upserted {len(data)} macro points for series {series_id}")


def upsert_macro_features(conn: Client, date: date, features: Dict[str, Any]):
    """Upsert macro features for a date"""
    data = []

    for feature, feature_data in features.items():
        data.append({
            "date": date.isoformat() if isinstance(date, (datetime, date)) else date,
            "feature": feature,
            "value": feature_data.get("value"),
            "details_json": feature_data.get("details", {})
        })

    result = conn.table("macro_features_daily").upsert(data, on_conflict="date,feature").execute()
    logger.info(f"Upserted {len(data)} macro features for {date}")


def upsert_regime(conn: Client, date: date, regime_data: Dict[str, Any]):
    """Upsert regime classification"""
    data = {
        "date": date.isoformat() if isinstance(date, (datetime, date)) else date,
        "growth_z": regime_data.get("growth_z"),
        "inflation_z": regime_data.get("inflation_z"),
        "liquidity_z": regime_data.get("liquidity_z"),
        "rates_z": regime_data.get("rates_z"),
        "regime": regime_data.get("regime"),
        "details_json": regime_data.get("details", {})
    }

    result = conn.table("macro_regime_daily").upsert(data, on_conflict="date").execute()
    logger.info(f"Upserted regime for {date}: {regime_data.get('regime')}")


def upsert_prices(conn: Client, prices: List[Dict[str, Any]]):
    """Bulk upsert price data"""
    if not prices:
        return

    # Prepare data
    data = [
        {
            "ticker": p["ticker"],
            "date": p["date"].isoformat() if isinstance(p["date"], date) else p["date"],
            "open": p.get("open"),
            "high": p.get("high"),
            "low": p.get("low"),
            "close": p.get("close"),
            "adj_close": p.get("adj_close"),
            "volume": p.get("volume"),
            "source": p.get("source", "yfinance"),
            "raw_json": p.get("raw_json", {})
        }
        for p in prices
    ]

    # Batch upsert (Supabase handles up to 1000 rows per request)
    batch_size = 1000
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        result = conn.table("prices_daily").upsert(batch, on_conflict="ticker,date").execute()
        logger.info(f"Upserted batch {i//batch_size + 1}: {len(batch)} price records")


def upsert_sector_scores(conn: Client, date: date, scores: List[Dict[str, Any]]):
    """Upsert sector scores"""
    if not scores:
        return

    data = [
        {
            "date": date.isoformat() if isinstance(date, (datetime, date)) else date,
            "sector": score["sector"],
            "score": score["score"],
            "components_json": score.get("components", {})
        }
        for score in scores
    ]

    result = conn.table("sector_scores").upsert(data, on_conflict="date,sector").execute()
    logger.info(f"Upserted {len(data)} sector scores for {date}")


def upsert_ta_indicators(conn: Client, indicators: List[Dict[str, Any]]):
    """Bulk upsert technical indicators"""
    if not indicators:
        return

    # Prepare data
    data = [
        {
            "ticker": ind["ticker"],
            "date": ind["date"].isoformat() if isinstance(ind["date"], date) else ind["date"],
            "rsi_14": ind.get("rsi_14"),
            "macd_12_26_9": ind.get("macd_12_26_9"),
            "macd_signal": ind.get("macd_signal"),
            "sma_20": ind.get("sma_20"),
            "sma_50": ind.get("sma_50"),
            "sma_200": ind.get("sma_200"),
            "atr_14": ind.get("atr_14"),
            "details_json": ind.get("details_json", {})
        }
        for ind in indicators
    ]

    # Batch upsert
    batch_size = 1000
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        result = conn.table("ta_daily").upsert(batch, on_conflict="ticker,date").execute()
        logger.info(f"Upserted batch {i//batch_size + 1}: {len(batch)} TA indicators")


def upsert_ai_weights(conn: Client, date: datetime, agent_id: int, weights: Dict[str, Dict[str, Any]]):
    """Upsert AI agent weights (including CASH)"""
    data = [
        {
            "date": date.isoformat() if isinstance(date, (datetime, date)) else date,
            "agent_id": agent_id,
            "ticker": ticker,
            "weight": weight_data["weight"],
            "reason_json": weight_data.get("reason", {})
        }
        for ticker, weight_data in weights.items()
    ]

    result = conn.table("ai_weights_history").upsert(data, on_conflict="date,agent_id,ticker").execute()
    logger.info(f"Upserted {len(data)} weights for agent {agent_id}")


def upsert_ai_performance(conn: Client, date: datetime, agent_id: int, perf: Dict[str, Any]):
    """Upsert AI agent performance metrics"""
    data = {
        "date": date.isoformat() if isinstance(date, (datetime, date)) else date,
        "agent_id": agent_id,
        "nav": perf.get("nav"),
        "cash_weight": perf.get("cash_weight"),
        "pnl_daily": perf.get("pnl_daily"),
        "sharpe": perf.get("sharpe"),
        "mdd": perf.get("mdd"),
        "benchmark_return": perf.get("benchmark_return")
    }

    result = conn.table("ai_performance").upsert(data, on_conflict="date,agent_id").execute()
    logger.info(f"Upserted performance for agent {agent_id}")


def upsert_decision_log(conn: Client, date: datetime, stage: str, agent: str, log: Dict[str, Any]):
    """Upsert decision log"""
    data = {
        "date": date.isoformat() if isinstance(date, (datetime, date)) else date,
        "stage": stage,
        "agent": agent,
        "input_ref": log.get("input_ref", {}),
        "computed_ref": log.get("computed_ref", {}),
        "decision": log.get("decision", {}),
        "rationale_md": log.get("rationale_md", "")
    }

    result = conn.table("decision_logs").upsert(data, on_conflict="date,stage,agent").execute()
    logger.info(f"Upserted decision log for {agent} - {stage}")


# Helper functions for read operations
def fetch_macro_series(conn: Client, code: str) -> Optional[Dict]:
    """Fetch a macro series by code"""
    result = conn.table("macro_series").select("*").eq("code", code).execute()
    return result.data[0] if result.data else None


def fetch_latest_regime(conn: Client) -> Optional[str]:
    """Fetch the latest regime classification"""
    result = conn.table("macro_regime_daily").select("regime").order("date", desc=True).limit(1).execute()
    return result.data[0]["regime"] if result.data else None


def fetch_ai_agents(conn: Client) -> List[Dict]:
    """Fetch all AI agents"""
    result = conn.table("ai_agents").select("id, name, risk_profile").order("id").execute()
    return result.data if result.data else []


def fetch_prices(conn: Client, ticker: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict]:
    """Fetch price data for a ticker"""
    query = conn.table("prices_daily").select("*").eq("ticker", ticker).order("date")

    if start_date:
        query = query.gte("date", start_date.isoformat())
    if end_date:
        query = query.lte("date", end_date.isoformat())

    result = query.execute()
    return result.data if result.data else []


def fetch_macro_points(conn: Client, series_code: str, start_date: Optional[date] = None) -> List[Dict]:
    """Fetch macro points for a series"""
    # First get series ID
    series = fetch_macro_series(conn, series_code)
    if not series:
        return []

    query = conn.table("macro_points").select("*").eq("series_id", series["id"]).order("ts")

    if start_date:
        query = query.gte("ts", start_date.isoformat())

    result = query.execute()
    return result.data if result.data else []


def fetch_sector_scores(conn: Client, date: date) -> List[Dict]:
    """Fetch sector scores for a specific date"""
    result = conn.table("sector_scores").select("*").eq("date", date.isoformat()).order("score", desc=True).execute()
    return result.data if result.data else []
