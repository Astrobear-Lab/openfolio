# Deployment Guide

Complete guide for deploying Openfolio to production.

## Architecture Overview

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Vercel    │─────▶│  Supabase    │◀─────│   GitHub    │
│  (Frontend) │      │ (PostgreSQL) │      │   Actions   │
│   Next.js   │      │   Database   │      │  (ETL Cron) │
└─────────────┘      └──────────────┘      └─────────────┘
```

---

## Part 1: Database Setup (Supabase)

### Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click "New Project"
3. Configure:
   - **Name**: openfolio
   - **Database Password**: (generate strong password)
   - **Region**: Choose closest to your users
   - **Plan**: Free tier is sufficient for testing

### Step 2: Get Connection String

1. In Supabase dashboard, go to **Settings** → **Database**
2. Copy the **Connection String** (Pooler mode recommended for serverless)
3. Replace `[YOUR-PASSWORD]` with your database password

Example:
```
postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-us-west-1.pooler.supabase.com:6543/postgres
```

### Step 3: Run Migrations

```bash
# Set DATABASE_URL in .env
echo 'DATABASE_URL="postgresql://postgres.xxx..."' > .env

# Generate Prisma client
npm run prisma:generate

# Deploy migrations
npx prisma migrate deploy

# Seed AI agents
npx prisma db seed
```

### Step 4: Verify Schema

```bash
# Open Prisma Studio
npm run prisma:studio
```

Check that all tables exist:
- macro_series, macro_points
- macro_features_daily, macro_regime_daily
- prices_daily
- sector_scores
- event_docs, event_nlp
- ta_daily
- screening_steps, rankings
- ai_agents (should have 3 rows), ai_weights_history, ai_performance
- decision_logs

---

## Part 2: Frontend Deployment (Vercel)

### Step 1: Push to GitHub

```bash
# Initialize git (if not already)
git init
git add .
git commit -m "Initial commit"

# Create GitHub repo and push
git remote add origin https://github.com/yourusername/openfolio.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy to Vercel

#### Option A: Vercel Dashboard

1. Go to [vercel.com](https://vercel.com) and sign in
2. Click "Add New..." → "Project"
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `./`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`

5. Add environment variable:
   - **Key**: `DATABASE_URL`
   - **Value**: Your Supabase connection string
   - **Environment**: Production, Preview, Development

6. Click "Deploy"

#### Option B: Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel

# Add environment variable
vercel env add DATABASE_URL production
# Paste your DATABASE_URL when prompted

# Deploy to production
vercel --prod
```

### Step 3: Verify Deployment

1. Visit your Vercel URL (e.g., `openfolio.vercel.app`)
2. Check all 5 pages load:
   - Home: `/`
   - Macro Lab: `/macro`
   - Sector Board: `/sectors`
   - Screener: `/screener`
   - Events Studio: `/events`
   - AI Compare: `/ai-compare`

3. Test API endpoint:
   ```bash
   curl https://openfolio.vercel.app/api/regime?date=latest
   ```

---

## Part 3: ETL Automation (GitHub Actions)

### Step 1: Configure Secrets

In your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click "New repository secret" for each:

| Secret Name | Value | Required |
|-------------|-------|----------|
| `DATABASE_URL` | Supabase connection string | ✅ Yes |
| `FRED_API_KEY` | FRED API key ([get here](https://fred.stlouisfed.org/docs/api/api_key.html)) | ⚠️ Optional* |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage key ([get here](https://www.alphavantage.co/support/#api-key)) | ⚠️ Optional* |
| `FMP_API_KEY` | FMP key ([get here](https://site.financialmodelingprep.com/developer/docs)) | ⚠️ Optional* |
| `OPENAI_API_KEY` | OpenAI key (for NLP) | ⚠️ Optional* |
| `USE_SEED_DATA` | `"true"` or `"false"` | Default: `"true"` |

*If not provided, ETL will use seed data (synthetic mock data).

### Step 2: Enable Workflow

The workflow file is already created at `.github/workflows/etl-cron.yml`.

It runs:
- **Daily** at 2 AM UTC (after U.S. market close)
- **Manually** via GitHub Actions UI

### Step 3: Test Manual Run

1. Go to **Actions** tab in GitHub
2. Select "Daily ETL Pipeline"
3. Click "Run workflow"
4. Monitor the job logs

### Step 4: Verify Data

After ETL runs:

```bash
# Check latest regime
curl https://openfolio.vercel.app/api/regime?date=latest

# Check sector scores
curl https://openfolio.vercel.app/api/sectors/scores?date=latest

# Check AI weights
curl https://openfolio.vercel.app/api/ai/compare/weights?date=latest
```

---

## Part 4: Custom Domain (Optional)

### Vercel Domain Setup

1. In Vercel dashboard, go to your project
2. **Settings** → **Domains**
3. Add your custom domain (e.g., `openfolio.com`)
4. Follow DNS configuration instructions

Vercel automatically provisions SSL certificates via Let's Encrypt.

---

## Part 5: Monitoring & Maintenance

### Application Monitoring

**Vercel Analytics** (included):
- Go to Vercel dashboard → **Analytics**
- Monitor page views, Web Vitals, errors

**Vercel Logs**:
- **Deployments** tab → Click deployment → **Logs**
- Real-time function logs for API routes

### Database Monitoring

**Supabase Dashboard**:
- **Database** → **Database Health** → Check CPU, memory, connections
- **SQL Editor** → Run queries to inspect data

Example queries:
```sql
-- Check latest ETL run
SELECT date, regime FROM macro_regime_daily ORDER BY date DESC LIMIT 10;

-- Check AI agent allocations
SELECT * FROM ai_weights_history
WHERE date = (SELECT MAX(date) FROM ai_weights_history);

-- Check event count
SELECT COUNT(*) FROM event_docs;
```

### ETL Monitoring

**GitHub Actions**:
- Go to **Actions** tab
- Monitor daily ETL job status
- Review logs for errors

**Set up notifications**:
Edit `.github/workflows/etl-cron.yml` to add Slack/email alerts on failure.

---

## Part 6: Rate Limits & Costs

### Free Tier Limits

**Vercel**:
- 100 GB bandwidth/month
- Unlimited requests
- 100 hours serverless function execution
- ✅ **Sufficient for moderate traffic**

**Supabase**:
- 500 MB database storage
- 1 GB file storage
- 2 GB bandwidth
- ⚠️ **May need upgrade if storing 2+ years of daily prices**

**API Keys** (if using real data):
- **FRED**: 120 requests/day (free)
- **Alpha Vantage**: 25 requests/day (free)
- **FMP**: 250 requests/day (free)

**Recommendation**: Use seed data for development, real APIs for production.

---

## Part 7: Troubleshooting

### Issue: Frontend can't connect to database

**Symptom**: API routes return 500 errors

**Solution**:
1. Check `DATABASE_URL` is set in Vercel environment variables
2. Verify connection string includes password
3. Use **Pooler** connection string for serverless (Supabase)
4. Test connection:
   ```bash
   npx prisma db execute --stdin <<< "SELECT 1;"
   ```

### Issue: ETL job fails

**Symptom**: GitHub Actions shows red X

**Solution**:
1. Check job logs in Actions tab
2. Verify all secrets are set correctly
3. Test locally:
   ```bash
   cd etl
   python run_all.py
   ```
4. Check database permissions

### Issue: Pages show "No data available"

**Symptom**: UI renders but shows empty state

**Solution**:
1. Check if ETL has run:
   ```bash
   curl https://openfolio.vercel.app/api/regime?date=latest
   ```
2. If API returns 404, run ETL manually
3. Check database has data (Prisma Studio or Supabase SQL Editor)

### Issue: Build fails on Vercel

**Symptom**: Deployment shows build errors

**Solution**:
1. Check build logs in Vercel dashboard
2. Common issues:
   - TypeScript errors → Run `npm run type-check` locally
   - Missing dependencies → Check `package.json`
   - Prisma client not generated → Add to build command:
     ```
     npx prisma generate && next build
     ```

---

## Part 8: Security Checklist

- ✅ Database password is strong (20+ chars, random)
- ✅ `DATABASE_URL` is in environment variables, not committed to git
- ✅ API keys stored in GitHub Secrets
- ✅ Supabase RLS (Row Level Security) disabled for now (app uses service role)
- ✅ Vercel environment variables set to "Production" only (not public)
- ⚠️ **Do not expose** API keys in client-side code
- ⚠️ **Rate limit** API routes if publicly accessible (consider Vercel Edge Middleware)

---

## Part 9: Scaling Considerations

### When to Upgrade

**Database**:
- Upgrade Supabase plan if:
  - Database > 500 MB
  - Need more than 2 concurrent connections
  - Require point-in-time recovery

**Hosting**:
- Upgrade Vercel plan if:
  - Bandwidth > 100 GB/month
  - Need team collaboration features
  - Require priority support

### Performance Optimization

1. **Add database indexes** (already included in schema):
   ```sql
   CREATE INDEX IF NOT EXISTS idx_prices_ticker ON prices_daily(ticker);
   CREATE INDEX IF NOT EXISTS idx_prices_date ON prices_daily(date);
   ```

2. **Enable Vercel Edge Caching**:
   - Add cache headers to API routes:
     ```typescript
     return new Response(json, {
       headers: {
         'Cache-Control': 's-maxage=3600, stale-while-revalidate',
       },
     });
     ```

3. **Optimize ETL**:
   - Only fetch new data (check last update timestamp)
   - Use bulk inserts (already implemented in `db.py`)
   - Add retry logic with exponential backoff

---

## Part 10: Next Steps

After deployment:

1. **Monitor for 1 week** - Check daily ETL runs and API health
2. **Add real API keys** (optional) - Replace seed data with live data
3. **Customize AI agents** - Adjust prompts and weights in database
4. **Add more stocks** - Expand `sample_stocks` in `etl/config.json`
5. **Implement backfill** - Run ETL for historical dates:
   ```python
   # In etl/run_all.py, add date parameter
   for date in date_range(start='2022-01-01', end='2024-11-08'):
       run_etl_for_date(date)
   ```

6. **Set up alerts** - Integrate with PagerDuty, Slack, or email
7. **Add unit tests** - Use Jest for frontend, pytest for ETL

---

## Support

For issues or questions:
- Open a GitHub issue
- Check logs: Vercel dashboard, GitHub Actions, Supabase SQL Editor
- Review [Next.js docs](https://nextjs.org/docs), [Prisma docs](https://www.prisma.io/docs)

**Happy deploying! 🚀**
