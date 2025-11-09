#!/usr/bin/env python3
"""
Main ETL pipeline runner
Executes all ETL steps in sequence
"""
import os
import sys
import json
import logging
from datetime import datetime, date
from dotenv import load_dotenv

import db
from seed_data import (
    generate_macro_points,
    generate_prices,
    calculate_z_score,
    classify_regime,
    generate_event_docs
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

def load_config():
    """Load ETL configuration"""
    with open("config.json", "r") as f:
        return json.load(f)

def run_macro_etl(conn, config):
    """Step 1: Fetch and store macro data"""
    logger.info("=== Step 1: Macro Data ETL ===")

    use_seed = os.getenv("USE_SEED_DATA", "true").lower() == "true"

    for series_config in config["macro_series"]:
        code = series_config["code"]
        logger.info(f"Processing series: {code}")

        # Upsert series
        series_id = db.upsert_macro_series(
            conn,
            code=code,
            name=series_config["name"],
            source=series_config["source"],
            freq=series_config["freq"]
        )

        # Generate or fetch points
        if use_seed:
            points = generate_macro_points(code, days=365*3)  # 3 years
        else:
            # TODO: Implement real FRED API fetch
            logger.warning(f"Real API not implemented for {code}, using seed data")
            points = generate_macro_points(code, days=365*3)

        # Store points
        db.upsert_macro_points(conn, series_id, points)
        logger.info(f"  Stored {len(points)} points for {code}")

def run_features_regime_etl(conn, config):
    """Step 2: Calculate features and regime"""
    logger.info("=== Step 2: Features & Regime Calculation ===")

    # For simplicity, calculate for latest date
    # In production, would calculate for all dates
    today = date.today()

    # Mock feature calculation
    features = {
        "growth_composite": {
            "value": 1.2,
            "details": {
                "inputs": ["INDPRO", "PAYEMS"],
                "method": "z-score average",
                "window": 36
            }
        },
        "inflation_composite": {
            "value": -0.5,
            "details": {
                "inputs": ["CPIAUCSL", "CPILFESL"],
                "method": "z-score average",
                "window": 36
            }
        },
        "liquidity_composite": {
            "value": 0.8,
            "details": {
                "inputs": ["M2SL", "WALCL"],
                "method": "z-score average",
                "window": 36
            }
        },
        "rates_composite": {
            "value": -0.3,
            "details": {
                "inputs": ["DGS10", "DGS2"],
                "method": "z-score spread",
                "window": 36
            }
        }
    }

    db.upsert_macro_features(conn, today, features)

    # Classify regime
    regime_data = {
        "growth_z": 1.2,
        "inflation_z": -0.5,
        "liquidity_z": 0.8,
        "rates_z": -0.3,
        "regime": classify_regime(1.2, -0.5),
        "details": {
            "rules": config["regime_rules"],
            "calculated_at": datetime.now().isoformat()
        }
    }

    db.upsert_regime(conn, today, regime_data)
    logger.info(f"  Regime: {regime_data['regime']}")

def run_prices_etl(conn, config):
    """Step 3: Fetch EOD prices"""
    logger.info("=== Step 3: Prices ETL ===")

    use_seed = os.getenv("USE_SEED_DATA", "true").lower() == "true"

    all_tickers = [s["ticker"] for s in config["sector_etfs"]] + config["sample_stocks"]

    for ticker in all_tickers:
        logger.info(f"Processing prices for: {ticker}")

        if use_seed:
            prices = generate_prices(ticker, days=365*2)  # 2 years
        else:
            # TODO: Implement real price API fetch
            logger.warning(f"Real API not implemented for {ticker}, using seed data")
            prices = generate_prices(ticker, days=365*2)

        db.upsert_prices(conn, prices)
        logger.info(f"  Stored {len(prices)} price points for {ticker}")

def run_sector_scoring_etl(conn, config):
    """Step 4: Calculate sector scores"""
    logger.info("=== Step 4: Sector Scoring ===")

    today = date.today()
    scores = []

    for sector in config["sector_etfs"]:
        ticker = sector["ticker"]

        # Mock scoring calculation
        score_value = round(random.uniform(-5, 10), 2)

        scores.append({
            "sector": ticker,
            "score": score_value,
            "components": {
                "ret1m_z": round(random.uniform(-2, 2), 2),
                "ret3m_z": round(random.uniform(-2, 2), 2),
                "ret6m_z": round(random.uniform(-2, 2), 2),
                "vol3m_z": round(random.uniform(-1, 1), 2),
                "regime_tilt": round(random.uniform(-1, 2), 2),
                "formula": "z(ret1m) + z(ret3m) + 0.5*z(ret6m) - 0.5*z(vol3m) + regime_tilt"
            }
        })

    db.upsert_sector_scores(conn, today, scores)
    logger.info(f"  Scored {len(scores)} sectors")

def run_events_etl(conn, config):
    """Step 5: Fetch and process events"""
    logger.info("=== Step 5: Events ETL ===")

    # Process sample stocks only
    for ticker in config["sample_stocks"][:5]:  # Limit for demo
        logger.info(f"Processing events for: {ticker}")

        events = generate_event_docs(ticker, count=3)

        for event in events:
            with conn.cursor() as cur:
                # Insert event doc
                cur.execute(
                    """
                    INSERT INTO event_docs (ticker, dt, type, url, title, body)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (event["ticker"], event["dt"], event["type"],
                     event["url"], event["title"], event["body"])
                )
                doc_id = cur.fetchone()[0]

                # Insert NLP analysis
                cur.execute(
                    """
                    INSERT INTO event_nlp
                    (doc_id, sentiment, guidance, surprise_eps, topics, quotes, model, version)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (doc_id) DO UPDATE
                    SET sentiment = EXCLUDED.sentiment,
                        guidance = EXCLUDED.guidance,
                        surprise_eps = EXCLUDED.surprise_eps,
                        topics = EXCLUDED.topics,
                        quotes = EXCLUDED.quotes
                    """,
                    (doc_id, event["sentiment"], event["guidance"],
                     event["surprise_eps"], event["topics"],
                     json.dumps({"quotes": event["quotes"]}),
                     "FinBERT-seed", "1.0.0")
                )

        conn.commit()
        logger.info(f"  Stored {len(events)} events for {ticker}")

def run_ai_allocation_etl(conn, config):
    """Step 6: Run AI agent allocations"""
    logger.info("=== Step 6: AI Agent Allocation ===")

    today = date.today()

    # Get AI agents
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, risk_profile FROM ai_agents ORDER BY id")
        agents = cur.fetchall()

    for agent_id, agent_name, risk_profile in agents:
        logger.info(f"Processing agent: {agent_name}")

        # Mock allocation
        if agent_name == "Aggressive":
            weights = {
                "AAPL": {"weight": 12.5, "reason": {"momentum": "strong", "events": "positive"}},
                "MSFT": {"weight": 11.8, "reason": {"momentum": "strong", "quality": "high"}},
                "NVDA": {"weight": 10.2, "reason": {"momentum": "very strong"}},
                "CASH": {"weight": 5.2, "reason": {"minimum_buffer": True}}
            }
            perf = {"nav": 1.324, "cash_weight": 5.2, "pnl_daily": 0.015,
                   "sharpe": 1.85, "mdd": -0.182, "benchmark_return": 0.15}
        elif agent_name == "Balanced":
            weights = {
                "AAPL": {"weight": 8.5, "reason": {"balanced": True}},
                "MSFT": {"weight": 8.2, "reason": {"balanced": True}},
                "JNJ": {"weight": 6.5, "reason": {"quality": "high", "defensive": True}},
                "CASH": {"weight": 15.0, "reason": {"buffer": True}}
            }
            perf = {"nav": 1.185, "cash_weight": 15.0, "pnl_daily": 0.008,
                   "sharpe": 1.42, "mdd": -0.128, "benchmark_return": 0.15}
        else:  # Defensive
            weights = {
                "JNJ": {"weight": 10.5, "reason": {"quality": "high", "defensive": True}},
                "PG": {"weight": 9.8, "reason": {"stable": True, "dividend": True}},
                "CASH": {"weight": 35.0, "reason": {"capital_preservation": True}}
            }
            perf = {"nav": 1.095, "cash_weight": 35.0, "pnl_daily": 0.004,
                   "sharpe": 1.15, "mdd": -0.072, "benchmark_return": 0.15}

        # Store weights and performance
        db.upsert_ai_weights(conn, today, agent_id, weights)
        db.upsert_ai_performance(conn, today, agent_id, perf)

        # Store decision log
        db.upsert_decision_log(conn, today, "allocation", agent_name, {
            "input_ref": {"regime": "Goldilocks", "sector_scores": "available"},
            "computed_ref": {"total_weight": sum(w["weight"] for w in weights.values())},
            "decision": weights,
            "rationale_md": f"Allocated {agent_name} portfolio based on {risk_profile} risk profile"
        })

        logger.info(f"  Allocated {len(weights)} positions for {agent_name}")

def main():
    """Main ETL orchestrator"""
    logger.info("========================================")
    logger.info("Starting Openfolio ETL Pipeline")
    logger.info(f"Run time: {datetime.now()}")
    logger.info("========================================")

    # Load configuration
    config = load_config()

    # Connect to database
    conn = db.get_connection()

    try:
        # Run ETL steps
        run_macro_etl(conn, config)
        run_features_regime_etl(conn, config)
        run_prices_etl(conn, config)
        run_sector_scoring_etl(conn, config)
        run_events_etl(conn, config)
        run_ai_allocation_etl(conn, config)

        logger.info("========================================")
        logger.info("ETL Pipeline Completed Successfully")
        logger.info("========================================")

    except Exception as e:
        logger.error(f"ETL Pipeline Failed: {e}", exc_info=True)
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    import random  # Needed for mock scoring
    main()
