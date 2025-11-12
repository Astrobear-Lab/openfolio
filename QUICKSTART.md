# Quick Start Guide

Get Openfolio running in 5 minutes with Supabase!

## Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and create free account
2. Click **New Project**
3. Set project name: `openfolio`
4. Choose region and set database password
5. Wait for project to be ready (~2 minutes)

## Step 2: Run SQL Scripts

1. In Supabase dashboard, go to **SQL Editor**
2. Click **New Query**
3. Copy and paste contents of `supabase/schema.sql`
4. Click **Run**
5. Create another new query
6. Copy and paste contents of `supabase/seed.sql`
7. Click **Run**

You should see 3 AI agents inserted.

## Step 3: Get API Credentials

1. In Supabase dashboard, go to **Settings** → **API**
2. Copy:
   - **Project URL** (e.g., `https://abc123.supabase.co`)
   - **Anon/Public Key** (starts with `eyJ...`)

## Step 4: Install and Configure

```bash
# Clone and install
git clone <your-repo>
cd openfolio
npm install

# Create .env
cp .env.example .env

# Edit .env and add:
# NEXT_PUBLIC_SUPABASE_URL="https://your-project.supabase.co"
# NEXT_PUBLIC_SUPABASE_ANON_KEY="eyJ..."
```

## Step 5: Run ETL (Load Sample Data)

```bash
cd etl
pip install -r requirements.txt

# Copy ETL env
cp .env.example .env

# Edit etl/.env and add Supabase credentials
# (Use SERVICE ROLE key for ETL, find it in Settings → API)

# Run ETL
python run_all.py
```

Expected output:
```
=== Step 1: Macro Data ETL ===
Processing series: CPIAUCSL
...
ETL Pipeline Completed Successfully
```

## Step 6: Start App

```bash
cd ..
npm run dev
```

Open http://localhost:3000

## Verify

You should see:
- ✅ 5 pages working
- ✅ AI Compare showing 3 agents
- ✅ Macro Lab showing regime data
- ✅ Sectors with scores

## Troubleshooting

**"Missing Supabase environment variables"**
- Check `.env` file exists and has correct values
- Restart dev server after changing `.env`

**"No data in UI"**
- Run ETL: `cd etl && python run_all.py`
- Check Supabase dashboard → Table Editor for data

**ETL fails**
- Check `etl/.env` has correct Supabase SERVICE ROLE key (not anon key)
- Install Python deps: `pip install -r requirements.txt`

## Next Steps

- Read [README.md](README.md) for full docs
- Customize AI agents in Supabase Table Editor
- Add real API keys for live data

Done! 🎉
