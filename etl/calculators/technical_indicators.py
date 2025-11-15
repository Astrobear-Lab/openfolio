"""
Technical Indicators Calculator
Calculates RSI, MACD, SMA, ATR from price data
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class TechnicalCalculator:
    """
    Calculate technical analysis indicators from price data.

    All indicators use standard parameters:
    - RSI: 14 periods
    - MACD: 12/26/9
    - SMA: 20, 50, 200 days
    - ATR: 14 periods
    """

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).

        Formula:
        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss

        Args:
            prices: Series of closing prices
            period: RSI period (default 14)

        Returns:
            Series of RSI values (0-100)
        """
        # Calculate price changes
        delta = prices.diff()

        # Separate gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)

        # Calculate exponential moving averages
        avg_gains = gains.ewm(span=period, adjust=False).mean()
        avg_losses = losses.ewm(span=period, adjust=False).mean()

        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_macd(
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> tuple[pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).

        Args:
            prices: Series of closing prices
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)

        Returns:
            Tuple of (macd_line, signal_line)
        """
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()

        return macd_line, signal_line

    @staticmethod
    def calculate_sma(
        prices: pd.Series,
        periods: List[int] = [20, 50, 200]
    ) -> Dict[int, pd.Series]:
        """
        Calculate Simple Moving Averages.

        Args:
            prices: Series of closing prices
            periods: List of periods (default [20, 50, 200])

        Returns:
            Dict mapping period to SMA series
        """
        smas = {}
        for period in periods:
            smas[period] = prices.rolling(window=period).mean()

        return smas

    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate Average True Range (ATR).

        True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
        ATR = EMA of True Range

        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of closing prices
            period: ATR period (default 14)

        Returns:
            Series of ATR values
        """
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.ewm(span=period, adjust=False).mean()

        return atr

    def calculate_all_for_ticker(
        self,
        ticker: str,
        conn: Any,
    ) -> List[Dict[str, Any]]:
        """
        Calculate all technical indicators for a ticker.

        Args:
            ticker: Stock ticker symbol
            conn: Supabase client connection

        Returns:
            List of dicts ready for db.upsert_ta_daily()
        """
        logger.info(f"Calculating technical indicators for {ticker}")

        try:
            # Fetch price data from database
            response = conn.table("prices_daily") \
                .select("date, open, high, low, close, adj_close") \
                .eq("ticker", ticker) \
                .order("date", desc=False) \
                .execute()

            if not response.data or len(response.data) < 200:
                logger.warning(f"Insufficient price data for {ticker} (need 200+ days for SMA200)")
                return []

            # Convert to DataFrame
            df = pd.DataFrame(response.data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')

            # Calculate indicators
            close = df['close'].astype(float)
            high = df['high'].astype(float)
            low = df['low'].astype(float)

            rsi = self.calculate_rsi(close)
            macd, macd_signal = self.calculate_macd(close)
            smas = self.calculate_sma(close)
            atr = self.calculate_atr(high, low, close)

            # Prepare results
            results = []
            for date in df.index:
                # Generate flags
                flags = {}

                # RSI signals
                if pd.notna(rsi.loc[date]):
                    if rsi.loc[date] > 70:
                        flags['rsi_overbought'] = True
                    elif rsi.loc[date] < 30:
                        flags['rsi_oversold'] = True

                # MACD crossover
                if pd.notna(macd.loc[date]) and pd.notna(macd_signal.loc[date]):
                    if date > df.index[0]:  # Not first day
                        prev_date = df.index[df.index < date][-1]
                        if macd.loc[prev_date] < macd_signal.loc[prev_date] and \
                           macd.loc[date] > macd_signal.loc[date]:
                            flags['macd_bullish_cross'] = True
                        elif macd.loc[prev_date] > macd_signal.loc[prev_date] and \
                             macd.loc[date] < macd_signal.loc[date]:
                            flags['macd_bearish_cross'] = True

                # Price vs SMA200
                if pd.notna(smas[200].loc[date]):
                    if close.loc[date] > smas[200].loc[date]:
                        flags['above_sma200'] = True
                    else:
                        flags['below_sma200'] = True

                results.append({
                    "ticker": ticker,
                    "date": date.date(),
                    "rsi14": float(rsi.loc[date]) if pd.notna(rsi.loc[date]) else None,
                    "macd": float(macd.loc[date]) if pd.notna(macd.loc[date]) else None,
                    "macd_signal": float(macd_signal.loc[date]) if pd.notna(macd_signal.loc[date]) else None,
                    "sma20": float(smas[20].loc[date]) if pd.notna(smas[20].loc[date]) else None,
                    "sma50": float(smas[50].loc[date]) if pd.notna(smas[50].loc[date]) else None,
                    "sma200": float(smas[200].loc[date]) if pd.notna(smas[200].loc[date]) else None,
                    "atr14": float(atr.loc[date]) if pd.notna(atr.loc[date]) else None,
                    "flags": flags,
                })

            logger.info(f"Calculated {len(results)} TA data points for {ticker}")
            return results

        except Exception as e:
            logger.error(f"Failed to calculate TA for {ticker}: {e}")
            return []
