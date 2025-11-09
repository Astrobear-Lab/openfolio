-- CreateTable
CREATE TABLE "macro_series" (
    "id" BIGSERIAL NOT NULL,
    "code" TEXT NOT NULL,
    "name" TEXT,
    "source" TEXT,
    "freq" TEXT,

    CONSTRAINT "macro_series_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "macro_points" (
    "series_id" BIGINT NOT NULL,
    "ts" DATE NOT NULL,
    "value" DECIMAL,
    "revision_of" DATE,
    "raw_json" JSONB,
    "url" TEXT,

    CONSTRAINT "macro_points_pkey" PRIMARY KEY ("series_id","ts","revision_of")
);

-- CreateTable
CREATE TABLE "macro_features_daily" (
    "date" DATE NOT NULL,
    "feature" TEXT NOT NULL,
    "value" DECIMAL,
    "details_json" JSONB,

    CONSTRAINT "macro_features_daily_pkey" PRIMARY KEY ("date","feature")
);

-- CreateTable
CREATE TABLE "macro_regime_daily" (
    "date" DATE NOT NULL,
    "growth_z" DECIMAL,
    "inflation_z" DECIMAL,
    "liquidity_z" DECIMAL,
    "rates_z" DECIMAL,
    "regime" TEXT,
    "details_json" JSONB,

    CONSTRAINT "macro_regime_daily_pkey" PRIMARY KEY ("date")
);

-- CreateTable
CREATE TABLE "prices_daily" (
    "ticker" TEXT NOT NULL,
    "date" DATE NOT NULL,
    "open" DECIMAL,
    "high" DECIMAL,
    "low" DECIMAL,
    "close" DECIMAL,
    "adj_close" DECIMAL,
    "volume" BIGINT,
    "source" TEXT,
    "raw_json" JSONB,

    CONSTRAINT "prices_daily_pkey" PRIMARY KEY ("ticker","date")
);

-- CreateTable
CREATE TABLE "sector_scores" (
    "date" DATE NOT NULL,
    "sector" TEXT NOT NULL,
    "score" DECIMAL,
    "components_json" JSONB,

    CONSTRAINT "sector_scores_pkey" PRIMARY KEY ("date","sector")
);

-- CreateTable
CREATE TABLE "event_docs" (
    "id" BIGSERIAL NOT NULL,
    "ticker" TEXT,
    "dt" TIMESTAMPTZ,
    "type" TEXT,
    "url" TEXT,
    "title" TEXT,
    "body" TEXT,

    CONSTRAINT "event_docs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "event_nlp" (
    "doc_id" BIGINT NOT NULL,
    "sentiment" REAL,
    "guidance" TEXT,
    "surprise_eps" REAL,
    "topics" TEXT[],
    "quotes" JSONB,
    "model" TEXT,
    "version" TEXT,

    CONSTRAINT "event_nlp_pkey" PRIMARY KEY ("doc_id")
);

-- CreateTable
CREATE TABLE "ta_daily" (
    "ticker" TEXT NOT NULL,
    "date" DATE NOT NULL,
    "rsi14" DECIMAL,
    "macd" DECIMAL,
    "macd_signal" DECIMAL,
    "sma20" DECIMAL,
    "sma50" DECIMAL,
    "sma200" DECIMAL,
    "atr14" DECIMAL,
    "flags" JSONB,

    CONSTRAINT "ta_daily_pkey" PRIMARY KEY ("ticker","date")
);

-- CreateTable
CREATE TABLE "screening_steps" (
    "date" DATE NOT NULL,
    "ticker" TEXT NOT NULL,
    "step" TEXT NOT NULL,
    "pass" BOOLEAN,
    "score" DECIMAL,
    "evidence_json" JSONB,

    CONSTRAINT "screening_steps_pkey" PRIMARY KEY ("date","ticker","step")
);

-- CreateTable
CREATE TABLE "rankings" (
    "date" DATE NOT NULL,
    "ticker" TEXT NOT NULL,
    "total_score" DECIMAL,
    "components_json" JSONB,
    "decision" TEXT,
    "version" TEXT,

    CONSTRAINT "rankings_pkey" PRIMARY KEY ("date","ticker")
);

-- CreateTable
CREATE TABLE "ai_agents" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "prompt_template" TEXT,
    "risk_profile" TEXT,
    "weights_json" JSONB,

    CONSTRAINT "ai_agents_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ai_weights_history" (
    "date" DATE NOT NULL,
    "agent_id" INTEGER NOT NULL,
    "ticker" TEXT NOT NULL,
    "weight" DECIMAL,
    "reason_json" JSONB,

    CONSTRAINT "ai_weights_history_pkey" PRIMARY KEY ("date","agent_id","ticker")
);

-- CreateTable
CREATE TABLE "ai_performance" (
    "date" DATE NOT NULL,
    "agent_id" INTEGER NOT NULL,
    "nav" DECIMAL,
    "cash_weight" DECIMAL,
    "pnl_daily" DECIMAL,
    "sharpe" DECIMAL,
    "mdd" DECIMAL,
    "benchmark_return" DECIMAL,

    CONSTRAINT "ai_performance_pkey" PRIMARY KEY ("date","agent_id")
);

-- CreateTable
CREATE TABLE "decision_logs" (
    "date" DATE NOT NULL,
    "stage" TEXT NOT NULL,
    "agent" TEXT NOT NULL,
    "input_ref" JSONB,
    "computed_ref" JSONB,
    "decision" JSONB,
    "rationale_md" TEXT,

    CONSTRAINT "decision_logs_pkey" PRIMARY KEY ("date","stage","agent")
);

-- CreateIndex
CREATE UNIQUE INDEX "macro_series_code_key" ON "macro_series"("code");

-- CreateIndex
CREATE INDEX "prices_daily_ticker_idx" ON "prices_daily"("ticker");

-- CreateIndex
CREATE INDEX "prices_daily_date_idx" ON "prices_daily"("date");

-- CreateIndex
CREATE INDEX "sector_scores_date_idx" ON "sector_scores"("date");

-- CreateIndex
CREATE INDEX "event_docs_ticker_idx" ON "event_docs"("ticker");

-- CreateIndex
CREATE INDEX "event_docs_dt_idx" ON "event_docs"("dt");

-- CreateIndex
CREATE INDEX "ta_daily_ticker_idx" ON "ta_daily"("ticker");

-- CreateIndex
CREATE INDEX "ta_daily_date_idx" ON "ta_daily"("date");

-- CreateIndex
CREATE INDEX "screening_steps_date_idx" ON "screening_steps"("date");

-- CreateIndex
CREATE INDEX "screening_steps_ticker_idx" ON "screening_steps"("ticker");

-- CreateIndex
CREATE INDEX "rankings_date_idx" ON "rankings"("date");

-- CreateIndex
CREATE UNIQUE INDEX "ai_agents_name_key" ON "ai_agents"("name");

-- CreateIndex
CREATE INDEX "ai_weights_history_date_idx" ON "ai_weights_history"("date");

-- CreateIndex
CREATE INDEX "ai_weights_history_agent_id_idx" ON "ai_weights_history"("agent_id");

-- CreateIndex
CREATE INDEX "ai_performance_date_idx" ON "ai_performance"("date");

-- CreateIndex
CREATE INDEX "ai_performance_agent_id_idx" ON "ai_performance"("agent_id");

-- CreateIndex
CREATE INDEX "decision_logs_date_idx" ON "decision_logs"("date");

-- AddForeignKey
ALTER TABLE "macro_points" ADD CONSTRAINT "macro_points_series_id_fkey" FOREIGN KEY ("series_id") REFERENCES "macro_series"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "event_nlp" ADD CONSTRAINT "event_nlp_doc_id_fkey" FOREIGN KEY ("doc_id") REFERENCES "event_docs"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ai_weights_history" ADD CONSTRAINT "ai_weights_history_agent_id_fkey" FOREIGN KEY ("agent_id") REFERENCES "ai_agents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ai_performance" ADD CONSTRAINT "ai_performance_agent_id_fkey" FOREIGN KEY ("agent_id") REFERENCES "ai_agents"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
