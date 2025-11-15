"""
Sector Scoring Calculator
Calculates momentum and volatility scores for sector ETFs
"""
import logging
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SectorScorer:
    """
    Calculate sector scores based on:
    - Momentum (1M, 3M, 6M returns)
    - Volatility (3M rolling std dev)
    - Regime tilt (favor certain sectors in specific regimes)
    """

    def fetch_prices(
        self,
        ticker: str,
        conn: Any,
        days_back: int = 365,
    ) -> pd.DataFrame:
        """
        Fetch price data from database.

        Args:
            ticker: ETF ticker
            conn: Supabase client
            days_back: Days of history

        Returns:
            DataFrame with OHLC data
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_back)).date()

            response = conn.table("prices_daily") \
                .select("date, open, high, low, close, adj_close") \
                .eq("ticker", ticker) \
                .gte("date", cutoff_date.isoformat()) \
                .order("date", desc=False) \
                .execute()

            if not response.data:
                return pd.DataFrame()

            df = pd.DataFrame(response.data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')

            return df.astype(float)

        except Exception as e:
            logger.error(f"Failed to fetch prices for {ticker}: {e}")
            return pd.DataFrame()

    def calculate_returns(
        self,
        ticker: str,
        conn: Any,
        periods: List[int] = [21, 63, 126],  # 1M, 3M, 6M (trading days)
    ) -> Dict[str, float]:
        """
        Calculate returns for different periods.

        Args:
            ticker: ETF ticker
            conn: Supabase client
            periods: List of periods in trading days

        Returns:
            Dict with return values
        """
        df = self.fetch_prices(ticker, conn, days_back=max(periods) + 30)

        if df.empty or len(df) < max(periods):
            logger.warning(f"Insufficient data for {ticker}")
            return {}

        close = df['close']
        results = {}

        for period in periods:
            if len(close) >= period:
                ret = (close.iloc[-1] / close.iloc[-period] - 1) * 100
                results[f"ret_{period}d"] = float(ret)

        return results

    def calculate_volatility(
        self,
        ticker: str,
        conn: Any,
        window: int = 63,  # 3 months trading days
    ) -> float:
        """
        Calculate rolling volatility.

        Args:
            ticker: ETF ticker
            conn: Supabase client
            window: Rolling window (default 63 days)

        Returns:
            Annualized volatility (%)
        """
        df = self.fetch_prices(ticker, conn, days_back=window + 30)

        if df.empty or len(df) < window:
            return 0.0

        close = df['close']
        returns = close.pct_change().dropna()

        # Calculate standard deviation and annualize
        vol = returns.rolling(window=window).std().iloc[-1] * np.sqrt(252) * 100

        return float(vol)

    def calculate_z_scores(self, values: List[float]) -> List[float]:
        """
        Standardize values to z-scores.

        Args:
            values: List of values

        Returns:
            List of z-scores
        """
        arr = np.array(values)
        mean = np.mean(arr)
        std = np.std(arr)

        if std == 0:
            return [0.0] * len(values)

        z_scores = (arr - mean) / std
        return z_scores.tolist()

    def get_regime_tilt(self, sector: str, regime: str) -> float:
        """
        Get regime tilt for sector.

        Args:
            sector: Sector ETF ticker
            regime: Current economic regime

        Returns:
            Tilt value (-1 to +2)
        """
        # Regime tilts based on sector characteristics
        tilts = {
            "Goldilocks": {  # Growth up, Inflation down
                "XLK": 2.0,  # Technology
                "XLC": 1.0,  # Communication
                "XLY": 1.0,  # Consumer Discretionary
            },
            "Reflation": {  # Growth up, Inflation up
                "XLE": 2.0,  # Energy
                "XLB": 1.0,  # Materials
                "XLF": 1.0,  # Financials
            },
            "Stagflation": {  # Growth down, Inflation up
                "XLP": 2.0,  # Consumer Staples
                "XLU": 1.0,  # Utilities
                "XLV": 1.0,  # Healthcare
            },
            "Disinflation": {  # Growth down, Inflation down
                "XLV": 2.0,  # Healthcare
                "XLP": 1.0,  # Consumer Staples
                "XLU": 1.0,  # Utilities
            },
        }

        return tilts.get(regime, {}).get(sector, 0.0)

    def score_sector(
        self,
        ticker: str,
        date: datetime,
        regime: str,
        conn: Any,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate sector score.

        Formula:
        score = z(ret1m) + z(ret3m) + 0.5*z(ret6m) - 0.5*z(vol3m) + regime_tilt

        Args:
            ticker: Sector ETF ticker
            date: Calculation date
            regime: Current regime
            conn: Supabase client
            config: ETL config

        Returns:
            Dict with score and components
        """
        logger.info(f"Scoring sector {ticker}")

        # Calculate returns
        returns = self.calculate_returns(ticker, conn, periods=[21, 63, 126])

        # Calculate volatility
        vol = self.calculate_volatility(ticker, conn, window=63)

        # Get regime tilt
        tilt = self.get_regime_tilt(ticker, regime)

        # These will be z-scored across all sectors
        components = {
            "ret1m": returns.get("ret_21d", 0.0),
            "ret3m": returns.get("ret_63d", 0.0),
            "ret6m": returns.get("ret_126d", 0.0),
            "vol3m": vol,
            "regime_tilt": tilt,
        }

        return {
            "sector": ticker,
            "components": components,
        }

    def score_all_sectors(
        self,
        date: datetime,
        regime: str,
        conn: Any,
        config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Score all sectors with cross-sectional z-scores.

        Args:
            date: Calculation date
            regime: Current regime
            conn: Supabase client
            config: ETL config

        Returns:
            List of sector scores ready for database
        """
        logger.info(f"Scoring all sectors for {date.date()}")

        sector_etfs = config.get("sector_etfs", [])
        tickers = [s["ticker"] for s in sector_etfs]

        # Calculate components for all sectors
        sector_data = []
        for ticker in tickers:
            sector_info = self.score_sector(ticker, date, regime, conn, config)
            sector_data.append(sector_info)

        # Extract components for z-scoring
        ret1m_vals = [s["components"]["ret1m"] for s in sector_data]
        ret3m_vals = [s["components"]["ret3m"] for s in sector_data]
        ret6m_vals = [s["components"]["ret6m"] for s in sector_data]
        vol3m_vals = [s["components"]["vol3m"] for s in sector_data]

        # Calculate z-scores
        ret1m_z = self.calculate_z_scores(ret1m_vals)
        ret3m_z = self.calculate_z_scores(ret3m_vals)
        ret6m_z = self.calculate_z_scores(ret6m_vals)
        vol3m_z = self.calculate_z_scores(vol3m_vals)

        # Get weights from config
        weights = config.get("scoring_weights", {}).get("sector", {})
        w_ret1m = weights.get("ret1m", 1.0)
        w_ret3m = weights.get("ret3m", 1.0)
        w_ret6m = weights.get("ret6m", 0.5)
        w_vol3m = weights.get("vol3m", -0.5)  # Negative weight (lower vol is better)
        w_tilt = weights.get("regime_tilt", 1.0)

        # Calculate final scores
        results = []
        for i, sector_info in enumerate(sector_data):
            comps = sector_info["components"]

            score = (
                w_ret1m * ret1m_z[i] +
                w_ret3m * ret3m_z[i] +
                w_ret6m * ret6m_z[i] +
                w_vol3m * vol3m_z[i] +
                w_tilt * comps["regime_tilt"]
            )

            results.append({
                "sector": sector_info["sector"],
                "score": round(score, 2),
                "components": {
                    **comps,
                    "ret1m_z": round(ret1m_z[i], 2),
                    "ret3m_z": round(ret3m_z[i], 2),
                    "ret6m_z": round(ret6m_z[i], 2),
                    "vol3m_z": round(vol3m_z[i], 2),
                    "formula": "z(ret1m) + z(ret3m) + 0.5*z(ret6m) - 0.5*z(vol3m) + regime_tilt",
                },
            })

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"Scored {len(results)} sectors")
        return results
