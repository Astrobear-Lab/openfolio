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
from openai import OpenAI

import db
from collectors.fred_collector import FREDCollector
from collectors.yahoo_collector import YahooCollector
from collectors.sec_collector import SECCollector
from calculators.technical_indicators import TechnicalCalculator
from calculators.feature_regime import FeatureRegimeCalculator
from calculators.sector_scoring import SectorScorer
from calculators.stock_screener import StockScreener
from calculators.backtest import run_backtest_for_allocation

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
            # Flatten the dictionary values (lists of prices) into a single list
            flattened_prices = []
            for ticker_prices in all_prices.values():
                flattened_prices.extend(ticker_prices)

            db.upsert_prices(conn, flattened_prices)
            logger.info(f"  ✓ Stored {len(flattened_prices)} total price records")
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


def run_screener_etl(conn, config):
    """
    Phase 2.4: Stock Screener

    Multi-stage screening of individual stocks:
    - Quality: Fundamental metrics
    - Value: Valuation metrics
    - Events: Recent performance, sentiment
    - Technical: Momentum, RSI, MACD
    """
    logger.info("=== Phase 2.4: Stock Screener ===")

    screener = StockScreener()

    # Get latest date with price data
    try:
        response = conn.table("prices_daily").select("date").order("date", desc=True).limit(1).execute()
        if not response.data:
            logger.warning("No price data available for screening")
            return
        latest_date = datetime.fromisoformat(response.data[0]["date"])
    except Exception as e:
        logger.error(f"Failed to get latest date: {e}")
        return

    logger.info(f"Screening stocks for {latest_date.date()}")

    try:
        # Screen all stocks
        results = screener.screen_all_stocks(conn, config, latest_date)

        if results:
            # Store screening steps
            screening_steps = []
            rankings = []

            for i, result in enumerate(results):
                # Store individual screening steps
                for step_name in ["quality", "value", "events", "technical"]:
                    step_data = result[step_name]
                    screening_steps.append({
                        "date": latest_date.date(),
                        "ticker": result["ticker"],
                        "step": step_name,
                        "pass": step_data["pass"],
                        "score": step_data["score"],
                        "evidence_json": {
                            "metrics": step_data["metrics"],
                            "evidence": step_data["evidence"]
                        }
                    })

                # Store final ranking
                rankings.append({
                    "date": latest_date.date(),
                    "ticker": result["ticker"],
                    "rank": i + 1,
                    "total_score": result["total_score"],
                    "decision": result["decision"],
                    "stages_passed": result["stages_passed"],
                    "details_json": {
                        "quality": result["quality"],
                        "value": result["value"],
                        "events": result["events"],
                        "technical": result["technical"],
                        "weights": result["weights"]
                    }
                })

            # Upsert to database
            db.upsert_screening_steps(conn, screening_steps)
            db.upsert_rankings(conn, rankings)

            logger.info(f"  ✓ Screened {len(results)} stocks, stored {len(screening_steps)} steps")
        else:
            logger.warning("  ⚠ No screening results generated")

    except Exception as e:
        logger.error(f"  ✗ Failed to run screener: {e}")


def run_ai_allocation_etl(conn, config):
    """
    Phase 3: Run AI agent allocations using OpenAI GPT-4

    Generates portfolio allocations using AI with full transparency:
    - Input: macro regime, sector scores, screener results
    - Output: stock weights + detailed reasoning for each position
    - All prompts and responses logged to decision_log table
    """
    logger.info("=== Phase 3: AI Agent Allocation (OpenAI GPT-4) ===")

    today = date.today()

    # Check for OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.warning("  ⚠️  OPENAI_API_KEY not found - using fallback rule-based allocation")
        return _run_fallback_allocation(conn, config, today)

    try:
        client = OpenAI(api_key=openai_api_key)
        logger.info("  ✓ OpenAI client initialized")
    except Exception as e:
        logger.error(f"  ✗ Failed to initialize OpenAI: {e}")
        return _run_fallback_allocation(conn, config, today)

    # Fetch context data
    context = _fetch_allocation_context(conn)

    # Get AI agents
    agents_result = conn.table("ai_agents").select("id, name, risk_profile, description").order("id").execute()
    agents = agents_result.data if agents_result.data else []

    if not agents:
        logger.warning("  ⚠️  No AI agents found in database")
        return

    logger.info(f"  Context: Regime={context['regime']}, Top Sectors={context['top_sectors'][:3]}")
    logger.info(f"  Processing {len(agents)} AI agents...")

    for agent in agents:
        agent_id = agent["id"]
        agent_name = agent["name"]
        risk_profile = agent["risk_profile"]

        logger.info(f"\n  🤖 Agent: {agent_name} ({risk_profile})")

        try:
            # Build prompt
            prompt = _build_allocation_prompt(agent, context)

            # Call OpenAI
            logger.info(f"    Calling GPT-4...")
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a quantitative portfolio manager with expertise in macro-driven top-down investing. You provide detailed, transparent reasoning for every decision."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )

            ai_response = response.choices[0].message.content
            logger.info(f"    ✓ Received AI response ({len(ai_response)} chars)")

            # Parse AI response
            weights = _parse_ai_allocation(ai_response, agent_name)

            if not weights:
                logger.warning(f"    ⚠️  Failed to parse weights, using fallback")
                weights = _get_fallback_weights(agent_name)

            # Run backtest to calculate real performance metrics
            logger.info(f"    Running backtest (1-year lookback)...")
            try:
                perf = run_backtest_for_allocation(conn, weights, lookback_days=252)
                logger.info(f"    ✓ Backtest complete: Return={perf['total_return']:.2%}, Sharpe={perf['sharpe']:.2f}, MDD={perf['mdd']:.2%}")
            except Exception as e:
                logger.warning(f"    ⚠️  Backtest failed: {e}, using fallback metrics")
                total_weight = sum(w["weight"] for w in weights.values())
                cash_weight = weights.get("CASH", {}).get("weight", 0)
                perf = {
                    "nav": 1.0,
                    "cash_weight": cash_weight,
                    "pnl_daily": 0.0,
                    "sharpe": 0.0,
                    "mdd": 0.0,
                    "volatility": 0.0,
                    "total_return": 0.0,
                    "annualized_return": 0.0,
                    "benchmark_return": 0.0,
                    "excess_return": 0.0
                }

            # Store to database
            db.upsert_ai_weights(conn, today, agent_id, weights)
            db.upsert_ai_performance(conn, today, agent_id, perf)

            # Store decision log with full prompt and response
            db.upsert_decision_log(conn, today, "allocation", agent_name, {
                "input_ref": {
                    "regime": context["regime"],
                    "regime_details": context["regime_details"],
                    "top_sectors": context["top_sectors"],
                    "screener_count": len(context["screener_results"])
                },
                "computed_ref": {
                    "total_weight": total_weight,
                    "risk_profile": risk_profile,
                    "model": "gpt-4",
                    "prompt_length": len(prompt),
                    "response_length": len(ai_response)
                },
                "decision": weights,
                "rationale_md": ai_response,  # Full AI reasoning
                "prompt": prompt  # Full prompt for transparency
            })

            logger.info(f"    ✓ Allocated {len(weights)} positions (Total: {total_weight:.1f}%)")

        except Exception as e:
            logger.error(f"    ✗ Failed to process agent {agent_name}: {e}")
            # Continue with next agent
            continue

    logger.info(f"\n  ✅ AI Allocation Complete")


def _fetch_allocation_context(conn):
    """Fetch all context data needed for AI allocation"""
    context = {}

    # Get latest regime
    regime_result = conn.table("macro_regime_daily").select("*").order("date", desc=True).limit(1).execute()
    if regime_result.data:
        regime_data = regime_result.data[0]
        context["regime"] = regime_data["regime"]
        context["regime_details"] = {
            "growth_z": regime_data.get("growth_z"),
            "inflation_z": regime_data.get("inflation_z"),
            "liquidity_z": regime_data.get("liquidity_z"),
            "rates_z": regime_data.get("rates_z")
        }
    else:
        context["regime"] = "Unknown"
        context["regime_details"] = {}

    # Get top sector scores
    latest_sector_date = conn.table("sector_scores").select("date").order("date", desc=True).limit(1).execute()
    if latest_sector_date.data:
        latest_date = latest_sector_date.data[0]["date"]
        sectors_result = conn.table("sector_scores").select("sector, score").eq("date", latest_date).order("score", desc=True).limit(10).execute()
        context["top_sectors"] = [(s["sector"], s["score"]) for s in sectors_result.data] if sectors_result.data else []
    else:
        context["top_sectors"] = []

    # Get screener results
    latest_screener_date = conn.table("screener_results").select("date").order("date", desc=True).limit(1).execute()
    if latest_screener_date.data:
        latest_date = latest_screener_date.data[0]["date"]
        screener_result = conn.table("screener_results").select("*").eq("date", latest_date).order("composite_score", desc=True).limit(30).execute()
        context["screener_results"] = screener_result.data if screener_result.data else []
    else:
        context["screener_results"] = []

    return context


def _build_allocation_prompt(agent, context):
    """Build the prompt for OpenAI allocation"""
    agent_name = agent["name"]
    risk_profile = agent["risk_profile"]
    regime = context["regime"]
    regime_details = context["regime_details"]
    top_sectors = context["top_sectors"]
    screener_results = context["screener_results"]

    # Format sectors
    sectors_text = "\n".join([f"  {i+1}. {sector} (score: {score:.2f})" for i, (sector, score) in enumerate(top_sectors[:5])])

    # Format screener results
    screener_text = "\n".join([
        f"  {i+1}. {stock['ticker']} - Score: {stock['composite_score']:.2f} (Quality: {stock.get('quality_score', 0):.1f}, Value: {stock.get('value_score', 0):.1f}, Momentum: {stock.get('momentum_score', 0):.1f})"
        for i, stock in enumerate(screener_results[:20])
    ])

    prompt = f"""You are managing a {risk_profile} risk profile portfolio called "{agent_name}".

**Current Market Regime: {regime}**
- Growth Z-Score: {regime_details.get('growth_z', 'N/A')}
- Inflation Z-Score: {regime_details.get('inflation_z', 'N/A')}
- Liquidity Z-Score: {regime_details.get('liquidity_z', 'N/A')}
- Rates Z-Score: {regime_details.get('rates_z', 'N/A')}

**Top Performing Sectors:**
{sectors_text if sectors_text else "  (No sector data available)"}

**Stock Screener Results (Top 20):**
{screener_text if screener_text else "  (No screener results available)"}

**Your Task:**
Construct a portfolio allocation with 8-12 stock positions that aligns with the {risk_profile} risk profile.

**Requirements:**
1. Total portfolio weight should be 100%
2. Include CASH as a position (minimum 5% for Aggressive, 15% for Balanced, 30% for Defensive)
3. Consider the macro regime and favor sectors/stocks that perform well in current conditions
4. For each position, provide clear reasoning

**Output Format:**
Return a JSON object with this structure:
{{
  "AAPL": {{
    "weight": 12.5,
    "reason": "Strong momentum in technology sector, high quality fundamentals, performs well in Goldilocks regime"
  }},
  "CASH": {{
    "weight": 5.0,
    "reason": "Minimum buffer for rebalancing opportunities"
  }}
}}

Make sure weights add up to 100%. Focus on transparency - explain WHY you chose each stock and WHY that weight."""

    return prompt


def _parse_ai_allocation(ai_response, agent_name):
    """Parse AI response to extract weights"""
    try:
        # Try to find JSON in the response
        import re
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', ai_response, re.DOTALL)
        if json_match:
            weights_json = json.loads(json_match.group())
            return weights_json
        else:
            logger.warning(f"    No JSON found in AI response")
            return None
    except Exception as e:
        logger.error(f"    Failed to parse AI response: {e}")
        return None


def _get_fallback_weights(agent_name):
    """Fallback weights when AI parsing fails"""
    if agent_name == "Aggressive":
        return {
            "AAPL": {"weight": 12.5, "reason": "Fallback allocation"},
            "MSFT": {"weight": 11.8, "reason": "Fallback allocation"},
            "NVDA": {"weight": 10.2, "reason": "Fallback allocation"},
            "GOOGL": {"weight": 8.5, "reason": "Fallback allocation"},
            "CASH": {"weight": 5.0, "reason": "Buffer"}
        }
    elif agent_name == "Balanced":
        return {
            "AAPL": {"weight": 8.5, "reason": "Fallback allocation"},
            "MSFT": {"weight": 8.2, "reason": "Fallback allocation"},
            "JNJ": {"weight": 6.5, "reason": "Fallback allocation"},
            "CASH": {"weight": 15.0, "reason": "Buffer"}
        }
    else:  # Defensive
        return {
            "JNJ": {"weight": 10.5, "reason": "Fallback allocation"},
            "PG": {"weight": 9.8, "reason": "Fallback allocation"},
            "KO": {"weight": 7.5, "reason": "Fallback allocation"},
            "CASH": {"weight": 35.0, "reason": "Capital preservation"}
        }


def _run_fallback_allocation(conn, config, today):
    """Fallback to rule-based allocation when OpenAI is not available"""
    logger.info("  Using rule-based fallback allocation...")

    # Get AI agents
    agents_result = conn.table("ai_agents").select("id, name, risk_profile").order("id").execute()
    agents = [(a["id"], a["name"], a["risk_profile"]) for a in agents_result.data] if agents_result.data else []

    # Get context for logging
    regime_result = conn.table("macro_regime_daily").select("regime").order("date", desc=True).limit(1).execute()
    regime = regime_result.data[0]["regime"] if regime_result.data else "Unknown"

    for agent_id, agent_name, risk_profile in agents:
        weights = _get_fallback_weights(agent_name)

        total_weight = sum(w["weight"] for w in weights.values())
        cash_weight = weights.get("CASH", {}).get("weight", 0)

        perf = {
            "nav": 1.0,
            "cash_weight": cash_weight,
            "pnl_daily": 0.0,
            "sharpe": 0.0,
            "mdd": 0.0,
            "benchmark_return": 0.0
        }

        db.upsert_ai_weights(conn, today, agent_id, weights)
        db.upsert_ai_performance(conn, today, agent_id, perf)

        db.upsert_decision_log(conn, today, "allocation", agent_name, {
            "input_ref": {"regime": regime},
            "computed_ref": {"total_weight": total_weight, "risk_profile": risk_profile, "model": "rule-based-fallback"},
            "decision": weights,
            "rationale_md": "Fallback rule-based allocation (OpenAI not available)"
        })

        logger.info(f"    ✓ {agent_name}: {len(weights)} positions (Total: {total_weight:.1f}%)")


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
            run_screener_etl(conn, config)
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
