"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EvidenceDrawer } from "@/components/evidence/EvidenceDrawer";
import { Check, X } from "lucide-react";

export default function ScreenerPage() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  // Mock screening data
  const screeningResults = [
    {
      ticker: "AAPL",
      name: "Apple Inc.",
      sector: "XLK",
      qualityPass: true,
      qualityScore: 8.5,
      valuePass: true,
      valueScore: 6.2,
      eventPass: true,
      eventScore: 7.8,
      taPass: true,
      taScore: 8.1,
      totalScore: 30.6,
      decision: "BUY",
    },
    {
      ticker: "MSFT",
      name: "Microsoft Corp.",
      sector: "XLK",
      qualityPass: true,
      qualityScore: 9.1,
      valuePass: true,
      valueScore: 5.8,
      eventPass: true,
      eventScore: 8.5,
      taPass: true,
      taScore: 7.9,
      totalScore: 31.3,
      decision: "BUY",
    },
    {
      ticker: "XOM",
      name: "Exxon Mobil Corp.",
      sector: "XLE",
      qualityPass: true,
      qualityScore: 7.2,
      valuePass: false,
      valueScore: 3.1,
      eventPass: false,
      eventScore: 2.5,
      taPass: false,
      taScore: 3.8,
      totalScore: 16.6,
      decision: "PASS",
    },
  ];

  const handleViewEvidence = (ticker: string) => {
    setSelectedTicker(ticker);
    setDrawerOpen(true);
  };

  const evidenceTabs = selectedTicker
    ? [
        {
          id: "quality",
          label: "Quality",
          content: (
            <div className="space-y-3 text-sm">
              <div>
                <strong>ROE (Return on Equity):</strong>
                <p className="text-text-subtle">45.2% → Z-score: +2.1 ✓</p>
              </div>
              <div>
                <strong>Gross Margin:</strong>
                <p className="text-text-subtle">43.1% → Z-score: +1.8 ✓</p>
              </div>
              <div>
                <strong>Debt/Equity:</strong>
                <p className="text-text-subtle">1.8 → Z-score: +0.5 ✓</p>
              </div>
              <div className="pt-2 border-t border-border">
                <strong>Quality Score:</strong>
                <p className="text-lg font-mono text-positive">8.5 / 10</p>
                <Badge variant="positive">PASS</Badge>
              </div>
            </div>
          ),
        },
        {
          id: "value",
          label: "Value",
          content: (
            <div className="space-y-3 text-sm">
              <div>
                <strong>P/E Ratio:</strong>
                <p className="text-text-subtle">28.5 → Z-score: -0.2</p>
              </div>
              <div>
                <strong>P/B Ratio:</strong>
                <p className="text-text-subtle">42.1 → Z-score: -1.1</p>
              </div>
              <div>
                <strong>EV/EBITDA:</strong>
                <p className="text-text-subtle">22.3 → Z-score: +0.3 ✓</p>
              </div>
              <div className="pt-2 border-t border-border">
                <strong>Value Score:</strong>
                <p className="text-lg font-mono">6.2 / 10</p>
                <Badge variant="positive">PASS (marginal)</Badge>
              </div>
            </div>
          ),
        },
        {
          id: "events",
          label: "Events & Sentiment",
          content: (
            <div className="space-y-3 text-sm">
              <div>
                <strong>Latest Earnings (Q3 2024):</strong>
                <p className="text-text-subtle">
                  EPS: $1.64 vs $1.60 est. → Beat by +2.5%
                </p>
              </div>
              <div>
                <strong>Guidance:</strong>
                <p className="text-text-subtle">
                  "Strong Services momentum expected to continue" → Positive
                </p>
              </div>
              <div>
                <strong>Sentiment Score:</strong>
                <p className="text-text-subtle">0.82 (FinBERT) → Very Positive</p>
              </div>
              <div className="pt-2 border-t border-border">
                <strong>Event Score:</strong>
                <p className="text-lg font-mono text-positive">7.8 / 10</p>
                <Badge variant="positive">PASS</Badge>
              </div>
            </div>
          ),
        },
        {
          id: "technical",
          label: "Technical",
          content: (
            <div className="space-y-3 text-sm">
              <div>
                <strong>RSI (14):</strong>
                <p className="text-text-subtle">62.3 → Neutral ✓</p>
              </div>
              <div>
                <strong>Price vs SMA200:</strong>
                <p className="text-text-subtle">+8.5% above → Uptrend ✓</p>
              </div>
              <div>
                <strong>MACD:</strong>
                <p className="text-text-subtle">
                  Bullish crossover 3 days ago → Positive ✓
                </p>
              </div>
              <div className="pt-2 border-t border-border">
                <strong>TA Score:</strong>
                <p className="text-lg font-mono text-positive">8.1 / 10</p>
                <Badge variant="positive">PASS</Badge>
              </div>
            </div>
          ),
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Screener</h1>
        <p className="text-text-subtle">
          Multi-stage stock screening with transparent scoring and evidence
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card title="Total Screened" className="p-3">
          <p className="text-2xl font-mono font-semibold">125</p>
        </Card>
        <Card title="Passed All Stages" className="p-3">
          <p className="text-2xl font-mono font-semibold text-positive">42</p>
        </Card>
        <Card title="Top Rated (>25)" className="p-3">
          <p className="text-2xl font-mono font-semibold text-primary">18</p>
        </Card>
        <Card title="Last Updated" className="p-3">
          <p className="text-sm font-mono">2024-11-08</p>
        </Card>
      </div>

      {/* Screening Results Table */}
      <Card
        title="Screening Results"
        subtitle="Ranked by total score (Quality 25% + Value 25% + Event 30% + TA 20%)"
      >
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Name</th>
                <th>Sector</th>
                <th className="numeric">Quality</th>
                <th className="numeric">Value</th>
                <th className="numeric">Event</th>
                <th className="numeric">TA</th>
                <th className="numeric">Total</th>
                <th>Decision</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {screeningResults.map((stock) => (
                <tr key={stock.ticker}>
                  <td className="font-mono font-semibold">{stock.ticker}</td>
                  <td>{stock.name}</td>
                  <td>
                    <Badge variant="default" className="font-mono">
                      {stock.sector}
                    </Badge>
                  </td>
                  <td className="numeric">
                    <div className="flex items-center justify-end gap-1">
                      <span className="font-mono">{stock.qualityScore}</span>
                      {stock.qualityPass ? (
                        <Check className="w-4 h-4 text-positive" />
                      ) : (
                        <X className="w-4 h-4 text-danger" />
                      )}
                    </div>
                  </td>
                  <td className="numeric">
                    <div className="flex items-center justify-end gap-1">
                      <span className="font-mono">{stock.valueScore}</span>
                      {stock.valuePass ? (
                        <Check className="w-4 h-4 text-positive" />
                      ) : (
                        <X className="w-4 h-4 text-danger" />
                      )}
                    </div>
                  </td>
                  <td className="numeric">
                    <div className="flex items-center justify-end gap-1">
                      <span className="font-mono">{stock.eventScore}</span>
                      {stock.eventPass ? (
                        <Check className="w-4 h-4 text-positive" />
                      ) : (
                        <X className="w-4 h-4 text-danger" />
                      )}
                    </div>
                  </td>
                  <td className="numeric">
                    <div className="flex items-center justify-end gap-1">
                      <span className="font-mono">{stock.taScore}</span>
                      {stock.taPass ? (
                        <Check className="w-4 h-4 text-positive" />
                      ) : (
                        <X className="w-4 h-4 text-danger" />
                      )}
                    </div>
                  </td>
                  <td
                    className={`numeric font-mono font-semibold ${
                      stock.totalScore > 25 ? "text-positive" : "text-text"
                    }`}
                  >
                    {stock.totalScore}
                  </td>
                  <td>
                    <Badge
                      variant={
                        stock.decision === "BUY" ? "positive" : "default"
                      }
                    >
                      {stock.decision}
                    </Badge>
                  </td>
                  <td>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleViewEvidence(stock.ticker)}
                    >
                      Evidence
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Evidence Drawer */}
      <EvidenceDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        tabs={evidenceTabs}
        title={`Evidence: ${selectedTicker}`}
      />
    </div>
  );
}
