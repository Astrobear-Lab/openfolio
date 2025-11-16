#!/usr/bin/env python3
"""
Integrated Yahoo Finance & Calculations Test Script
Tests both Phase 1 (data collection) and Phase 2 (calculations) in one script

This script provides comprehensive testing of the entire ETL pipeline:
Phase 1: Yahoo Finance price data collection
Phase 2: Technical indicators, features/regime, and sector scoring calculations

Useful for:
- End-to-end pipeline testing
- Testing Yahoo Finance API connectivity
- Debugging data collection and calculation issues
- Validating database writes across all components
- Quick data collection + analysis workflow

Usage:
  python test_yahoo_prices.py                           # Test Phase 1 + Phase 2 (full pipeline)
  python test_yahoo_prices.py --only-phase1             # Phase 1 only (data collection)
  python test_yahoo_prices.py --only-phase2             # Phase 2 only (calculations)
  python test_yahoo_prices.py --tickers AAPL NVDA --days 90
  python test_yahoo_prices.py --all-tickers             # Test with all tickers from config
  python test_yahoo_prices.py --skip-connection-tests   # Skip connection tests

Note: Requires .env file with Supabase credentials and FRED_API_KEY (even if not used)
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

import db
from collectors.yahoo_collector import YahooCollector
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


def test_yahoo_connection():
    """Test Yahoo Finance connection before starting ETL"""
    logger.info("🔍 TESTING YAHOO FINANCE CONNECTION")

    try:
        yahoo_collector = YahooCollector()
        # Quick test with a reliable ticker
        test_prices = yahoo_collector.fetch_bulk(["AAPL"], start_date=datetime.now() - timedelta(days=7))
        if test_prices:
            logger.info("    ✓ Yahoo Finance connection successful")
            return True
        else:
            logger.warning("    ⚠ Yahoo Finance returned no data")
            return False
    except Exception as e:
        logger.error(f"    ✗ Yahoo Finance connection failed: {e}")
        return False


def run_prices_etl_test(conn, config, tickers=None, days_back=None):
    """
    Test version of Yahoo Finance price ETL (Phase 1.2)

    Args:
        conn: Database connection
        config: Configuration dict
        tickers: Optional list of tickers to test (default: all)
        days_back: Optional days of history (default: 30 days for testing)
    """
    logger.info("=== PHASE 1.2: Yahoo Finance Price ETL ===")

    # Use provided tickers or default to first few for testing
    if tickers is None:
        # Default to just a few tickers for testing
        tickers = ["AAPL", "MSFT", "GOOGL"]
        logger.info(f"Using default test tickers: {tickers}")

    # Use shorter date range for testing
    if days_back is None:
        days_back = 30
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    logger.info(f"Testing with {len(tickers)} tickers, {days_back} days of history")

    collector = YahooCollector()

    try:
        # Bulk fetch all tickers at once (more efficient)
        logger.info(f"Fetching prices for {len(tickers)} tickers...")
        all_prices = collector.fetch_bulk(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date
        )

        total_points = 0
        successful_tickers = 0

        # Store prices (flatten the dict structure)
        if all_prices:
            prices_list = []
            for ticker, prices in all_prices.items():
                if prices:
                    logger.info(f"  ✓ {ticker}: {len(prices)} price points")
                    total_points += len(prices)
                    successful_tickers += 1

                    # Add ticker to each price record
                    for price in prices:
                        price["ticker"] = ticker
                        prices_list.append(price)
                else:
                    logger.warning(f"  ⚠ {ticker}: No price data")

            if prices_list:
                # Store to database
                db.upsert_prices(conn, prices_list)
                logger.info(f"✓ Stored {len(prices_list)} total price records to database")
            else:
                logger.warning("⚠ No price data to store")
        else:
            logger.warning("⚠ No price data received from Yahoo Finance")

        # Summary
        logger.info(f"Test Results: {successful_tickers}/{len(tickers)} tickers successful, {total_points} total data points")

        return {
            "total_tickers": len(tickers),
            "successful_tickers": successful_tickers,
            "total_points": total_points,
            "start_date": start_date.date(),
            "end_date": end_date.date()
        }

    except Exception as e:
        logger.error(f"✗ Failed to fetch prices: {e}")
        raise


def run_technical_indicators_test(conn, config, tickers=None):
    """
    Test Phase 2.1: Technical Indicators Calculation

    Args:
        conn: Database connection
        config: Configuration dict
        tickers: Optional list of tickers to test

    Returns:
        Dict with test results
    """
    logger.info("=== PHASE 2.1: Technical Indicators ===")

    calculator = TechnicalCalculator()

    # Use provided tickers or default to first few
    if tickers is None:
        tickers = ["AAPL", "MSFT", "GOOGL"]  # Default test tickers
        logger.info(f"Using default test tickers: {tickers}")

    total_indicators = 0
    successful_tickers = 0

    for ticker in tickers:
        try:
            logger.info(f"  Calculating indicators for {ticker}...")
            indicators = calculator.calculate_all_for_ticker(ticker, conn)

            if indicators:
                # Store indicators
                db.upsert_ta_indicators(conn, indicators)
                indicator_count = len(indicators)
                total_indicators += indicator_count
                successful_tickers += 1
                logger.info(f"    ✓ {ticker}: {indicator_count} days of indicators calculated")
            else:
                logger.warning(f"    ⚠ {ticker}: No indicators calculated")

        except Exception as e:
            logger.error(f"    ✗ Failed to calculate indicators for {ticker}: {e}")
            continue

    logger.info(f"Technical indicators test completed: {successful_tickers}/{len(tickers)} tickers, {total_indicators} total indicator records")

    return {
        "component": "technical_indicators",
        "total_tickers": len(tickers),
        "successful_tickers": successful_tickers,
        "total_indicators": total_indicators
    }


def run_features_regime_test(conn, config, days_back=7):
    """
    Test Phase 2.2: Features & Regime Calculation

    Args:
        conn: Database connection
        config: Configuration dict
        days_back: Days of history to calculate

    Returns:
        Dict with test results
    """
    logger.info("=== PHASE 2.2: Features & Regime ===")

    calculator = FeatureRegimeCalculator(window_months=36)

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    logger.info(f"Calculating features & regime for {days_back} days (from {start_date.date()} to {end_date.date()})")

    current_date = start_date
    calculated_count = 0
    regime_counts = {}

    while current_date <= end_date:
        try:
            # Calculate composites (returns (value, details) tuples or None)
            growth_result = calculator.calculate_growth_composite(conn, current_date)
            inflation_result = calculator.calculate_inflation_composite(conn, current_date)
            liquidity_result = calculator.calculate_liquidity_composite(conn, current_date)
            rates_result = calculator.calculate_rates_composite(conn, current_date)

            # Skip if essential data missing (None)
            if growth_result is None or inflation_result is None:
                current_date += timedelta(days=1)
                continue

            # Unpack results (now we know they are not None)
            growth_z, growth_details = growth_result
            inflation_z, inflation_details = inflation_result

            # Optional data: use defaults if None
            liquidity_z, liquidity_details = liquidity_result or (0.0, {})
            rates_z, rates_details = rates_result or (0.0, {})

            # Store features
            features = {
                "growth_composite": {
                    "value": growth_z,
                    "details": growth_details
                },
                "inflation_composite": {
                    "value": inflation_z,
                    "details": inflation_details
                },
                "liquidity_composite": {
                    "value": liquidity_z,
                    "details": liquidity_details
                },
                "rates_composite": {
                    "value": rates_z,
                    "details": rates_details
                }
            }

            db.upsert_macro_features(conn, current_date, features)

            # Classify regime
            regime = calculator.classify_regime(
                growth_z=growth_z,
                inflation_z=inflation_z,
                rules=config["regime_rules"]
            )

            # Count regime occurrences
            regime_counts[regime] = regime_counts.get(regime, 0) + 1

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
            logger.error(f"  ✗ Failed to calculate for {current_date.date()}: {e}")

        current_date += timedelta(days=1)

    logger.info(f"Features & regime test completed: {calculated_count} days calculated")
    logger.info(f"Regime distribution: {regime_counts}")

    return {
        "component": "features_regime",
        "days_calculated": calculated_count,
        "regime_counts": regime_counts,
        "start_date": start_date.date(),
        "end_date": end_date.date()
    }


def run_sector_scoring_test(conn, config, days_back=7):
    """
    Test Phase 2.3: Sector Scoring Calculation

    Args:
        conn: Database connection
        config: Configuration dict
        days_back: Days of history to calculate

    Returns:
        Dict with test results
    """
    logger.info("=== PHASE 2.3: Sector Scoring ===")

    scorer = SectorScorer()

    # Get latest regime for scoring
    try:
        regime_result = conn.table("macro_regime_daily").select("regime").order("date", desc=True).limit(1).execute()
        regime = regime_result.data[0]["regime"] if regime_result.data else "Goldilocks"
        logger.info(f"Using current regime: {regime}")
    except Exception as e:
        logger.warning(f"Could not fetch current regime: {e}, using Goldilocks as default")
        regime = "Goldilocks"

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    logger.info(f"Calculating sector scores for {days_back} days (from {start_date.date()} to {end_date.date()})")

    current_date = start_date
    calculated_count = 0
    total_scores = 0

    while current_date <= end_date:
        try:
            scores = scorer.score_all_sectors(
                date=current_date,
                regime=regime,
                conn=conn,
                config=config
            )

            if scores:
                # Store scores
                db.upsert_sector_scores(conn, current_date.date(), scores)
                total_scores += len(scores)
                calculated_count += 1

                # Log top 3 sectors for this date
                top_sectors = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)[:3]
                top_sectors_str = ', '.join([f'{s[0]}({s[1]["score"]:.2f})' for s in top_sectors])
                logger.info(f"  {current_date.date()}: Top sectors: {top_sectors_str}")
            else:
                logger.warning(f"  ⚠ No sector scores for {current_date.date()}")

        except Exception as e:
            logger.error(f"  ✗ Failed to score sectors for {current_date.date()}: {e}")

        current_date += timedelta(days=1)

    logger.info(f"Sector scoring test completed: {calculated_count} days calculated, {total_scores} total scores")

    return {
        "component": "sector_scoring",
        "days_calculated": calculated_count,
        "total_scores": total_scores,
        "regime_used": regime,
        "start_date": start_date.date(),
        "end_date": end_date.date()
    }


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Integrated Yahoo Finance & Calculations Test (Phase 1 + Phase 2)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_yahoo_prices.py                           # Test Phase 1 (prices) + Phase 2 (all calculations)
  python test_yahoo_prices.py --only-phase1             # Phase 1 only (Yahoo Finance prices)
  python test_yahoo_prices.py --only-phase2             # Phase 2 only (calculations)
  python test_yahoo_prices.py --tickers AAPL NVDA --days 90
  python test_yahoo_prices.py --all-tickers             # Test with all tickers from config
  python test_yahoo_prices.py --skip-connection-tests   # Skip connection tests
        """
    )

    parser.add_argument('--only-phase1', action='store_true',
                       help='Test only Phase 1 (Yahoo Finance price collection)')
    parser.add_argument('--only-phase2', action='store_true',
                       help='Test only Phase 2 (calculations)')
    parser.add_argument('--tickers', nargs='+',
                       help='Specific tickers to test (space separated)')
    parser.add_argument('--days', type=int, default=30,
                       help='Days of history to fetch/calculate (default: 30)')
    parser.add_argument('--all-tickers', action='store_true',
                       help='Test with all tickers from config')
    parser.add_argument('--skip-connection-tests', action='store_true',
                       help='Skip Yahoo Finance connection tests')

    return parser.parse_args()


def check_data_availability(conn):
    """
    Check if required data is available for Phase 2 calculations
    """
    logger.info("📊 Checking data availability for Phase 2 calculations...")

    try:
        # Check prices data
        prices_result = conn.table("prices_daily").select("*", count="exact", head=False).execute()
        prices_count = getattr(prices_result, 'count', 0)
        logger.info(f"  💰 Prices data: {prices_count} records")

        # Check macro data
        macro_points_result = conn.table("macro_points").select("*", count="exact", head=False).execute()
        macro_points_count = getattr(macro_points_result, 'count', 0)
        logger.info(f"  📊 Macro points: {macro_points_count} data points")

        return prices_count > 0 and macro_points_count > 0

    except Exception as e:
        logger.error(f"❌ Failed to check data availability: {e}")
        return False


def main():
    """
    Main test orchestrator for integrated Phase 1 + Phase 2 testing
    """
    args = parse_args()

    logger.info("=" * 70)
    logger.info("Starting Integrated Yahoo Finance & Calculations Test")
    logger.info(f"Run time: {datetime.now()}")
    logger.info("=" * 70)

    # Load configuration
    config = load_config()

    # Determine which phases to run
    run_phase1 = not args.only_phase2
    run_phase2 = not args.only_phase1

    if run_phase1:
        logger.info("🎯 PHASE 1: Yahoo Finance Price Collection")
    if run_phase2:
        logger.info("🎯 PHASE 2: Technical Analysis & Calculations")
    logger.info("")

    # Test Yahoo connection first (skip if requested and running Phase 1)
    if run_phase1:
        skip_tests = args.skip_connection_tests or os.getenv("SKIP_CONNECTION_TESTS") == "true"
        if not skip_tests:
            if not test_yahoo_connection():
                logger.error("❌ Yahoo Finance connection test failed - aborting test")
                sys.exit(1)
        else:
            logger.info("🔍 YAHOO CONNECTION TESTS SKIPPED (--skip-connection-tests)")

    # Connect to database
    conn = db.get_connection()

    results = {}
    error_count = 0

    try:
        # Determine which tickers to test
        if args.tickers:
            tickers = args.tickers
        elif args.all_tickers:
            # Use all tickers from config
            tickers = [s["ticker"] for s in config["sector_etfs"]] + config["sample_stocks"]
        else:
            tickers = None  # Use defaults in the functions

        # Phase 1: Price Data Collection
        if run_phase1:
            try:
                logger.info("📥 PHASE 1: DATA COLLECTION")
                results["phase1_prices"] = run_prices_etl_test(
                    conn=conn,
                    config=config,
                    tickers=tickers,
                    days_back=args.days
                )
            except Exception as e:
                logger.error(f"Phase 1 failed: {e}")
                error_count += 1

        # Phase 2: Calculations
        if run_phase2:
            logger.info("\n🧮 PHASE 2: CALCULATIONS")

            # Check data availability for Phase 2
            if not check_data_availability(conn):
                logger.warning("⚠️  Insufficient data for Phase 2 calculations")
                logger.info("💡 Tip: Run Phase 1 first or use --only-phase1 to collect data")
                if run_phase1:
                    logger.info("   → Phase 1 was run above, but may need more data for full Phase 2")
            else:
                logger.info("✅ Sufficient data available for Phase 2 calculations")

            # Run Phase 2 calculations
            try:
                results["phase2_technical"] = run_technical_indicators_test(conn, config, tickers)
            except Exception as e:
                logger.error(f"Technical indicators failed: {e}")
                error_count += 1

            try:
                results["phase2_features"] = run_features_regime_test(conn, config, min(args.days, 7))  # Shorter for features
            except Exception as e:
                logger.error(f"Features & regime failed: {e}")
                error_count += 1

            try:
                results["phase2_sectors"] = run_sector_scoring_test(conn, config, min(args.days, 7))  # Shorter for sectors
            except Exception as e:
                logger.error(f"Sector scoring failed: {e}")
                error_count += 1

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("📊 INTEGRATED TEST SUMMARY")

        for component, result in results.items():
            logger.info(f"  {component}: {result}")

        if error_count > 0:
            logger.warning(f"⚠️ {error_count} component(s) failed")
            logger.info("=" * 70)
            sys.exit(1)
        else:
            logger.info("✅ All tests completed successfully")
            logger.info("=" * 70)

    except Exception as e:
        logger.error(f"\n❌ Integrated Test Failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
