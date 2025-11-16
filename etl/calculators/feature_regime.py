"""
Feature & Regime Calculator
Calculates macro z-scores and classifies economic regime
"""
import logging
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FeatureRegimeCalculator:
    """
    Calculate macro features (z-scores) and classify economic regime.

    Z-score normalization uses 36-month rolling window.
    Regime classification based on growth and inflation quadrants.

    Performance optimization: Data is cached to avoid repeated DB queries.
    """

    def __init__(self, window_months: int = 36):
        """
        Initialize calculator.

        Args:
            window_months: Rolling window for z-score (default 36 months)
        """
        self.window_months = window_months
        self.window_days = window_months * 30  # Approximate
        self._cache = {}  # Cache for fetched series

    def preload_data(self, conn: Any):
        """
        Preload all required macro series into cache.

        This significantly improves performance by fetching data once
        instead of on every calculation.

        Args:
            conn: Supabase client
        """
        logger.info("📥 Preloading macro data into cache...")

        series_codes = [
            "INDPRO", "PAYEMS", "UNRATE",  # Growth
            "CPIAUCSL", "CPILFESL",        # Inflation
            "M2SL", "WALCL",               # Liquidity
            "DGS10", "DGS2"                # Rates
        ]

        for code in series_codes:
            logger.info(f"  Loading {code}...")
            self._cache[code] = self.fetch_macro_series(code, conn)

        logger.info(f"✅ Cached {len(self._cache)} series")

    def get_cached_series(self, series_code: str, conn: Any) -> pd.Series:
        """
        Get series from cache or fetch if not cached.

        Args:
            series_code: FRED series code
            conn: Supabase client

        Returns:
            Pandas Series
        """
        if series_code not in self._cache:
            self._cache[series_code] = self.fetch_macro_series(series_code, conn)
        return self._cache[series_code]

    def fetch_macro_series(
        self,
        series_code: str,
        conn: Any,
        days_back: int = 1095,  # ~3 years
    ) -> pd.Series:
        """
        Fetch macro series from database.

        Args:
            series_code: FRED series code
            conn: Supabase client
            days_back: Days of history to fetch

        Returns:
            Pandas Series indexed by date
        """
        try:
            # Get series ID
            series_response = conn.table("macro_series") \
                .select("id") \
                .eq("code", series_code) \
                .execute()

            if not series_response.data:
                logger.error(f"Series {series_code} not found in database")
                return pd.Series()

            series_id = series_response.data[0]["id"]

            # Fetch points (include revision_of for deduplication)
            cutoff_date = (datetime.now() - timedelta(days=days_back)).date()

            points_response = conn.table("macro_points") \
                .select("ts, value, revision_of") \
                .eq("series_id", series_id) \
                .gte("ts", cutoff_date.isoformat()) \
                .order("ts", desc=False) \
                .execute()

            if not points_response.data:
                logger.warning(f"No data found for {series_code}")
                return pd.Series()

            # Convert to DataFrame and handle duplicates
            df = pd.DataFrame(points_response.data)
            df['ts'] = pd.to_datetime(df['ts'])

            # Handle duplicates: keep the most recent revision (NULL revision_of first, then latest revision_of)
            df = df.sort_values(['ts', 'revision_of'], na_position='first')
            df = df.drop_duplicates(subset=['ts'], keep='last')  # Keep last (most recent revision)

            df = df.set_index('ts')
            series = df['value'].astype(float)

            # Forward fill to daily
            series = series.resample('D').ffill()

            return series

        except Exception as e:
            logger.error(f"Failed to fetch {series_code}: {e}")
            return pd.Series()

    def calculate_z_score(self, series: pd.Series, window: int) -> pd.Series:
        """
        Calculate rolling z-score.

        Args:
            series: Data series
            window: Rolling window size (days)

        Returns:
            Z-score series
        """
        rolling_mean = series.rolling(window=window).mean()
        rolling_std = series.rolling(window=window).std()

        z_scores = (series - rolling_mean) / rolling_std
        return z_scores

    def calculate_growth_composite(
        self,
        conn: Any,
        date: datetime,
    ) -> Optional[float]:
        """
        Calculate growth composite z-score.

        Uses: INDPRO, PAYEMS, UNRATE (inverted)

        Args:
            conn: Supabase client
            date: Calculation date

        Returns:
            Composite z-score or None if no data
        """
        try:
            # Use cached data
            indpro = self.get_cached_series("INDPRO", conn)
            payems = self.get_cached_series("PAYEMS", conn)
            unrate = self.get_cached_series("UNRATE", conn)

            if indpro.empty or payems.empty or unrate.empty:
                logger.warning("Missing growth data")
                return None

            # Calculate z-scores
            indpro_z = self.calculate_z_score(indpro, self.window_days)
            payems_z = self.calculate_z_score(payems, self.window_days)
            unrate_z = -self.calculate_z_score(unrate, self.window_days)  # Invert (high unemployment = bad)

            # Get values for target date
            try:
                date_pd = pd.Timestamp(date)
                indpro_val = indpro_z.loc[date_pd]
                payems_val = payems_z.loc[date_pd]
                unrate_val = unrate_z.loc[date_pd]

                # Average
                composite = np.nanmean([indpro_val, payems_val, unrate_val])
                return float(composite) if pd.notna(composite) else None

            except KeyError:
                logger.warning(f"No data for {date.date()}")
                return None

        except Exception as e:
            logger.error(f"Failed to calculate growth composite: {e}")
            return None

    def calculate_inflation_composite(
        self,
        conn: Any,
        date: datetime,
    ) -> Optional[float]:
        """
        Calculate inflation composite z-score.

        Uses: CPIAUCSL, CPILFESL (month-over-month % change)

        Args:
            conn: Supabase client
            date: Calculation date

        Returns:
            Composite z-score or None if no data
        """
        try:
            # Use cached data
            cpi = self.get_cached_series("CPIAUCSL", conn)
            core_cpi = self.get_cached_series("CPILFESL", conn)

            if cpi.empty or core_cpi.empty:
                logger.warning("Missing inflation data")
                return None

            # Calculate month-over-month % change
            cpi_pct = cpi.pct_change(periods=30)  # ~1 month
            core_cpi_pct = core_cpi.pct_change(periods=30)

            # Calculate z-scores
            cpi_z = self.calculate_z_score(cpi_pct, self.window_days)
            core_cpi_z = self.calculate_z_score(core_cpi_pct, self.window_days)

            # Get values for target date
            try:
                date_pd = pd.Timestamp(date)
                cpi_val = cpi_z.loc[date_pd]
                core_val = core_cpi_z.loc[date_pd]

                # Average
                composite = np.nanmean([cpi_val, core_val])
                return float(composite) if pd.notna(composite) else None

            except KeyError:
                logger.warning(f"No inflation data for {date.date()}")
                return None

        except Exception as e:
            logger.error(f"Failed to calculate inflation composite: {e}")
            return None

    def calculate_liquidity_composite(
        self,
        conn: Any,
        date: datetime,
    ) -> Optional[float]:
        """
        Calculate liquidity composite z-score.

        Uses: M2SL growth, WALCL (Fed balance sheet) growth

        Args:
            conn: Supabase client
            date: Calculation date

        Returns:
            Composite z-score or None if no data
        """
        try:
            # Use cached data
            m2 = self.get_cached_series("M2SL", conn)
            walcl = self.get_cached_series("WALCL", conn)

            if m2.empty or walcl.empty:
                logger.warning("Missing liquidity data")
                return None

            # Calculate year-over-year growth
            m2_growth = m2.pct_change(periods=252)  # ~1 year
            walcl_growth = walcl.pct_change(periods=252)

            # Calculate z-scores
            m2_z = self.calculate_z_score(m2_growth, self.window_days)
            walcl_z = self.calculate_z_score(walcl_growth, self.window_days)

            # Get values for target date
            try:
                date_pd = pd.Timestamp(date)
                m2_val = m2_z.loc[date_pd]
                walcl_val = walcl_z.loc[date_pd]

                # Average
                composite = np.nanmean([m2_val, walcl_val])
                return float(composite) if pd.notna(composite) else None

            except KeyError:
                logger.warning(f"No liquidity data for {date.date()}")
                return None

        except Exception as e:
            logger.error(f"Failed to calculate liquidity composite: {e}")
            return None

    def calculate_rates_composite(
        self,
        conn: Any,
        date: datetime,
    ) -> Optional[float]:
        """
        Calculate rates composite z-score.

        Uses: Yield curve spread (DGS10 - DGS2)

        Args:
            conn: Supabase client
            date: Calculation date

        Returns:
            Composite z-score or None if no data
        """
        try:
            # Use cached data
            dgs10 = self.get_cached_series("DGS10", conn)
            dgs2 = self.get_cached_series("DGS2", conn)

            if dgs10.empty or dgs2.empty:
                logger.warning("Missing rates data")
                return None

            # Calculate spread
            spread = dgs10 - dgs2

            # Calculate z-score
            spread_z = self.calculate_z_score(spread, self.window_days)

            # Get value for target date
            try:
                date_pd = pd.Timestamp(date)
                spread_val = spread_z.loc[date_pd]
                return float(spread_val) if pd.notna(spread_val) else None

            except KeyError:
                logger.warning(f"No rates data for {date.date()}")
                return None

        except Exception as e:
            logger.error(f"Failed to calculate rates composite: {e}")
            return None

    def classify_regime(
        self,
        growth_z: float,
        inflation_z: float,
        rules: Dict[str, Any],
    ) -> str:
        """
        Classify economic regime.

        Args:
            growth_z: Growth z-score
            inflation_z: Inflation z-score
            rules: Regime rules from config

        Returns:
            Regime name (Goldilocks, Reflation, Stagflation, Disinflation)
        """
        if growth_z > 0 and inflation_z < 0:
            return "Goldilocks"
        elif growth_z > 0 and inflation_z > 0:
            return "Reflation"
        elif growth_z < 0 and inflation_z > 0:
            return "Stagflation"
        else:
            return "Disinflation"
