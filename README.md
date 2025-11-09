# Openfolio

**Transparent Investment Analysis Platform**

A comprehensive, educational investment research tool combining top-down macro analysis, sector rotation, event-driven insights, and multi-AI portfolio strategies with full data transparency.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue)
![Python](https://img.shields.io/badge/Python-3.11-green)

## ⚠️ Disclaimer

**Openfolio is an educational research tool only. This is NOT investment advice.**

- Data may be delayed, incomplete, or inaccurate
- Past performance does not guarantee future results
- Always consult a licensed financial advisor before making investment decisions
- Use at your own risk

---

## 🎯 Features

### Core Capabilities

1. **Macro Lab** - Economic regime classification (Goldilocks, Reflation, Stagflation, Disinflation)
   - Raw data from FRED/BLS with full lineage
   - 36-month rolling z-score normalization
   - Transparent calculation methodology

2. **Sector Board** - Top-down sector rotation signals
   - Momentum, volatility, and regime-based scoring
   - Evidence panels with formula breakdowns
   - All components traceable to source data

3. **Screener** - Multi-stage stock screening
   - Quality, Value, Event, and Technical factors
   - Pass/fail gates with score breakdowns
   - Full evidence trail for each decision

4. **Events Studio** - SEC filings and earnings analysis
   - NLP sentiment extraction (FinBERT-based)
   - Guidance classification and EPS surprise tracking
   - Key quote extraction with citations

5. **AI Compare** - Multi-agent portfolio strategies
   - **Aggressive**: High momentum, 5-10% cash
   - **Balanced**: Diversified factors, 10-20% cash
   - **Defensive**: Quality focus, 20-40% cash
   - Performance tracking vs SPY benchmark
   - Decision rationale logs for every allocation

### Transparency Principles

- ✅ All raw data sources linked and versioned
- ✅ Z-score methodology with 36M rolling windows
- ✅ Evidence drawers show inputs, calculations, citations
- ✅ AI rationales logged with timestamps
- ✅ Daily ETL with seed data for offline testing

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and npm 9+
- **PostgreSQL** 14+ (or Supabase account)
- **Python** 3.11+ (for ETL)

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/openfolio.git
cd openfolio

# Install Node dependencies
npm install

# Install Python dependencies
cd etl
pip install -r requirements.txt
cd ..
```

### 2. Environment Setup

```bash
# Copy environment templates
cp .env.example .env
cp etl/.env.example etl/.env

# Edit .env with your database URL
# For local PostgreSQL:
DATABASE_URL="postgresql://user:password@localhost:5432/openfolio"

# For Supabase:
DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
```

### 3. Database Setup

```bash
# Generate Prisma client
npm run prisma:generate

# Run migrations
npm run prisma:migrate

# Seed AI agents and sample data
npm run prisma:seed
```

### 4. Run ETL Pipeline

```bash
# Run full ETL (uses seed data by default)
cd etl
python run_all.py
cd ..
```

**Note**: By default, ETL uses synthetic seed data. To use real APIs, set `USE_SEED_DATA="false"` in `etl/.env` and provide API keys.

### 5. Start Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the app.

---

## 📊 Data Sources

### Macroeconomic Data (FRED)

| Series Code | Description | Frequency | Category |
|-------------|-------------|-----------|----------|
| `CPIAUCSL` | Consumer Price Index | Monthly | Inflation |
| `CPILFESL` | Core CPI (ex Food & Energy) | Monthly | Inflation |
| `INDPRO` | Industrial Production | Monthly | Growth |
| `PAYEMS` | Nonfarm Payrolls | Monthly | Growth |
| `UNRATE` | Unemployment Rate | Monthly | Growth |
| `M2SL` | M2 Money Supply | Monthly | Liquidity |
| `WALCL` | Fed Balance Sheet | Weekly | Liquidity |
| `DGS10` | 10-Year Treasury Yield | Daily | Rates |
| `DGS2` | 2-Year Treasury Yield | Daily | Rates |

### Price Data

- **Source**: Yahoo Finance (yfinance) or Alpha Vantage
- **Coverage**: 11 sector ETFs (XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLK, XLU, XLRE, XLC) + sample stocks
- **Frequency**: Daily (EOD)

### Events Data

- **Source**: SEC EDGAR (8-K, 10-Q, 10-K filings), IR feeds
- **NLP**: FinBERT for sentiment + LLM for summarization (mock in seed mode)

---

## 🔧 API Reference

All API endpoints return JSON with:
```json
{
  "data": { ... },
  "timestamp": "2024-11-08T12:00:00Z",
  "source": "FRED | Computed | etc.",
  "version": "1.0.0"
}
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/raw/macro?series=CPIAUCSL&from=2023-01-01` | Raw macro time series |
| GET | `/api/macro/features?date=latest` | Normalized features (z-scores) |
| GET | `/api/regime?date=latest` | Regime classification |
| GET | `/api/sectors/scores?date=latest` | Sector scores |
| GET | `/api/events?ticker=AAPL&range=30d` | Event documents |
| GET | `/api/events/nlp?ticker=AAPL&range=30d` | NLP analysis |
| GET | `/api/ta?ticker=AAPL&range=1y` | Technical indicators |
| GET | `/api/ai/:agent/weights?range=2y` | AI agent weights history |
| GET | `/api/ai/compare/weights?date=latest` | Compare all AI weights |
| GET | `/api/ai/:agent/perf?range=2y` | AI performance metrics |
| GET | `/api/decision/logs?date=2024-11-08&stage=allocation` | Decision logs |

---

## 📁 Project Structure

```
openfolio/
├── app/                      # Next.js App Router pages
│   ├── api/                  # API routes (11 endpoints)
│   ├── macro/                # Macro Lab page
│   ├── sectors/              # Sector Board page
│   ├── screener/             # Screener page
│   ├── events/               # Events Studio page
│   ├── ai-compare/           # AI Compare page
│   ├── layout.tsx            # Root layout
│   ├── page.tsx              # Home page
│   └── globals.css           # Global styles
├── components/               # React components
│   ├── ui/                   # UI primitives (Card, Badge, etc.)
│   ├── evidence/             # Evidence drawer
│   └── layout/               # Navigation
├── lib/                      # Utilities
│   ├── prisma.ts             # Prisma client
│   ├── utils.ts              # Helper functions
│   └── api-utils.ts          # API utilities
├── prisma/                   # Database
│   ├── schema.prisma         # Schema definition
│   └── seed.ts               # Seed script
├── etl/                      # Python ETL pipeline
│   ├── run_all.py            # Main ETL runner
│   ├── db.py                 # Database utilities
│   ├── seed_data.py          # Seed data generator
│   ├── config.json           # ETL configuration
│   └── requirements.txt      # Python dependencies
├── .github/                  # GitHub Actions
│   └── workflows/
│       └── etl-cron.yml      # Daily ETL cron job
├── package.json              # Node dependencies
├── tsconfig.json             # TypeScript config
├── tailwind.config.ts        # Tailwind config
├── next.config.js            # Next.js config
└── README.md                 # This file
```

---

## 🎨 Design System

### Color Palette

- **Primary**: `#2563EB` (Indigo 600)
- **Positive**: `#10B981` (Emerald 500)
- **Warning**: `#F59E0B` (Amber 500)
- **Danger**: `#EF4444` (Red 500)
- **Background**: `#0B0F1A` (Dark)
- **Surface**: `#121826`
- **Border**: `#1F2937`
- **Text**: `#E5E7EB`

### Typography

- **Headings**: Inter 700
- **Body**: Inter 400-500
- **Monospace**: IBM Plex Mono 500

### Accessibility

- WCAG 2.1 AA compliant (4.5:1 contrast ratio)
- Keyboard navigation support
- Screen reader labels
- Motion reduction support

---

## 🚢 Deployment

### Vercel (Frontend)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Add environment variable
vercel env add DATABASE_URL
```

### Supabase (Database)

1. Create project at [supabase.com](https://supabase.com)
2. Copy connection string
3. Run migrations:
   ```bash
   npx prisma migrate deploy
   npx prisma db seed
   ```

### GitHub Actions (ETL Cron)

See `.github/workflows/etl-cron.yml` for daily ETL automation.

---

## 🧪 Development

### Run Tests

```bash
npm run type-check     # TypeScript check
npm run lint           # ESLint
```

### Prisma Studio

```bash
npm run prisma:studio  # Open database GUI at localhost:5555
```

### ETL Development

```bash
cd etl
python run_all.py      # Run full pipeline
```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

This is an educational project. Contributions welcome via issues and pull requests.

**Key Guidelines**:
- Maintain data transparency principles
- Document all calculations and sources
- Add tests for new features
- Follow existing code style

---

## 📚 Resources

- [FRED API Documentation](https://fred.stlouisfed.org/docs/api/fred/)
- [SEC EDGAR](https://www.sec.gov/edgar.shtml)
- [Next.js Documentation](https://nextjs.org/docs)
- [Prisma Documentation](https://www.prisma.io/docs)

---

## 🙏 Acknowledgments

Data sources:
- Federal Reserve Economic Data (FRED)
- U.S. Securities and Exchange Commission (SEC)
- Yahoo Finance

Open-source projects:
- Next.js, React, Tailwind CSS
- Prisma, PostgreSQL
- Recharts, Lucide Icons

---

**Remember**: This is a learning tool. Always do your own research and consult professionals before making investment decisions.
