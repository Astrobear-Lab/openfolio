"""Generate seed data for testing without API keys"""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import numpy as np

def generate_macro_points(series_code: str, days: int = 365) -> List[Dict[str, Any]]:
    """Generate synthetic macro time series"""
    points = []
    base_value = {
        "CPIAUCSL": 300,
        "CPILFESL": 310,
        "INDPRO": 100,
        "PAYEMS": 155000,
        "UNRATE": 3.8,
        "M2SL": 21000,
        "WALCL": 8500,
        "DGS10": 4.2,
        "DGS2": 4.5,
    }.get(series_code, 100)

    trend = random.uniform(-0.02, 0.05)  # Annual trend
    volatility = random.uniform(0.005, 0.02)

    end_date = datetime.now().date()
    for i in range(days):
        date = end_date - timedelta(days=days - i)
        # Random walk with trend
        value = base_value * (1 + trend * i / 365 + random.gauss(0, volatility))

        points.append({
            "date": date,
            "value": round(value, 2),
            "revision_of": None,
            "raw_json": {"synthetic": True},
            "url": f"https://fred.stlouisfed.org/series/{series_code}"
        })

    return points

def generate_prices(ticker: str, days: int = 365) -> List[Dict[str, Any]]:
    """Generate synthetic price data"""
    prices = []
    base_price = random.uniform(50, 500)
    drift = random.uniform(-0.001, 0.002)
    volatility = random.uniform(0.01, 0.03)

    end_date = datetime.now().date()
    current_price = base_price

    for i in range(days):
        date = end_date - timedelta(days=days - i)

        # Geometric Brownian motion
        daily_return = drift + volatility * random.gauss(0, 1)
        current_price *= (1 + daily_return)

        open_price = current_price * (1 + random.gauss(0, 0.005))
        high_price = max(open_price, current_price) * (1 + abs(random.gauss(0, 0.01)))
        low_price = min(open_price, current_price) * (1 - abs(random.gauss(0, 0.01)))
        close_price = current_price

        prices.append({
            "ticker": ticker,
            "date": date,
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "adj_close": round(close_price, 2),
            "volume": random.randint(1000000, 100000000),
            "source": "seed_data",
            "raw_json": {"synthetic": True}
        })

    return prices

def calculate_z_score(series: List[float], window: int = 36) -> List[float]:
    """Calculate rolling z-scores"""
    arr = np.array(series)
    z_scores = []

    for i in range(len(arr)):
        if i < window:
            # Not enough data
            z_scores.append(0.0)
        else:
            window_data = arr[i-window:i]
            mean = np.mean(window_data)
            std = np.std(window_data)
            if std > 0:
                z = (arr[i] - mean) / std
            else:
                z = 0.0
            z_scores.append(z)

    return z_scores

def classify_regime(growth_z: float, inflation_z: float) -> str:
    """Classify economic regime"""
    if growth_z > 0 and inflation_z < 0:
        return "Goldilocks"
    elif growth_z > 0 and inflation_z > 0:
        return "Reflation"
    elif growth_z < 0 and inflation_z > 0:
        return "Stagflation"
    else:
        return "Disinflation"

def generate_event_docs(ticker: str, count: int = 5) -> List[Dict[str, Any]]:
    """Generate synthetic event documents"""
    events = []
    event_types = ["Earnings", "8-K Filing", "10-Q Filing", "Dividend"]

    for i in range(count):
        event_type = random.choice(event_types)
        sentiment = random.uniform(-0.5, 0.9)

        events.append({
            "ticker": ticker,
            "dt": datetime.now() - timedelta(days=random.randint(1, 90)),
            "type": event_type,
            "url": f"https://sec.gov/edgar/{ticker}/{i}",
            "title": f"{ticker} {event_type} - Q{random.randint(1,4)} 2024",
            "body": f"Synthetic event document for {ticker}. " * 20,
            "sentiment": sentiment,
            "guidance": "Positive" if sentiment > 0.3 else "Mixed" if sentiment > -0.2 else "Negative",
            "surprise_eps": random.uniform(-10, 10) if event_type == "Earnings" else None,
            "topics": random.sample(["Revenue", "Margins", "Guidance", "AI", "Growth"], 3),
            "quotes": [
                f"We are pleased with the {random.choice(['strong', 'solid', 'challenging'])} performance",
                f"Looking ahead, we expect {random.choice(['continued growth', 'headwinds', 'stability'])}"
            ]
        })

    return events
