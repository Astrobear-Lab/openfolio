"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { KpiTile } from "@/components/ui/KpiTile";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export default function AIComparePage() {
  const [selectedAgent, setSelectedAgent] = useState<string>("Aggressive");

  // Mock AI agent data
  const agents = [
    {
      name: "Aggressive",
      riskProfile: "HIGH",
      nav: 1.324,
      return: 32.4,
      sharpe: 1.85,
      mdd: -18.2,
      cashWeight: 5.2,
      topHoldings: [
        { ticker: "AAPL", weight: 12.5 },
        { ticker: "MSFT", weight: 11.8 },
        { ticker: "NVDA", weight: 10.2 },
        { ticker: "TSLA", weight: 8.5 },
        { ticker: "CASH", weight: 5.2 },
      ],
      rationale: `**Decision Date:** 2024-11-08

**Macro Context:**
- Regime: Goldilocks (Growth +1.2, Inflation -0.5)
- Liquidity: Supportive (+0.8 z-score)
- → **Overweight equities, minimize cash**

**Sector Allocation:**
- XLK (Tech): 45% - Strongest momentum and regime tilt
- XLF (Financials): 25% - Benefiting from steeper yield curve
- XLY (Discretionary): 20% - Consumer resilience

**Stock Selection:**
- AAPL: Earnings beat (+2.5%), positive guidance, strong TA
- MSFT: Azure acceleration, AI tailwinds
- NVDA: Continued data center demand, pricing power
- TSLA: Speculative position on production recovery (high beta play)

**Risk Management:**
- Cash: 5.2% (minimum buffer)
- Stop-losses: None (momentum strategy)
- Rebalance trigger: Regime change or 3-day momentum reversal`,
    },
    {
      name: "Balanced",
      riskProfile: "MODERATE",
      nav: 1.185,
      return: 18.5,
      sharpe: 1.42,
      mdd: -12.8,
      cashWeight: 15.0,
      topHoldings: [
        { ticker: "AAPL", weight: 8.5 },
        { ticker: "MSFT", weight: 8.2 },
        { ticker: "JNJ", weight: 6.5 },
        { ticker: "PG", weight: 6.0 },
        { ticker: "CASH", weight: 15.0 },
      ],
      rationale: `**Decision Date:** 2024-11-08

**Portfolio Objective:**
Balanced risk-reward with diversification across factors and sectors.

**Factor Mix:**
- Value: 30% (PG, JNJ, moderate P/E names)
- Momentum: 25% (AAPL, MSFT)
- Quality: 25% (MSFT, JNJ - strong balance sheets)
- Event-driven: 10% (Recent earnings beats)
- Cash: 15% (volatility buffer)

**Sector Diversification:**
- Tech: 30%, Financials: 20%, Consumer Staples: 15%, Healthcare: 15%, Others: 5%

**Rationale:**
While Goldilocks regime favors growth, maintain balanced exposure for downside protection. Cash buffer allows opportunistic rebalancing.`,
    },
    {
      name: "Defensive",
      riskProfile: "LOW",
      nav: 1.095,
      return: 9.5,
      sharpe: 1.15,
      mdd: -7.2,
      cashWeight: 35.0,
      topHoldings: [
        { ticker: "JNJ", weight: 10.5 },
        { ticker: "PG", weight: 9.8 },
        { ticker: "KO", weight: 8.5 },
        { ticker: "XLU", weight: 7.2 },
        { ticker: "CASH", weight: 35.0 },
      ],
      rationale: `**Decision Date:** 2024-11-08

**Defensive Mandate:**
Capital preservation first. Avoid high-beta and event-driven volatility.

**Holdings Rationale:**
- JNJ, PG, KO: Quality dividend payers, low volatility
- XLU: Defensive sector, stable cash flows
- Cash: 35% - elevated due to late-cycle concerns

**Risk Considerations:**
- Avoid: Energy (XLE negative momentum), Discretionary (cyclical risk)
- Avoid: Stocks with negative event signals or technical breakdowns
- Focus: Above-average quality scores (>7/10)

**Current Stance:**
Despite Goldilocks regime, maintain high cash. Late-cycle signals (tight labor market, elevated valuations) warrant caution.`,
    },
  ];

  const selectedAgentData = agents.find((a) => a.name === selectedAgent)!;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">AI Portfolio Comparison</h1>
        <p className="text-text-subtle">
          Multi-agent strategies with transparent rationales and performance tracking
        </p>
      </div>

      {/* Agent Selector */}
      <div className="flex gap-3">
        {agents.map((agent) => (
          <Button
            key={agent.name}
            variant={selectedAgent === agent.name ? "primary" : "outline"}
            onClick={() => setSelectedAgent(agent.name)}
          >
            {agent.name}
            <Badge
              variant={
                agent.riskProfile === "HIGH"
                  ? "danger"
                  : agent.riskProfile === "LOW"
                  ? "positive"
                  : "warning"
              }
              className="ml-2"
            >
              {agent.riskProfile}
            </Badge>
          </Button>
        ))}
      </div>

      {/* Performance KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <KpiTile
          label="NAV"
          value={selectedAgentData.nav.toFixed(3)}
          positive={selectedAgentData.nav > 1}
        />
        <KpiTile
          label="Total Return"
          value={`${selectedAgentData.return > 0 ? "+" : ""}${selectedAgentData.return}%`}
          delta={`vs SPY +15%`}
          positive={selectedAgentData.return > 15}
        />
        <KpiTile
          label="Sharpe Ratio"
          value={selectedAgentData.sharpe.toFixed(2)}
        />
        <KpiTile
          label="Max Drawdown"
          value={`${selectedAgentData.mdd}%`}
        />
        <KpiTile
          label="Cash Weight"
          value={`${selectedAgentData.cashWeight}%`}
        />
      </div>

      {/* Holdings */}
      <Card
        title="Current Holdings"
        subtitle={`${selectedAgent} agent allocation`}
        updatedAt="EOD 2024-11-08"
      >
        <div className="space-y-4">
          {/* Holdings Table */}
          <table className="data-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th className="numeric">Weight %</th>
                <th className="numeric">Allocation</th>
              </tr>
            </thead>
            <tbody>
              {selectedAgentData.topHoldings.map((holding) => (
                <tr key={holding.ticker}>
                  <td
                    className={`font-mono font-semibold ${
                      holding.ticker === "CASH" ? "text-text-subtle" : ""
                    }`}
                  >
                    {holding.ticker}
                  </td>
                  <td className="numeric font-mono">{holding.weight}%</td>
                  <td className="numeric">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-32 h-2 bg-background rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            holding.ticker === "CASH"
                              ? "bg-text-subtle"
                              : "bg-primary"
                          }`}
                          style={{ width: `${holding.weight * 4}%` }}
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Performance Comparison */}
      <Card
        title="Performance Comparison"
        subtitle="All agents vs SPY benchmark (2Y)"
      >
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>Risk Profile</th>
                <th className="numeric">Return</th>
                <th className="numeric">Sharpe</th>
                <th className="numeric">Max DD</th>
                <th className="numeric">Cash %</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.name}>
                  <td className="font-semibold">{agent.name}</td>
                  <td>
                    <Badge
                      variant={
                        agent.riskProfile === "HIGH"
                          ? "danger"
                          : agent.riskProfile === "LOW"
                          ? "positive"
                          : "warning"
                      }
                    >
                      {agent.riskProfile}
                    </Badge>
                  </td>
                  <td
                    className={`numeric font-mono ${
                      agent.return > 15 ? "text-positive" : "text-text"
                    }`}
                  >
                    {agent.return > 0 ? "+" : ""}
                    {agent.return}%
                  </td>
                  <td className="numeric font-mono">{agent.sharpe.toFixed(2)}</td>
                  <td className="numeric font-mono text-danger">
                    {agent.mdd}%
                  </td>
                  <td className="numeric font-mono">{agent.cashWeight}%</td>
                </tr>
              ))}
              <tr className="border-t-2 border-border">
                <td className="font-semibold">SPY (Benchmark)</td>
                <td>
                  <Badge variant="default">MARKET</Badge>
                </td>
                <td className="numeric font-mono">+15.0%</td>
                <td className="numeric font-mono">1.10</td>
                <td className="numeric font-mono text-danger">-15.5%</td>
                <td className="numeric font-mono">0.0%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      {/* Rationale */}
      <Card title="Decision Rationale" subtitle={`${selectedAgent} agent logic`}>
        <div className="prose prose-invert prose-sm max-w-none">
          <pre className="whitespace-pre-wrap text-sm leading-relaxed">
            {selectedAgentData.rationale}
          </pre>
        </div>
      </Card>
    </div>
  );
}
