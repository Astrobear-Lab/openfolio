# Openfolio ETL Pipeline

Complete ETL pipeline for the Openfolio investment analysis platform. Fetches macro data, prices, events, and calculates technical indicators, regime classification, and sector scores.

## Architecture

The ETL pipeline is organized into 3 phases:

### Phase 1: Data Collection (Parallel)
- **1.1 Macro Data**: Fetches 9 economic indicators from FRED API
- **1.2 Prices**: Fetches EOD prices for 11 sector ETFs + 20 stocks from Yahoo Finance
- **1.3 Events**: Fetches SEC filings (8-K, 10-Q) from SEC EDGAR

### Phase 2: Calculations (Sequential)
- **2.1 Technical Indicators**: RSI, MACD, SMA, ATR for all tickers
- **2.2 Features & Regime**: Macro z-scores and regime classification
- **2.3 Sector Scoring**: Momentum + volatility + regime tilt scoring

### Phase 3: AI Allocation
- Generates portfolio allocations for 3 AI agents (Aggressive, Balanced, Defensive)

## Directory Structure

```
etl/
├── utils/                      # Infrastructure utilities
│   ├── rate_limiter.py        # Token bucket rate limiting
│   ├── cache_manager.py       # File-based caching
│   └── retry_logic.py         # Exponential backoff retry
├── collectors/                 # Data collectors
│   ├── base_collector.py      # Common collector functionality
│   ├── fred_collector.py      # FRED API (macro data)
│   ├── yahoo_collector.py     # Yahoo Finance (prices)
│   └── sec_collector.py       # SEC EDGAR (filings)
├── calculators/               # Data processors
│   ├── technical_indicators.py # TA calculations
│   ├── feature_regime.py      # Macro features & regime
│   └── sector_scoring.py      # Sector momentum scoring
├── db.py                      # Database operations
├── config.json                # ETL configuration
├── run_all.py                 # Main pipeline orchestrator
└── test_imports.py            # Import validation test
```

## Setup

### 1. Install Python Dependencies

```bash
cd etl
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with:

```bash
# Database
DATABASE_URL="postgresql://user:password@host:5432/dbname"

# API Keys
FRED_API_KEY="your_fred_api_key"          # Get from: https://fred.stlouisfed.org/
ALPHA_VANTAGE_API_KEY="your_av_key"       # (Optional)
FMP_API_KEY="your_fmp_key"                # (Optional)
OPENAI_API_KEY="your_openai_key"          # (Optional)

# SEC User-Agent (required by SEC)
SEC_USER_AGENT="YourApp contact@email.com"

# Optional: Use seed data instead of real APIs
USE_SEED_DATA="false"
```

### 3. Initialize Database

Run the SQL schema:

```bash
psql $DATABASE_URL < ../supabase/schema.sql
psql $DATABASE_URL < ../supabase/seed.sql
```

## Usage

### Run Full ETL Pipeline

```bash
cd etl
python run_all.py
```

This executes all 3 phases sequentially.

### Test Imports (Validation)

```bash
python test_imports.py
```

Validates that all modules can be imported correctly.

### Run Individual Components

```python
from collectors.fred_collector import FREDCollector
from datetime import date, timedelta

collector = FREDCollector()
data = collector.fetch_series(
    series_code="CPIAUCSL",
    start_date=date(2020, 1, 1),
    end_date=date.today()
)
```

## Configuration

Edit `config.json` to customize:

- **macro_series**: Which FRED series to fetch
- **sector_etfs**: Which sector ETFs to track
- **sample_stocks**: Which stocks to analyze
- **regime_rules**: Regime classification thresholds
- **scoring_weights**: Sector/stock scoring weights

## Data Sources & Rate Limits

| Source | Rate Limit | API Key Required | Notes |
|--------|------------|------------------|-------|
| FRED | 120 req/day | Yes | Free registration |
| Yahoo Finance | ~100 req/min | No | Soft limit |
| SEC EDGAR | 10 req/sec | No | User-Agent required |

## Caching

All API responses are cached locally in `./cache/`:

- **Default TTL**: 24 hours
- **Format**: JSON files with metadata
- **Location**: `./cache/{source}_{key}.json`

To force refresh, delete cache files or set `force_refresh=True`.

## Retry & Error Handling

- **Retry Strategy**: Exponential backoff (max 3 retries)
- **Delays**: 2s, 4s, 8s
- **Fallback**: Seed data if API unavailable
- **Rate Limiting**: Token bucket algorithm

## Database Tables

The pipeline writes to these Supabase tables:

### Macro Data
- `macro_series`: Series metadata (CPIAUCSL, INDPRO, etc.)
- `macro_points`: Time series values
- `macro_features_daily`: Calculated z-scores
- `macro_regime_daily`: Regime classification

### Prices & TA
- `prices_daily`: OHLCV data
- `ta_daily`: Technical indicators (RSI, MACD, SMA, ATR)

### Sectors
- `sector_scores`: Daily sector momentum scores

### Events
- `event_docs`: SEC filings
- `event_nlp`: NLP analysis of filings

### AI Agents
- `ai_agents`: Agent configurations
- `ai_weights_history`: Portfolio weights over time
- `ai_performance`: Performance metrics
- `decision_logs`: Decision audit trail

## Logging

Logs are written to stdout with format:

```
2025-11-15 10:30:45 - fred_collector - INFO - Fetched 36 points for CPIAUCSL
```

Set log level via environment:

```bash
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
python run_all.py
```

## Troubleshooting

### "FRED API key not found"
- Set `FRED_API_KEY` in `.env`
- Or set `USE_SEED_DATA=true` to use mock data

### "Database connection failed"
- Check `DATABASE_URL` in `.env`
- Ensure PostgreSQL is running
- Verify database exists

### "Rate limit exceeded"
- Wait for rate limit window to reset
- Check cache for recent data
- Reduce number of tickers in `config.json`

### "Import errors"
- Run `pip install -r requirements.txt`
- Check Python version (requires 3.11+)

## Development

### Adding a New Collector

1. Create `collectors/new_collector.py`
2. Inherit from `BaseCollector`
3. Implement rate limiting and caching
4. Add to `run_all.py`

Example:

```python
from collectors.base_collector import BaseCollector

class NewCollector(BaseCollector):
    def __init__(self):
        super().__init__(
            name="NewSource",
            rate_limiter=RateLimiter(max_requests=100, period_seconds=60)
        )

    def fetch_data(self):
        # Implementation
        pass
```

### Adding a New Calculator

1. Create `calculators/new_calculator.py`
2. Add calculation logic
3. Update `db.py` with upsert function
4. Add to Phase 2 in `run_all.py`

## Production Deployment

### Cron Schedule

Run daily at 6 AM UTC:

```bash
0 6 * * * cd /path/to/openfolio/etl && python run_all.py >> /var/log/openfolio-etl.log 2>&1
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY etl/ /app/
RUN pip install -r requirements.txt
CMD ["python", "run_all.py"]
```

### Monitoring

- Check logs for errors
- Monitor cache hit rates
- Track API quota usage
- Alert on failed runs

## Testing

```bash
# Run import validation
python test_imports.py

# Test individual components
python -c "from collectors.fred_collector import FREDCollector; c = FREDCollector(); print('OK')"

# Dry run (uses seed data)
USE_SEED_DATA=true python run_all.py
```

## License

MIT License - See root LICENSE file
