# Openfolio

**Transparent Investment Analysis Platform**

A comprehensive, educational investment research tool combining top-down macro analysis, sector rotation, event-driven insights, and multi-AI portfolio strategies with full data transparency.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Next.js](https://img.shields.io/badge/Next.js-15-black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-green)

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

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and npm 9+
- **Supabase account** (free tier)
- **Python** 3.11+ (for ETL)

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/openfolio.git
cd openfolio

# Install dependencies
npm install
```

### 2. Set up Supabase

1. Create free account at [supabase.com](https://supabase.com)
2. Create new project
3. Go to **SQL Editor** and run:
   - `supabase/schema.sql` (creates tables)
   - `supabase/seed.sql` (seeds AI agents)

### 3. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Supabase credentials:
NEXT_PUBLIC_SUPABASE_URL="https://your-project.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="your-anon-key"
```

Get these values from: **Supabase Dashboard → Settings → API**

### 4. Run ETL Pipeline

```bash
# Install Python dependencies
cd etl
pip install -r requirements.txt

# Copy ETL env and add Supabase URL
cp .env.example .env
# Edit etl/.env and add SUPABASE_URL and SUPABASE_KEY

# Run ETL (uses seed data by default)
python run_all.py
cd ..
```

### 5. Start Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the app.

---

## 📊 Database Schema

All tables are created via SQL in `supabase/schema.sql`:

**Core Tables:**
- `macro_series`, `macro_points` - Raw economic data
- `macro_features_daily`, `macro_regime_daily` - Normalized features & regime
- `prices_daily` - EOD prices (11 sector ETFs + stocks)
- `sector_scores` - Sector rotation scores
- `event_docs`, `event_nlp` - Events with NLP analysis
- `ta_daily` - Technical indicators
- `screening_steps`, `rankings` - Stock screening
- `ai_agents`, `ai_weights_history`, `ai_performance`, `decision_logs` - Multi-AI system

---

## 🔧 API Reference

All API endpoints return JSON with `timestamp`, `source`, and `version`.

| Endpoint | Description |
|----------|-------------|
| `/api/regime?date=latest` | Regime classification |
| `/api/sectors/scores?date=latest` | Sector scores |
| `/api/ai/compare/weights?date=latest` | Compare all AI weights |
| `/api/events/nlp?ticker=AAPL&range=30d` | NLP event analysis |

---

## 📁 Project Structure

```
openfolio/
├── app/
│   ├── macro/              # Macro Lab page
│   ├── sectors/            # Sector Board
│   ├── screener/           # Screener
│   ├── events/             # Events Studio
│   ├── ai-compare/         # AI Compare
│   └── api/                # API routes
├── supabase/
│   ├── schema.sql          # Database schema
│   └── seed.sql            # Seed data (AI agents)
├── etl/                    # Python ETL pipeline
│   ├── run_all.py         # Main runner
│   └── seed_data.py       # Seed generator
├── components/             # React components
└── lib/
    └── supabase.ts        # Supabase client
```

---

## 🚢 Deployment

### Vercel (Frontend)

```bash
vercel

# Add environment variables in Vercel dashboard:
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
```

### GitHub Actions (ETL)

See `.github/workflows/etl-cron.yml` for automated daily ETL.

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgments

- Federal Reserve Economic Data (FRED)
- Supabase
- Next.js, React, Tailwind CSS

**Remember**: This is a learning tool. Always do your own research!
