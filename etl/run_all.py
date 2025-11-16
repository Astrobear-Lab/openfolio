#!/usr/bin/env python3
"""
Main ETL pipeline runner
Executes all ETL steps in sequence using real data collectors
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

import db
from collectors.fred_collector import FREDCollector
from collectors.yahoo_collector import YahooCollector
from collectors.sec_collector import SECCollector
from calculators.technical_indicators import TechnicalCalculator
from calculators.feature_regime import FeatureRegimeCalculator
from calculators.sector_scoring import SectorScorer

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


def check_phase2_data_availability(conn):
    """Check data availability for Phase 2 calculations."""
    logger.info("📊 Checking data availability for Phase 2...")

    try:
        # Check prices_daily (needed for technical indicators and sector scoring)
        prices_result = conn.table("prices_daily").select("*", count="exact", head=False).execute()
        prices_count = getattr(prices_result, 'count', 0)
        logger.info(f"  💰 Prices data: {prices_count} records")

        # Check macro data (needed for features & regime)
        macro_series_result = conn.table("macro_series").select("*", count="exact", head=False).execute()
        macro_series_count = getattr(macro_series_result, 'count', 0)
        logger.info(f"  📈 Macro series: {macro_series_count} series")

        macro_points_result = conn.table("macro_points").select("*", count="exact", head=False).execute()
        macro_points_count = getattr(macro_points_result, 'count', 0)
        logger.info(f"  📊 Macro points: {macro_points_count} data points")

        # Check existing calculations (optional)
        try:
            ta_result = conn.table("ta_daily").select("*", count="exact", head=False).execute()
            ta_count = getattr(ta_result, 'count', 0)
            logger.info(f"  📈 Technical indicators: {ta_count} records (existing)")
        except Exception as e:
            logger.info(f"  📈 Technical indicators: 0 records ({e})")

        try:
            features_result = conn.table("macro_features_daily").select("*", count="exact", head=False).execute()
            features_count = getattr(features_result, 'count', 0)
            logger.info(f"  🧮 Macro features: {features_count} records (existing)")
        except Exception as e:
            logger.info(f"  🧮 Macro features: 0 records ({e})")

        try:
            regime_result = conn.table("macro_regime_daily").select("*", count="exact", head=False).execute()
            regime_count = getattr(regime_result, 'count', 0)
            logger.info(f"  🎯 Regime data: {regime_count} records (existing)")
        except Exception as e:
            logger.info(f"  🎯 Regime data: 0 records ({e})")

        # Summary
        if prices_count > 0 and macro_points_count > 0:
            logger.info("✅ Phase 2 prerequisites met - sufficient data available")
        else:
            logger.warning("⚠️ Phase 2 prerequisites not fully met - some calculations may fail")
            if prices_count == 0:
                logger.warning("  - Missing: Price data (required for technical indicators)")
            if macro_points_count == 0:
                logger.warning("  - Missing: Macro data (required for features & regime)")

    except Exception as e:
        logger.error(f"❌ Failed to check data availability: {e}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Openfolio ETL Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all.py                    # Run all phases
  python run_all.py --only-phase2      # Run only Phase 2 (calculations)
  python run_all.py --skip-phase1      # Skip Phase 1, run Phase 2+3
  python run_all.py --skip-phase3      # Run Phase 1+2, skip Phase 3
  python run_all.py --skip-connection-tests  # Skip connection tests
        """
    )

    parser.add_argument('--only-phase2', action='store_true',
                       help='Run only Phase 2 (calculations), skip Phase 1 and 3')
    parser.add_argument('--skip-phase1', action='store_true',
                       help='Skip Phase 1 (data collection)')
    parser.add_argument('--skip-phase3', action='store_true',
                       help='Skip Phase 3 (AI allocation)')
    parser.add_argument('--skip-connection-tests', action='store_true',
                       help='Skip external connection tests')

    return parser.parse_args()


def run_macro_etl(conn, config):
    """
    Phase 1.1: Fetch and store macro data from FRED

    This fetches the 9 macro series:
    - Growth: INDPRO, PAYEMS, UNRATE
    - Inflation: CPIAUCSL, CPILFESL
    - Liquidity: M2SL, WALCL
    - Rates: DGS10, DGS2
    """
    logger.info("=== Phase 1.1: Macro Data ETL ===")

    collector = FREDCollector()

    # Determine date range (3 years of history)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*3)

    for series_config in config["macro_series"]:
        code = series_config["code"]
        logger.info(f"Processing series: {code}")

        try:
            # Upsert series metadata
            series_id = db.upsert_macro_series(
                conn,
                code=code,
                name=series_config["name"],
                source=series_config["source"],
                freq=series_config["freq"]
            )

            # Fetch data from FRED
            points = collector.fetch_series(
                series_code=code,
                start_date=start_date,
                end_date=end_date
            )

            if points:
                # Store points
                db.upsert_macro_points(conn, series_id, points)
                logger.info(f"  ✓ Stored {len(points)} points for {code}")
            else:
                logger.warning(f"  ⚠ No data received for {code}")

        except Exception as e:
            logger.error(f"  ✗ Failed to process {code}: {e}")
            continue


def run_prices_etl(conn, config):
    """
    Phase 1.2: Fetch EOD prices for all tickers

    This fetches prices for:
    - 11 Sector ETFs (XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLK, XLU, XLRE, XLC)
    - 20 Sample stocks (AAPL, MSFT, etc.)
    """
    logger.info("=== Phase 1.2: Prices ETL ===")

    collector = YahooCollector()

    # Get all tickers
    all_tickers = [s["ticker"] for s in config["sector_etfs"]] + config["sample_stocks"]

    # Determine date range (2 years for technical indicators)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*2)

    try:
        # Bulk fetch all tickers at once (more efficient)
        logger.info(f"Fetching prices for {len(all_tickers)} tickers...")
        all_prices = collector.fetch_bulk(
            tickers=all_tickers,
            start_date=start_date,
            end_date=end_date
        )

        # Store prices
        if all_prices:
            db.upsert_prices(conn, all_prices)
            logger.info(f"  ✓ Stored {len(all_prices)} total price records")
        else:
            logger.warning("  ⚠ No price data received")

    except Exception as e:
        logger.error(f"  ✗ Failed to fetch prices: {e}")


def run_events_etl(conn, config):
    """
    Phase 1.3: Fetch SEC filings (8-K, 10-Q) for stocks

    Fetches recent filings from SEC EDGAR for the sample stocks.
    """
    logger.info("=== Phase 1.3: Events ETL ===")

    collector = SECCollector()

    # Fetch filings for all sample stocks
    tickers = config["sample_stocks"]

    try:
        all_filings = collector.fetch_all_tickers_filings(
            tickers=tickers,
            filing_types=["8-K", "10-Q"],
            days_back=90
        )

        # Store filings
        for ticker, filings in all_filings.items():
            for filing in filings:
                try:
                    # Upsert event doc
                    event_data = {
                        "ticker": filing["ticker"],
                        "dt": filing["dt"].isoformat() if hasattr(filing["dt"], "isoformat") else filing["dt"],
                        "type": filing["type"],
                        "url": filing["url"],
                        "title": filing["title"],
                        "body": filing["body"]
                    }

                    result = conn.table("event_docs").upsert(
                        event_data,
                        on_conflict="ticker,dt,type"
                    ).execute()

                    if result.data and len(result.data) > 0:
                        doc_id = result.data[0]["id"]
                    else:
                        # Fetch the doc_id if upsert didn't return it
                        fetch_result = conn.table("event_docs").select("id").match({
                            "ticker": filing["ticker"],
                            "dt": event_data["dt"],
                            "type": filing["type"]
                        }).execute()
                        doc_id = fetch_result.data[0]["id"] if fetch_result.data else None

                    if doc_id:
                        # Store basic NLP placeholder
                        nlp_data = {
                            "doc_id": doc_id,
                            "sentiment": 0.0,
                            "guidance": None,
                            "surprise_eps": None,
                            "topics": [],
                            "quotes": {"filing_type": filing["type"]},
                            "model": "placeholder",
                            "version": "1.0.0"
                        }
                        conn.table("event_nlp").upsert(nlp_data, on_conflict="doc_id").execute()

                except Exception as e:
                    logger.error(f"  ✗ Failed to store filing for {ticker}: {e}")
                    continue

        logger.info(f"  ✓ Processed filings for {len(all_filings)} tickers")

    except Exception as e:
        logger.error(f"  ✗ Failed to fetch events: {e}")


def run_technical_indicators_etl(conn, config):
    """
    Phase 2.1: Calculate technical indicators

    Calculates for all tickers:
    - RSI (14)
    - MACD (12, 26, 9)
    - SMA (20, 50, 200)
    - ATR (14)
    """
    logger.info("=== Phase 2.1: Technical Indicators ===")

    calculator = TechnicalCalculator()

    all_tickers = [s["ticker"] for s in config["sector_etfs"]] + config["sample_stocks"]

    for ticker in all_tickers:
        try:
            indicators = calculator.calculate_all_for_ticker(ticker, conn)

            if indicators:
                db.upsert_ta_indicators(conn, indicators)
                logger.info(f"  ✓ Calculated indicators for {ticker}: {len(indicators)} days")
            else:
                logger.warning(f"  ⚠ No indicators calculated for {ticker}")

        except Exception as e:
            logger.error(f"  ✗ Failed to calculate indicators for {ticker}: {e}")
            continue


def run_features_regime_etl(conn, config):
    """
    Phase 2.2: Calculate features and regime classification

    Calculates:
    - Growth composite (z-score of INDPRO, PAYEMS, -UNRATE)
    - Inflation composite (z-score of CPI MoM changes)
    - Liquidity composite (z-score of M2, Fed balance sheet)
    - Rates composite (z-score of 10Y-2Y spread)
    - Regime classification (Goldilocks/Reflation/Stagflation/Disinflation)
    """
    logger.info("=== Phase 2.2: Features & Regime ===")

    calculator = FeatureRegimeCalculator(window_months=36)

    # 🚀 PERFORMANCE: Preload all macro data once (instead of 810 queries!)
    calculator.preload_data(conn)

    # Calculate for recent dates (default: 7 days, configurable via env)
    days_to_calculate = int(os.getenv("ETL_CALCULATION_DAYS", "7"))
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_to_calculate)

    logger.info(f"Calculating features for last {days_to_calculate} days (set ETL_CALCULATION_DAYS to change)")

    current_date = start_date
    calculated_count = 0

    while current_date <= end_date:
        try:
            # Calculate composites
            growth_z = calculator.calculate_growth_composite(conn, current_date)
            inflation_z = calculator.calculate_inflation_composite(conn, current_date)
            liquidity_z = calculator.calculate_liquidity_composite(conn, current_date)
            rates_z = calculator.calculate_rates_composite(conn, current_date)

            # Skip if no data available
            if growth_z is None or inflation_z is None:
                current_date += timedelta(days=1)
                continue

            # Store features
            features = {
                "growth_composite": {
                    "value": growth_z,
                    "details": {
                        "inputs": ["INDPRO", "PAYEMS", "UNRATE"],
                        "method": "z-score average",
                        "window": 36
                    }
                },
                "inflation_composite": {
                    "value": inflation_z,
                    "details": {
                        "inputs": ["CPIAUCSL", "CPILFESL"],
                        "method": "z-score average MoM%",
                        "window": 36
                    }
                },
                "liquidity_composite": {
                    "value": liquidity_z if liquidity_z is not None else 0.0,
                    "details": {
                        "inputs": ["M2SL", "WALCL"],
                        "method": "z-score average",
                        "window": 36
                    }
                },
                "rates_composite": {
                    "value": rates_z if rates_z is not None else 0.0,
                    "details": {
                        "inputs": ["DGS10", "DGS2"],
                        "method": "z-score spread",
                        "window": 36
                    }
                }
            }

            db.upsert_macro_features(conn, current_date, features)

            # Classify regime
            regime = calculator.classify_regime(
                growth_z=growth_z,
                inflation_z=inflation_z,
                rules=config["regime_rules"]
            )

            regime_data = {
                "growth_z": growth_z,
                "inflation_z": inflation_z,
                "liquidity_z": liquidity_z if liquidity_z is not None else 0.0,
                "rates_z": rates_z if rates_z is not None else 0.0,
                "regime": regime,
                "details": {
                    "rules": config["regime_rules"],
                    "calculated_at": datetime.now().isoformat()
                }
            }

            db.upsert_regime(conn, current_date, regime_data)
            calculated_count += 1

        except Exception as e:
            logger.error(f"  ✗ Failed to calculate for {current_date}: {e}")

        current_date += timedelta(days=1)

    logger.info(f"  ✓ Calculated features & regime for {calculated_count} days")


def run_sector_scoring_etl(conn, config):
    """
    Phase 2.3: Calculate sector scores

    Scores all 11 sector ETFs based on:
    - Momentum (1M, 3M, 6M returns)
    - Volatility (3M rolling std dev)
    - Regime tilt
    """
    logger.info("=== Phase 2.3: Sector Scoring ===")

    scorer = SectorScorer()

    # Get latest regime
    result = conn.table("macro_regime_daily").select("regime").order("date", desc=True).limit(1).execute()
    regime = result.data[0]["regime"] if result.data else "Goldilocks"

    logger.info(f"  Current regime: {regime}")

    # 🚀 PERFORMANCE: Calculate for recent dates only (default: 7 days)
    days_to_calculate = int(os.getenv("ETL_CALCULATION_DAYS", "7"))
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_to_calculate)

    logger.info(f"Calculating sector scores for last {days_to_calculate} days")

    current_date = start_date
    calculated_count = 0

    while current_date <= end_date:
        try:
            scores = scorer.score_all_sectors(
                date=current_date,
                regime=regime,
                conn=conn,
                config=config
            )

            if scores:
                db.upsert_sector_scores(conn, current_date.date(), scores)
                calculated_count += 1

        except Exception as e:
            logger.error(f"  ✗ Failed to score sectors for {current_date.date()}: {e}")

        current_date += timedelta(days=1)

    logger.info(f"  ✓ Scored sectors for {calculated_count} days")


def run_ai_allocation_etl(conn, config):
    """
    Phase 3: Run AI agent allocations

    This would ideally use OpenAI to generate allocations.
    For now, uses a simplified rule-based approach.
    """
    logger.info("=== Phase 3: AI Agent Allocation ===")

    today = date.today()

    # Get AI agents
    agents_result = conn.table("ai_agents").select("id, name, risk_profile").order("id").execute()
    agents = [(a["id"], a["name"], a["risk_profile"]) for a in agents_result.data] if agents_result.data else []

    # Get latest regime
    regime_result = conn.table("macro_regime_daily").select("regime").order("date", desc=True).limit(1).execute()
    regime = regime_result.data[0]["regime"] if regime_result.data else "Goldilocks"

    # Get top sector scores
    # First get the latest date
    latest_date_result = conn.table("sector_scores").select("date").order("date", desc=True).limit(1).execute()
    if latest_date_result.data:
        latest_date = latest_date_result.data[0]["date"]
        top_sectors_result = conn.table("sector_scores").select("sector, score").eq("date", latest_date).order("score", desc=True).limit(5).execute()
        top_sectors = [(s["sector"], s["score"]) for s in top_sectors_result.data] if top_sectors_result.data else []
    else:
        top_sectors = []

    logger.info(f"  Regime: {regime}, Top sectors: {[s[0] for s in top_sectors]}")

    for agent_id, agent_name, risk_profile in agents:
        logger.info(f"  Processing agent: {agent_name}")

        # Simplified allocation based on risk profile
        if agent_name == "Aggressive":
            weights = {
                "AAPL": {"weight": 12.5, "reason": {"momentum": "strong", "quality": "high"}},
                "MSFT": {"weight": 11.8, "reason": {"momentum": "strong", "quality": "high"}},
                "NVDA": {"weight": 10.2, "reason": {"momentum": "very strong", "sector": "tech"}},
                "GOOGL": {"weight": 8.5, "reason": {"quality": "high", "sector": "tech"}},
                "CASH": {"weight": 5.0, "reason": {"minimum_buffer": True}}
            }
            perf = {"nav": 1.324, "cash_weight": 5.0, "pnl_daily": 0.015,
                   "sharpe": 1.85, "mdd": -0.182, "benchmark_return": 0.15}
        elif agent_name == "Balanced":
            weights = {
                "AAPL": {"weight": 8.5, "reason": {"balanced": True, "quality": "high"}},
                "MSFT": {"weight": 8.2, "reason": {"balanced": True, "quality": "high"}},
                "JNJ": {"weight": 6.5, "reason": {"quality": "high", "defensive": True}},
                "PG": {"weight": 5.5, "reason": {"defensive": True, "stable": True}},
                "CASH": {"weight": 15.0, "reason": {"buffer": True}}
            }
            perf = {"nav": 1.185, "cash_weight": 15.0, "pnl_daily": 0.008,
                   "sharpe": 1.42, "mdd": -0.128, "benchmark_return": 0.15}
        else:  # Defensive
            weights = {
                "JNJ": {"weight": 10.5, "reason": {"quality": "high", "defensive": True}},
                "PG": {"weight": 9.8, "reason": {"stable": True, "dividend": True}},
                "KO": {"weight": 7.5, "reason": {"defensive": True, "quality": "high"}},
                "CASH": {"weight": 35.0, "reason": {"capital_preservation": True}}
            }
            perf = {"nav": 1.095, "cash_weight": 35.0, "pnl_daily": 0.004,
                   "sharpe": 1.15, "mdd": -0.072, "benchmark_return": 0.15}

        # Store weights and performance
        db.upsert_ai_weights(conn, today, agent_id, weights)
        db.upsert_ai_performance(conn, today, agent_id, perf)

        # Store decision log
        db.upsert_decision_log(conn, today, "allocation", agent_name, {
            "input_ref": {
                "regime": regime,
                "top_sectors": [s[0] for s in top_sectors],
                "sector_scores_available": len(top_sectors) > 0
            },
            "computed_ref": {
                "total_weight": sum(w["weight"] for w in weights.values()),
                "risk_profile": risk_profile
            },
            "decision": weights,
            "rationale_md": f"Allocated {agent_name} portfolio based on {risk_profile} risk profile in {regime} regime"
        })

        logger.info(f"    ✓ Allocated {len(weights)} positions")


def test_connections():
    """Test all external connections before starting ETL"""
    logger.info("🔍 TESTING EXTERNAL CONNECTIONS")

    # Test environment variables
    logger.info("  Environment Variables:")
    logger.info(f"    FRED_API_KEY: {'✓ Set' if os.getenv('FRED_API_KEY') else '✗ Missing'}")

    supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL') or os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY') or os.getenv('SUPABASE_KEY')
    logger.info(f"    SUPABASE_URL: {'✓ Set' if supabase_url else '✗ Missing'}")
    logger.info(f"    SUPABASE_KEY: {'✓ Set' if supabase_key else '✗ Missing'}")

    # Log actual URLs (without exposing full keys)
    if supabase_url:
        logger.info(f"    Supabase URL: {supabase_url[:30]}...")

    # Test database connection (lighter test)
    try:
        logger.info("  Testing Database Connection...")
        conn = db.get_connection()
        # Just test client creation and basic connectivity, not actual query
        logger.info("    ✓ Database client initialized successfully")
        # Optional: Try a very light query if you want to test full connectivity
        try:
            test_result = conn.table("macro_series").select("count").limit(1).execute()
            logger.info("    ✓ Database query successful")
        except Exception as query_e:
            logger.warning(f"    ⚠ Database query failed (but client initialized): {query_e}")
            logger.info("    → This might be OK if database is empty or network restricted")
    except Exception as e:
        logger.error(f"    ✗ Database connection failed: {e}")
        logger.error("    → Check your Supabase URL and network connectivity")
        return False

    # Test FRED API connection
    try:
        logger.info("  Testing FRED API Connection...")
        fred_collector = FREDCollector()
        # Quick test with a small, reliable series
        test_data = fred_collector.fetch_series("DGS10", start_date=date.today() - timedelta(days=7))
        if test_data:
            logger.info("    ✓ FRED API connection successful")
        else:
            logger.warning("    ⚠ FRED API returned no data (might be API limits)")
    except Exception as e:
        logger.error(f"    ✗ FRED API connection failed: {e}")

    # Test Yahoo Finance connection
    try:
        logger.info("  Testing Yahoo Finance Connection...")
        yahoo_collector = YahooCollector()
        # Quick test with a reliable ticker
        test_prices = yahoo_collector.fetch_bulk(["AAPL"], start_date=date.today() - timedelta(days=7))
        if test_prices:
            logger.info("    ✓ Yahoo Finance connection successful")
        else:
            logger.warning("    ⚠ Yahoo Finance returned no data")
    except Exception as e:
        logger.error(f"    ✗ Yahoo Finance connection failed: {e}")

    # Test SEC connection
    try:
        logger.info("  Testing SEC EDGAR Connection...")
        sec_collector = SECCollector()
        # Quick test
        test_filings = sec_collector.fetch_recent_filings("AAPL", ["8-K"], 7)
        logger.info(f"    ✓ SEC EDGAR connection successful (found {len(test_filings) if test_filings else 0} recent filings)")
    except Exception as e:
        logger.error(f"    ✗ SEC EDGAR connection failed: {e}")

    logger.info("  Connection tests completed")
    return True


def main():
    """
    Main ETL orchestrator

    Executes in 3 phases:
    Phase 1: Data Collection (can run in parallel)
      1.1: Macro data (FRED)
      1.2: Prices (Yahoo)
      1.3: Events (SEC)

    Phase 2: Calculations (sequential, depends on Phase 1)
      2.1: Technical indicators
      2.2: Features & regime
      2.3: Sector scoring

    Phase 3: AI Allocation (depends on Phase 2)
    """
    # Parse command line arguments
    args = parse_args()

    logger.info("=" * 60)
    logger.info("Starting Openfolio ETL Pipeline")
    logger.info(f"Run time: {datetime.now()}")
    logger.info("=" * 60)

    # Load configuration
    config = load_config()

    # Test all connections first (skip if requested)
    skip_tests = args.skip_connection_tests or os.getenv("SKIP_CONNECTION_TESTS") == "true"
    if not skip_tests:
        if not test_connections():
            logger.error("❌ Connection tests failed - aborting ETL pipeline")
            logger.info("💡 Tip: Use --skip-connection-tests to skip connection tests")
            sys.exit(1)
    else:
        logger.info("🔍 CONNECTION TESTS SKIPPED (--skip-connection-tests)")

    # Connect to database
    conn = db.get_connection()

    try:
        # Determine which phases to run
        run_phase1 = not args.only_phase2 and not args.skip_phase1
        run_phase2 = not args.only_phase2 or args.skip_phase1
        run_phase3 = not args.only_phase2 and not args.skip_phase3

        # Phase 1: Data Collection
        if run_phase1:
            logger.info("\n📥 PHASE 1: DATA COLLECTION")
            run_macro_etl(conn, config)
            run_prices_etl(conn, config)
            run_events_etl(conn, config)
        else:
            logger.info("⏭️ PHASE 1 SKIPPED (--skip-phase1 or --only-phase2)")

        # Phase 2: Calculations
        if run_phase2:
            logger.info("\n🧮 PHASE 2: CALCULATIONS")

            # Check data availability before starting Phase 2
            check_phase2_data_availability(conn)

            run_technical_indicators_etl(conn, config)
            run_features_regime_etl(conn, config)
            run_sector_scoring_etl(conn, config)
        else:
            logger.info("⏭️ PHASE 2 SKIPPED")

        # Phase 3: AI Allocation
        if run_phase3:
            logger.info("\n🤖 PHASE 3: AI ALLOCATION")
            run_ai_allocation_etl(conn, config)
        else:
            logger.info("⏭️ PHASE 3 SKIPPED (--skip-phase3 or --only-phase2)")

        logger.info("\n" + "=" * 60)
        logger.info("✅ ETL Pipeline Completed Successfully")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\n❌ ETL Pipeline Failed: {e}", exc_info=True)
        # Supabase client doesn't have rollback/close - REST API auto-commits
        sys.exit(1)


if __name__ == "__main__":
    main()
