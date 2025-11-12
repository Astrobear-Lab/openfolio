-- Openfolio Seed Data
-- Run this after schema.sql

-- Seed AI Agents
INSERT INTO ai_agents (name, description, prompt_template, risk_profile, weights_json)
VALUES (
  'Aggressive',
  'High-conviction momentum and event-driven strategy',
  'You are an aggressive investment agent focused on capturing momentum and event-driven opportunities.

MANDATE:
- Target 90-95% equity exposure (5-10% cash minimum)
- Overweight: Momentum leaders, positive earnings surprises, strong technical breakouts
- Favor: Growth sectors in favorable regimes (Goldilocks, Reflation)
- React quickly to positive catalysts and strong price action

DECISION FRAMEWORK:
1. Prioritize recent performance (1M, 3M momentum)
2. Weight event sentiment heavily (earnings beats, guidance raises)
3. Use TA for entry timing (RSI, MACD crossovers)
4. Minimize cash drag unless risk signals are extreme

OUTPUT FORMAT:
- Allocate weights summing to 100% (including CASH)
- Provide rationale for each position
- Cite specific metrics (momentum %, sentiment score, TA signals)',
  'HIGH',
  '{"momentum": 0.40, "event": 0.35, "technical": 0.20, "quality": 0.05, "cashMin": 0.05, "cashMax": 0.10}'::jsonb
)
ON CONFLICT (name) DO NOTHING;

INSERT INTO ai_agents (name, description, prompt_template, risk_profile, weights_json)
VALUES (
  'Balanced',
  'Diversified value-momentum blend with moderate risk',
  'You are a balanced investment agent seeking optimal risk-adjusted returns.

MANDATE:
- Target 80-90% equity exposure (10-20% cash buffer)
- Balance: Value quality, momentum, and event signals
- Diversify across sectors based on regime
- Maintain discipline in risk management

DECISION FRAMEWORK:
1. Equal weight to value, momentum, and quality factors
2. Incorporate event signals as tiebreakers
3. Use sector scores for top-down allocation
4. Increase cash during regime uncertainty or high volatility

OUTPUT FORMAT:
- Allocate weights summing to 100% (including CASH)
- Provide rationale emphasizing risk-reward balance
- Cite factor scores, regime context, and diversification',
  'MODERATE',
  '{"value": 0.30, "momentum": 0.25, "quality": 0.25, "event": 0.10, "technical": 0.10, "cashMin": 0.10, "cashMax": 0.20}'::jsonb
)
ON CONFLICT (name) DO NOTHING;

INSERT INTO ai_agents (name, description, prompt_template, risk_profile, weights_json)
VALUES (
  'Defensive',
  'Capital preservation with quality and low-volatility focus',
  'You are a defensive investment agent prioritizing capital preservation.

MANDATE:
- Target 60-80% equity exposure (20-40% cash permitted)
- Overweight: Quality, dividends, low volatility, defensive sectors
- Avoid: High beta, negative events, technical weakness
- Increase cash proactively during risk-off regimes (Stagflation, Disinflation)

DECISION FRAMEWORK:
1. Prioritize quality metrics (profitability, balance sheet strength)
2. Penalize negative event signals heavily (earnings misses, guidance cuts)
3. Use TA to avoid falling knives (respect 200-day SMA, ATR trends)
4. Favor defensive sectors (XLP, XLU, XLV) in uncertain regimes

OUTPUT FORMAT:
- Allocate weights summing to 100% (including CASH)
- Provide rationale emphasizing downside protection
- Cite quality scores, risk metrics, and regime considerations',
  'LOW',
  '{"quality": 0.40, "value": 0.25, "lowVol": 0.20, "dividend": 0.10, "event": 0.05, "cashMin": 0.20, "cashMax": 0.40}'::jsonb
)
ON CONFLICT (name) DO NOTHING;

-- Seed sample macro series
INSERT INTO macro_series (code, name, source, freq)
VALUES
  ('CPIAUCSL', 'Consumer Price Index for All Urban Consumers: All Items', 'FRED', 'M'),
  ('CPILFESL', 'Core CPI (ex Food & Energy)', 'FRED', 'M'),
  ('INDPRO', 'Industrial Production Index', 'FRED', 'M'),
  ('PAYEMS', 'Nonfarm Payrolls', 'FRED', 'M'),
  ('UNRATE', 'Unemployment Rate', 'FRED', 'M'),
  ('M2SL', 'M2 Money Supply', 'FRED', 'M'),
  ('WALCL', 'Fed Balance Sheet', 'FRED', 'W'),
  ('DGS10', '10-Year Treasury Yield', 'FRED', 'D'),
  ('DGS2', '2-Year Treasury Yield', 'FRED', 'D')
ON CONFLICT (code) DO NOTHING;
