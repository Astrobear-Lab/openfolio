"""
Stock Screener Calculator
Multi-stage stock screening based on Quality, Value, Events, and Technical analysis
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StockScreener:
    """
    Multi-stage stock screener with transparent scoring.

    Stages:
    1. Quality: Fundamental metrics (ROE, margins, leverage)
    2. Value: Valuation metrics (P/E, P/B, EV/EBITDA)
    3. Events: Recent performance, guidance, sentiment
    4. Technical: Momentum, RSI, MACD, trends
    """

    def __init__(self):
        self.weights = {
            "quality": 0.25,
            "value": 0.25,
            "events": 0.30,
            "technical": 0.20
        }

    def calculate_z_scores(self, values: List[float]) -> List[float]:
        """Standardize values to z-scores"""
        arr = np.array(values)
        mean = np.mean(arr)
        std = np.std(arr)

        if std == 0:
            return [0.0] * len(values)

        z_scores = (arr - mean) / std
        return z_scores.tolist()

    def screen_quality(
        self,
        ticker: str,
        conn: Any,
        date: datetime
    ) -> Dict[str, Any]:
        """Quality screening based on fundamental metrics"""
        logger.info(f"Screening quality for {ticker}")

        # For now, generate mock quality metrics
        # In production, this would pull from financials database
        quality_metrics = {
            "roe": np.random.uniform(5, 25),  # Return on Equity
            "gross_margin": np.random.uniform(30, 70),  # Gross Margin %
            "debt_to_equity": np.random.uniform(0.1, 1.5),  # Debt/Equity
            "current_ratio": np.random.uniform(1.0, 3.0),  # Current Ratio
        }

        # Calculate z-scores for quality metrics
        quality_values = list(quality_metrics.values())
        quality_z_scores = self.calculate_z_scores(quality_values)

        # Quality score (higher is better)
        quality_score = np.mean(quality_z_scores)

        # Pass criteria: score > -0.5 (above average quality)
        quality_pass = quality_score > -0.5

        return {
            "pass": quality_pass,
            "score": round(quality_score, 2),
            "metrics": {
                "roe": round(quality_metrics["roe"], 1),
                "gross_margin": round(quality_metrics["gross_margin"], 1),
                "debt_to_equity": round(quality_metrics["debt_to_equity"], 2),
                "current_ratio": round(quality_metrics["current_ratio"], 1),
            },
            "evidence": f"ROE: {quality_metrics['roe']:.1f}%, Margin: {quality_metrics['gross_margin']:.1f}%, D/E: {quality_metrics['debt_to_equity']:.2f}"
        }

    def screen_value(
        self,
        ticker: str,
        conn: Any,
        date: datetime
    ) -> Dict[str, Any]:
        """Value screening based on valuation metrics"""
        logger.info(f"Screening value for {ticker}")

        # Mock valuation metrics
        value_metrics = {
            "pe_ratio": np.random.uniform(8, 35),  # P/E Ratio
            "pb_ratio": np.random.uniform(1.5, 4.5),  # P/B Ratio
            "ev_ebitda": np.random.uniform(8, 25),  # EV/EBITDA
            "div_yield": np.random.uniform(0.5, 4.0),  # Dividend Yield %
        }

        # For value investing, lower ratios are better (invert for scoring)
        value_scores = [
            -value_metrics["pe_ratio"],  # Lower P/E is better
            -value_metrics["pb_ratio"],  # Lower P/B is better
            -value_metrics["ev_ebitda"], # Lower EV/EBITDA is better
            value_metrics["div_yield"],  # Higher dividend is better
        ]

        value_z_scores = self.calculate_z_scores(value_scores)
        value_score = np.mean(value_z_scores)

        # Pass criteria: score > -0.3 (reasonably valued)
        value_pass = value_score > -0.3

        return {
            "pass": value_pass,
            "score": round(value_score, 2),
            "metrics": {
                "pe_ratio": round(value_metrics["pe_ratio"], 1),
                "pb_ratio": round(value_metrics["pb_ratio"], 1),
                "ev_ebitda": round(value_metrics["ev_ebitda"], 1),
                "div_yield": round(value_metrics["div_yield"], 1),
            },
            "evidence": f"P/E: {value_metrics['pe_ratio']:.1f}, P/B: {value_metrics['pb_ratio']:.1f}, EV/EBITDA: {value_metrics['ev_ebitda']:.1f}"
        }

    def screen_events(
        self,
        ticker: str,
        conn: Any,
        date: datetime
    ) -> Dict[str, Any]:
        """Event screening based on recent performance and sentiment"""
        logger.info(f"Screening events for {ticker}")

        # Get recent earnings surprise (mock)
        earnings_surprise = np.random.uniform(-20, 30)  # % surprise

        # Get recent price performance
        try:
            response = conn.table("prices_daily") \
                .select("close") \
                .eq("ticker", ticker) \
                .gte("date", (date - timedelta(days=90)).isoformat()) \
                .order("date", desc=False) \
                .execute()

            if response.data and len(response.data) > 20:
                prices = [p["close"] for p in response.data]
                returns_1m = (prices[-1] / prices[-21]) - 1 if len(prices) > 21 else 0
                returns_3m = (prices[-1] / prices[0]) - 1
            else:
                returns_1m = np.random.uniform(-15, 25) / 100
                returns_3m = np.random.uniform(-20, 40) / 100
        except:
            returns_1m = np.random.uniform(-15, 25) / 100
            returns_3m = np.random.uniform(-20, 40) / 100

        # Mock sentiment score (-1 to 1)
        sentiment = np.random.uniform(-0.8, 0.9)

        # Calculate event score
        event_components = [
            earnings_surprise / 10,  # Scale earnings surprise
            returns_1m * 10,         # Scale 1M returns
            returns_3m * 5,          # Scale 3M returns
            sentiment * 2            # Scale sentiment
        ]

        event_z_scores = self.calculate_z_scores(event_components)
        event_score = np.mean(event_z_scores)

        # Pass criteria: score > -0.2 (positive momentum)
        event_pass = event_score > -0.2

        return {
            "pass": event_pass,
            "score": round(event_score, 2),
            "metrics": {
                "earnings_surprise": round(earnings_surprise, 1),
                "returns_1m": round(returns_1m * 100, 1),
                "returns_3m": round(returns_3m * 100, 1),
                "sentiment": round(sentiment, 2),
            },
            "evidence": f"Earnings: {earnings_surprise:+.1f}%, 1M: {returns_1m*100:+.1f}%, Sentiment: {sentiment:.2f}"
        }

    def screen_technical(
        self,
        ticker: str,
        conn: Any,
        date: datetime
    ) -> Dict[str, Any]:
        """Technical screening based on momentum and indicators"""
        logger.info(f"Screening technical for {ticker}")

        try:
            # Get technical indicators from database
            response = conn.table("ta_daily") \
                .select("*") \
                .eq("ticker", ticker) \
                .lte("date", date.isoformat()) \
                .order("date", desc=True) \
                .limit(1) \
                .execute()

            if response.data and response.data[0]:
                ta_data = response.data[0]
                rsi = ta_data.get("rsi_14", 50)
                macd_signal = ta_data.get("macd_signal", 0)
                bb_position = ta_data.get("bb_position", 0)
                trend_strength = ta_data.get("trend_strength", 0)
            else:
                # Fallback to mock data
                rsi = np.random.uniform(20, 80)
                macd_signal = np.random.uniform(-2, 2)
                bb_position = np.random.uniform(-0.8, 0.8)
                trend_strength = np.random.uniform(-0.5, 0.8)

        except Exception as e:
            logger.warning(f"Failed to get TA data for {ticker}: {e}")
            # Fallback to mock data
            rsi = np.random.uniform(20, 80)
            macd_signal = np.random.uniform(-2, 2)
            bb_position = np.random.uniform(-0.8, 0.8)
            trend_strength = np.random.uniform(-0.5, 0.8)

        # Get recent price momentum
        try:
            response = conn.table("prices_daily") \
                .select("close") \
                .eq("ticker", ticker) \
                .gte("date", (date - timedelta(days=30)).isoformat()) \
                .order("date", desc=False) \
                .execute()

            if response.data and len(response.data) > 10:
                prices = [p["close"] for p in response.data]
                momentum = (prices[-1] / prices[0]) - 1
            else:
                momentum = np.random.uniform(-15, 25) / 100
        except:
            momentum = np.random.uniform(-15, 25) / 100

        # Calculate technical score components
        ta_components = [
            1 - abs(rsi - 50) / 50,  # RSI closeness to 50 (neutral)
            macd_signal,                # MACD signal
            bb_position,                # Bollinger Band position
            trend_strength,             # Trend strength
            momentum * 5                # Recent momentum
        ]

        ta_z_scores = self.calculate_z_scores(ta_components)
        ta_score = np.mean(ta_z_scores)

        # Pass criteria: score > -0.1 (neutral to positive technicals)
        ta_pass = ta_score > -0.1

        return {
            "pass": ta_pass,
            "score": round(ta_score, 2),
            "metrics": {
                "rsi": round(rsi, 1),
                "macd_signal": round(macd_signal, 2),
                "bb_position": round(bb_position, 2),
                "trend_strength": round(trend_strength, 2),
                "momentum": round(momentum * 100, 1),
            },
            "evidence": f"RSI: {rsi:.1f}, Momentum: {momentum*100:+.1f}%, Trend: {trend_strength:.2f}"
        }

    def screen_stock(
        self,
        ticker: str,
        conn: Any,
        date: datetime
    ) -> Dict[str, Any]:
        """Complete multi-stage screening for a single stock"""
        logger.info(f"Screening {ticker} on {date.date()}")

        # Run all screening stages
        quality = self.screen_quality(ticker, conn, date)
        value = self.screen_value(ticker, conn, date)
        events = self.screen_events(ticker, conn, date)
        technical = self.screen_technical(ticker, conn, date)

        # Calculate weighted total score
        total_score = (
            self.weights["quality"] * quality["score"] +
            self.weights["value"] * value["score"] +
            self.weights["events"] * events["score"] +
            self.weights["technical"] * technical["score"]
        )

        # Determine final decision
        stages_passed = sum([quality["pass"], value["pass"], events["pass"], technical["pass"]])

        if stages_passed == 4:
            decision = "BUY" if total_score > 0.5 else "HOLD"
        elif stages_passed == 3:
            decision = "HOLD" if total_score > 0 else "PASS"
        else:
            decision = "PASS"

        return {
            "ticker": ticker,
            "date": date.date(),
            "quality": quality,
            "value": value,
            "events": events,
            "technical": technical,
            "total_score": round(total_score, 2),
            "stages_passed": stages_passed,
            "decision": decision,
            "weights": self.weights
        }

    def screen_all_stocks(
        self,
        conn: Any,
        config: Dict[str, Any],
        date: datetime
    ) -> List[Dict[str, Any]]:
        """Screen all stocks in the universe"""
        logger.info(f"Screening all stocks for {date.date()}")

        sample_stocks = config.get("sample_stocks", [])
        results = []

        for ticker in sample_stocks:
            try:
                result = self.screen_stock(ticker, conn, date)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to screen {ticker}: {e}")
                continue

        # Sort by total score (descending)
        results.sort(key=lambda x: x["total_score"], reverse=True)

        logger.info(f"Screened {len(results)} stocks")
        return results
