import time
import requests
import pandas as pd
from datetime import datetime

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

# 브라우저 흉내 내는 헤더
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; .NET CLR 1.0.3705;)",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

def fetch_chart_like_browser(ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
    """
    Yahoo Finance chart API를 브라우저처럼 직접 호출해서
    AAPL 같은 티커의 OHLCV를 DataFrame으로 반환.
    """
    url = YAHOO_CHART_URL.format(ticker=ticker)

    # Yahoo chart API는 period1, period2를 Unix timestamp로 받음
    period1 = int(start.timestamp())
    period2 = int(end.timestamp())

    params = {
        "period1": period1,
        "period2": period2,
        "interval": "1d",
        "events": "div,split",
        "includePrePost": "false",
    }

    # Referer도 넣어주면 조금 더 브라우저스럽게 보임
    headers = {
        **BROWSER_HEADERS,
        "Referer": f"www.google.com",
    }

    resp = requests.get(url, headers=headers, params=params, timeout=10)

    if resp.status_code == 429:
        # 여기서 바로 yfinance와 똑같이 JSON 파싱 에러 나기 전에 방어
        raise RuntimeError(f"Yahoo 429 Too Many Requests for {ticker}")

    resp.raise_for_status()
    data = resp.json()

    # JSON 구조 파싱
    result_list = data.get("chart", {}).get("result")
    if not result_list:
        raise RuntimeError(f"No chart result for {ticker}: {data.get('chart', {}).get('error')}")

    result = result_list[0]
    timestamps = result.get("timestamp", [])
    indicators = result.get("indicators", {})
    quote_list = indicators.get("quote", [])
    adjclose_list = indicators.get("adjclose", [])

    if not timestamps or not quote_list:
        raise RuntimeError(f"Incomplete data for {ticker}")

    quote = quote_list[0]

    df = pd.DataFrame({
        "Open": quote.get("open", []),
        "High": quote.get("high", []),
        "Low": quote.get("low", []),
        "Close": quote.get("close", []),
        "Volume": quote.get("volume", []),
    }, index=pd.to_datetime(timestamps, unit="s"))

    if adjclose_list:
        df["Adj Close"] = adjclose_list[0].get("adjclose", [])
    else:
        df["Adj Close"] = df["Close"]

    # 인덱스 이름처럼 yfinance랑 비슷하게 맞춰주면 이후 코드 재사용 쉽다
    df.index.name = "Date"

    return df

# 테스트 실행
if __name__ == "__main__":
    try:
        print("Testing Yahoo Finance API with new User-Agent...")
        df = fetch_chart_like_browser("AAPL", datetime(2025, 1, 1), datetime(2025, 1, 31))
        print(f"✅ Success! Got {len(df)} rows of data")
        print("Sample data:")
        print(df.head())
    except Exception as e:
        print(f"❌ Error: {e}")