# Quick Start Guide

Get Openfolio running in 5 minutes!

## Prerequisites

- Node.js 18+
- PostgreSQL 14+ OR Supabase account (free tier works)
- Python 3.11+ (for ETL)

## Step 1: Clone and Install

```bash
# Clone the repository
git clone <your-repo-url>
cd openfolio

# Install Node dependencies
npm install

# Install Python dependencies
cd etl
pip install -r requirements.txt
cd ..
```

## Step 2: Database Setup

### Option A: Supabase (Recommended)

1. Create free account at [supabase.com](https://supabase.com)
2. Create new project
3. Copy connection string from Settings → Database
4. Create `.env`:

```bash
echo 'DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"' > .env
```

### Option B: Local PostgreSQL

```bash
# Create database
createdb openfolio

# Create .env
echo 'DATABASE_URL="postgresql://user:password@localhost:5432/openfolio"' > .env
```

## Step 3: Initialize Database

```bash
# Generate Prisma client
npm run prisma:generate

# Run migrations
npx prisma migrate deploy

# Seed AI agents
npm run prisma:seed
```

## Step 4: Run ETL (Load Sample Data)

```bash
# Copy ETL env
cp etl/.env.example etl/.env

# Edit etl/.env and set DATABASE_URL (same as above)
# Leave USE_SEED_DATA="true" for testing

# Run ETL pipeline
cd etl
python run_all.py
cd ..
```

Expected output:
```
=== Step 1: Macro Data ETL ===
Processing series: CPIAUCSL
  Stored 1095 points for CPIAUCSL
...
ETL Pipeline Completed Successfully
```

## Step 5: Start Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Verify Installation

You should see:
- ✅ Home page with 5 feature cards
- ✅ Macro Lab showing Goldilocks regime
- ✅ Sector Board with ranked sectors
- ✅ Screener with stock scores
- ✅ Events Studio with sample events
- ✅ AI Compare with 3 agents

## Test API

```bash
# Check regime
curl http://localhost:3000/api/regime?date=latest

# Check AI weights
curl http://localhost:3000/api/ai/compare/weights?date=latest
```

## Next Steps

- 📖 Read [README.md](README.md) for full documentation
- 🚀 See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- 🔧 Customize AI agents in database (use `npm run prisma:studio`)
- 📊 Add real API keys in `etl/.env` to fetch live data

## Troubleshooting

### "Cannot connect to database"

- Verify `DATABASE_URL` is correct
- Check database is running (PostgreSQL) or accessible (Supabase)
- Test connection: `npx prisma db execute --stdin <<< "SELECT 1;"`

### "No data in UI"

- Run ETL pipeline: `cd etl && python run_all.py`
- Check database has data: `npm run prisma:studio`

### "ETL fails with import errors"

- Install Python dependencies: `cd etl && pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.11+)

### "Module not found" in Next.js

- Reinstall dependencies: `rm -rf node_modules && npm install`
- Generate Prisma client: `npm run prisma:generate`

## Get Help

- 💬 Open an issue on GitHub
- 📚 Read the [full documentation](README.md)
- 🔍 Check [Deployment Guide](DEPLOYMENT.md)

Happy analyzing! 📈
