#!/usr/bin/env python3
"""
Test script to validate all ETL imports and configurations
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all modules can be imported"""
    logger.info("Testing imports...")

    try:
        # Utils
        from utils.rate_limiter import RateLimiter
        from utils.cache_manager import CacheManager
        from utils.retry_logic import RetryStrategy
        logger.info("✓ Utils imported")

        # Base collector
        from collectors.base_collector import BaseCollector
        logger.info("✓ Base collector imported")

        # Collectors
        from collectors.fred_collector import FREDCollector
        from collectors.yahoo_collector import YahooCollector
        from collectors.sec_collector import SECCollector
        logger.info("✓ All collectors imported")

        # Calculators
        from calculators.technical_indicators import TechnicalCalculator
        from calculators.feature_regime import FeatureRegimeCalculator
        from calculators.sector_scoring import SectorScorer
        logger.info("✓ All calculators imported")

        # Database
        import db
        logger.info("✓ Database module imported")

        logger.info("\n✅ All imports successful!")
        return True

    except ImportError as e:
        logger.error(f"\n❌ Import failed: {e}")
        return False

def test_configurations():
    """Test that configuration files exist"""
    import os
    import json

    logger.info("\nTesting configurations...")

    # Check config.json
    if os.path.exists("config.json"):
        with open("config.json") as f:
            config = json.load(f)
        logger.info(f"✓ config.json loaded ({len(config['macro_series'])} macro series)")
    else:
        logger.error("✗ config.json not found")
        return False

    # Check .env
    if os.path.exists("../.env"):
        logger.info("✓ .env file exists")
    else:
        logger.warning("⚠ .env file not found (using defaults)")

    logger.info("\n✅ Configuration check complete!")
    return True

def test_instantiation():
    """Test that objects can be instantiated"""
    logger.info("\nTesting object instantiation...")

    try:
        from collectors.fred_collector import FREDCollector
        from collectors.yahoo_collector import YahooCollector
        from collectors.sec_collector import SECCollector
        from calculators.technical_indicators import TechnicalCalculator
        from calculators.feature_regime import FeatureRegimeCalculator
        from calculators.sector_scoring import SectorScorer

        fred = FREDCollector()
        yahoo = YahooCollector()
        sec = SECCollector()
        ta = TechnicalCalculator()
        fr = FeatureRegimeCalculator()
        scorer = SectorScorer()

        logger.info("✓ All objects instantiated")
        logger.info("\n✅ Instantiation test complete!")
        return True

    except Exception as e:
        logger.error(f"\n❌ Instantiation failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Openfolio ETL - Import & Configuration Test")
    logger.info("=" * 60)

    success = True
    success = test_imports() and success
    success = test_configurations() and success
    success = test_instantiation() and success

    if success:
        logger.info("\n" + "=" * 60)
        logger.info("✅ ALL TESTS PASSED")
        logger.info("=" * 60)
        logger.info("\nYou can now run the ETL pipeline with:")
        logger.info("  cd etl && python run_all.py")
        sys.exit(0)
    else:
        logger.error("\n" + "=" * 60)
        logger.error("❌ SOME TESTS FAILED")
        logger.error("=" * 60)
        sys.exit(1)
