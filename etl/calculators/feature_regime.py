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
    """

    def __init__(self, window_months: int = 36):
        """
        Initialize calculator.

        Args:
            window_months: Rolling window for z-score (default 36 months)
        """
        self.window_months = window_months
        self.window_days = window_months * 30  # Approximate

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
    ) -> Optional[Tuple[float, Dict[str, Any]]]:
        """
        Calculate growth composite z-score.

        Uses: INDPRO, PAYEMS, UNRATE (inverted)

        Args:
            conn: Supabase client
            date: Calculation date

        Returns:
            Tuple of (composite_z_score, details_dict) or None if no data
        """
        try:
            # Fetch series
            indpro = self.fetch_macro_series("INDPRO", conn)
            payems = self.fetch_macro_series("PAYEMS", conn)
            unrate = self.fetch_macro_series("UNRATE", conn)

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

                details = {
                    "inputs": {
                        "INDPRO_z": float(indpro_val) if pd.notna(indpro_val) else None,
                        "PAYEMS_z": float(payems_val) if pd.notna(payems_val) else None,
                        "UNRATE_z_inv": float(unrate_val) if pd.notna(unrate_val) else None,
                    },
                    "method": "average of z-scores",
                    "window_months": self.window_months,
                }

                return float(composite), details

            except KeyError:
                logger.warning(f"No data for {date}")
                return None

        except Exception as e:
            logger.error(f"Failed to calculate growth composite: {e}")
            return None

    def calculate_inflation_composite(
        self,
        conn: Any,
        date: datetime,
    ) -> Optional[Tuple[float, Dict[str, Any]]]:
        """
        Calculate inflation composite z-score.

        Uses: CPIAUCSL, CPILFESL (month-over-month % change)

        Args:
            conn: Supabase client
            date: Calculation date

        Returns:
            Tuple of (composite_z_score, details_dict) or None if no data
        """
        try:
            # Fetch series
            cpi = self.fetch_macro_series("CPIAUCSL", conn)
            core_cpi = self.fetch_macro_series("CPILFESL", conn)

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

                details = {
                    "inputs": {
                        "CPI_z": float(cpi_val) if pd.notna(cpi_val) else None,
                        "CoreCPI_z": float(core_val) if pd.notna(core_val) else None,
                    },
                    "method": "average of MoM % change z-scores",
                    "window_months": self.window_months,
                }

                return float(composite), details

            except KeyError:
                logger.warning(f"No inflation data for {date}")
                return None

        except Exception as e:
            logger.error(f"Failed to calculate inflation composite: {e}")
            return None

    def calculate_liquidity_composite(
        self,
        conn: Any,
        date: datetime,
    ) -> Optional[Tuple[float, Dict[str, Any]]]:
        """
        Calculate liquidity composite z-score.

        Uses: M2SL growth, WALCL (Fed balance sheet) growth

        Args:
            conn: Supabase client
            date: Calculation date

        Returns:
            Tuple of (composite_z_score, details_dict) or None if no data
        """
        try:
            # Fetch series
            m2 = self.fetch_macro_series("M2SL", conn)
            walcl = self.fetch_macro_series("WALCL", conn)

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

                details = {
                    "inputs": {
                        "M2_growth_z": float(m2_val) if pd.notna(m2_val) else None,
                        "WALCL_growth_z": float(walcl_val) if pd.notna(walcl_val) else None,
                    },
                    "method": "average of YoY growth z-scores",
                    "window_months": self.window_months,
                }

                return float(composite), details

            except KeyError:
                logger.warning(f"No liquidity data for {date}")
                return None

        except Exception as e:
            logger.error(f"Failed to calculate liquidity composite: {e}")
            return None

    def calculate_rates_composite(
        self,
        conn: Any,
        date: datetime,
    ) -> Optional[Tuple[float, Dict[str, Any]]]:
        """
        Calculate rates composite z-score.

        Uses: Yield curve spread (DGS10 - DGS2)

        Args:
            conn: Supabase client
            date: Calculation date

        Returns:
            Tuple of (composite_z_score, details_dict) or None if no data
        """
        try:
            # Fetch series
            dgs10 = self.fetch_macro_series("DGS10", conn)
            dgs2 = self.fetch_macro_series("DGS2", conn)

            # Calculate spread
            spread = dgs10 - dgs2

            # Calculate z-score
            spread_z = self.calculate_z_score(spread, self.window_days)

            # Get value for target date
            try:
                date_pd = pd.Timestamp(date)
                spread_val = spread_z.loc[date_pd]

                details = {
                    "inputs": {
                        "10Y": float(dgs10.loc[date_pd]) if pd.notna(dgs10.loc[date_pd]) else None,
                        "2Y": float(dgs2.loc[date_pd]) if pd.notna(dgs2.loc[date_pd]) else None,
                        "spread": float(spread.loc[date_pd]) if pd.notna(spread.loc[date_pd]) else None,
                    },
                    "method": "z-score of 10Y-2Y spread",
                    "window_months": self.window_months,
                }

                return float(spread_val), details

            except KeyError:
                logger.warning(f"No rates data for {date}")
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

    def calculate_all_features(
        self,
        conn: Any,
        date: datetime,
        config: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Calculate all features and regime for a date.

        Args:
            conn: Supabase client
            date: Calculation date
            config: ETL config

        Returns:
            Tuple of (features_dict, regime_dict)
        """
        logger.info(f"Calculating features and regime for {date.date()}")

        # Calculate composites
        growth_z, growth_details = self.calculate_growth_composite(conn, date)
        inflation_z, inflation_details = self.calculate_inflation_composite(conn, date)
        liquidity_z, liquidity_details = self.calculate_liquidity_composite(conn, date)
        rates_z, rates_details = self.calculate_rates_composite(conn, date)

        # Classify regime
        regime = self.classify_regime(
            growth_z,
            inflation_z,
            config.get("regime_rules", {}),
        )

        # Prepare features dict
        features = {
            "growth_composite": {
                "value": growth_z,
                "details": growth_details,
            },
            "inflation_composite": {
                "value": inflation_z,
                "details": inflation_details,
            },
            "liquidity_composite": {
                "value": liquidity_z,
                "details": liquidity_details,
            },
            "rates_composite": {
                "value": rates_z,
                "details": rates_details,
            },
        }

        # Prepare regime dict
        regime_data = {
            "growth_z": growth_z,
            "inflation_z": inflation_z,
            "liquidity_z": liquidity_z,
            "rates_z": rates_z,
            "regime": regime,
            "details": {
                "rules": config.get("regime_rules", {}),
                "calculated_at": datetime.now().isoformat(),
                "window_months": self.window_months,
            },
        }

        logger.info(f"Regime: {regime} (growth: {growth_z:.2f}, inflation: {inflation_z:.2f})")

        return features, regime_data
