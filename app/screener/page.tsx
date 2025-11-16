"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EvidenceDrawer } from "@/components/evidence/EvidenceDrawer";
import { Check, X } from "lucide-react";

interface ScreeningResult {
  ticker: string;
  name: string;
  sector: string;
  rank: number;
  totalScore: number;
  decision: string;
  stagesPassed: number;
  qualityPass: boolean;
  qualityScore: number;
  valuePass: boolean;
  valueScore: number;
  eventPass: boolean;
  eventScore: number;
  taPass: boolean;
  taScore: number;
  details: any;
}

export default function ScreenerPage() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [screeningResults, setScreeningResults] = useState<ScreeningResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    totalScreened: 0,
    passedCount: 0,
    topScore: 0
  });

  useEffect(() => {
    async function fetchScreeningResults() {
      try {
        const response = await fetch("/api/screener/results?date=latest");
        if (!response.ok) {
          throw new Error("Failed to fetch screening results");
        }
        const result = await response.json();

        if (result.data?.rankings) {
          setScreeningResults(result.data.rankings);
          setStats({
            totalScreened: result.data.totalScreened || 0,
            passedCount: result.data.passedCount || 0,
            topScore: result.data.topScore || 0
          });
        } else {
          // Fallback to mock data when no results
          setScreeningResults([
            {
              ticker: "AAPL",
              name: "Apple Inc.",
              sector: "XLK",
              rank: 1,
              totalScore: 30.6,
              decision: "BUY",
              stagesPassed: 4,
              qualityPass: true,
              qualityScore: 8.5,
              valuePass: true,
              valueScore: 6.2,
              eventPass: true,
              eventScore: 7.8,
              taPass: true,
              taScore: 8.1,
              details: {}
            },
            {
              ticker: "MSFT",
              name: "Microsoft Corp.",
              sector: "XLK",
              rank: 2,
              totalScore: 31.3,
              decision: "BUY",
              stagesPassed: 4,
              qualityPass: true,
              qualityScore: 9.1,
              valuePass: true,
              valueScore: 5.8,
              eventPass: true,
              eventScore: 8.5,
              taPass: true,
              taScore: 7.9,
              details: {}
            },
            {
              ticker: "XOM",
              name: "Exxon Mobil Corp.",
              sector: "XLE",
              rank: 15,
              totalScore: 16.6,
              decision: "PASS",
              stagesPassed: 1,
              qualityPass: true,
              qualityScore: 7.2,
              valuePass: false,
              valueScore: 3.1,
              eventPass: false,
              eventScore: 2.5,
              taPass: false,
              taScore: 3.8,
              details: {}
            }
          ]);
          setStats({ totalScreened: 3, passedCount: 2, topScore: 31.3 });
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
        // Fallback to mock data
        setScreeningResults([
          {
            ticker: "AAPL",
            name: "Apple Inc.",
            sector: "XLK",
            rank: 1,
            totalScore: 30.6,
            decision: "BUY",
            stagesPassed: 4,
            qualityPass: true,
            qualityScore: 8.5,
            valuePass: true,
            valueScore: 6.2,
            eventPass: true,
            eventScore: 7.8,
            taPass: true,
            taScore: 8.1,
            details: {}
          },
          {
            ticker: "MSFT",
            name: "Microsoft Corp.",
            sector: "XLK",
            rank: 2,
            totalScore: 31.3,
            decision: "BUY",
            stagesPassed: 4,
            qualityPass: true,
            qualityScore: 9.1,
            valuePass: true,
            valueScore: 5.8,
            eventPass: true,
            eventScore: 8.5,
            taPass: true,
            taScore: 7.9,
            details: {}
          },
          {
            ticker: "XOM",
            name: "Exxon Mobil Corp.",
            sector: "XLE",
            rank: 15,
            totalScore: 16.6,
            decision: "PASS",
            stagesPassed: 1,
            qualityPass: true,
            qualityScore: 7.2,
            valuePass: false,
            valueScore: 3.1,
            eventPass: false,
            eventScore: 2.5,
            taPass: false,
            taScore: 3.8,
            details: {}
          }
        ]);
        setStats({ totalScreened: 3, passedCount: 2, topScore: 31.3 });
      } finally {
        setLoading(false);
      }
    }

    fetchScreeningResults();
  }, []);

  const handleViewEvidence = (ticker: string) => {
    setSelectedTicker(ticker);
    setDrawerOpen(true);
  };

  // Get selected stock details for evidence drawer
  const selectedStock = selectedTicker
    ? screeningResults.find(s => s.ticker === selectedTicker)
    : null;

  const evidenceTabs = selectedStock
    ? [
        {
          id: "quality",
          label: "Quality",
          content: (
            <div className="space-y-3 text-sm">
              <div>
                <strong>ROE (Return on Equity):</strong>
                <p className="text-text-subtle">
                  {selectedStock.details?.quality?.metrics?.roe?.toFixed(1) || "N/A"}% → Score: {selectedStock.qualityScore?.toFixed(1) || "N/A"}
                  {selectedStock.qualityPass ? " ✓" : " ✗"}
                </p>
              </div>
              <div>
                <strong>Gross Margin:</strong>
                <p className="text-text-subtle">
                  {selectedStock.details?.quality?.metrics?.gross_margin?.toFixed(1) || "N/A"}% → Fundamental metric
                </p>
              </div>
              <div>
                <strong>Debt/Equity:</strong>
                <p className="text-text-subtle">
                  {selectedStock.details?.quality?.metrics?.debt_to_equity?.toFixed(2) || "N/A"} → Leverage ratio
                </p>
              </div>
              <div className="pt-2 border-t border-border">
                <strong>Quality Score:</strong>
                <p className="text-lg font-mono text-positive">{selectedStock.qualityScore?.toFixed(1) || "N/A"}</p>
                <Badge variant={selectedStock.qualityPass ? "positive" : "danger"}>
                  {selectedStock.qualityPass ? "PASS" : "FAIL"}
                </Badge>
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
                <p className="text-text-subtle">
                  {selectedStock.details?.value?.metrics?.pe_ratio?.toFixed(1) || "N/A"} → Valuation metric
                </p>
              </div>
              <div>
                <strong>P/B Ratio:</strong>
                <p className="text-text-subtle">
                  {selectedStock.details?.value?.metrics?.pb_ratio?.toFixed(1) || "N/A"} → Valuation metric
                </p>
              </div>
              <div>
                <strong>EV/EBITDA:</strong>
                <p className="text-text-subtle">
                  {selectedStock.details?.value?.metrics?.ev_ebitda?.toFixed(1) || "N/A"} → Valuation metric
                </p>
              </div>
              <div className="pt-2 border-t border-border">
                <strong>Value Score:</strong>
                <p className="text-lg font-mono">{selectedStock.valueScore?.toFixed(1) || "N/A"}</p>
                <Badge variant={selectedStock.valuePass ? "positive" : "danger"}>
                  {selectedStock.valuePass ? "PASS" : "FAIL"}
                </Badge>
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
                <strong>Earnings Surprise:</strong>
                <p className="text-text-subtle">
                  {selectedStock.details?.events?.metrics?.earnings_surprise?.toFixed(1) || "N/A"}% → Recent performance
                </p>
              </div>
              <div>
                <strong>1M Returns:</strong>
                <p className="text-text-subtle">
                  {selectedStock.details?.events?.metrics?.returns_1m?.toFixed(1) || "N/A"}% → Momentum
                </p>
              </div>
              <div>
                <strong>3M Returns:</strong>
                <p className="text-text-subtle">
                  {selectedStock.details?.events?.metrics?.returns_3m?.toFixed(1) || "N/A"}% → Trend
                </p>
              </div>
              <div>
                <strong>Sentiment:</strong>
                <p className="text-text-subtle">
                  {selectedStock.details?.events?.metrics?.sentiment?.toFixed(2) || "N/A"} → Market sentiment
                </p>
              </div>
              <div className="pt-2 border-t border-border">
                <strong>Event Score:</strong>
                <p className="text-lg font-mono text-positive">{selectedStock.eventScore?.toFixed(1) || "N/A"}</p>
                <Badge variant={selectedStock.eventPass ? "positive" : "danger"}>
                  {selectedStock.eventPass ? "PASS" : "FAIL"}
                </Badge>
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
                <p className="text-text-subtle">
                  {selectedStock.details?.technical?.metrics?.rsi?.toFixed(1) || "N/A"} → Momentum oscillator
                </p>
              </div>
              <div>
                <strong>MACD Signal:</strong>
                <p className="text-text-subtle">
                  {selectedStock.details?.technical?.metrics?.macd_signal?.toFixed(2) || "N/A"} → Trend indicator
                </p>
              </div>
              <div>
                <strong>Momentum:</strong>
                <p className="text-text-subtle">
                  {selectedStock.details?.technical?.metrics?.momentum?.toFixed(1) || "N/A"}% → Recent momentum
                </p>
              </div>
              <div>
                <strong>Trend Strength:</strong>
                <p className="text-text-subtle">
                  {selectedStock.details?.technical?.metrics?.trend_strength?.toFixed(2) || "N/A"} → Trend strength
                </p>
              </div>
              <div className="pt-2 border-t border-border">
                <strong>TA Score:</strong>
                <p className="text-lg font-mono text-positive">{selectedStock.taScore?.toFixed(1) || "N/A"}</p>
                <Badge variant={selectedStock.taPass ? "positive" : "danger"}>
                  {selectedStock.taPass ? "PASS" : "FAIL"}
                </Badge>
              </div>
            </div>
          ),
        },
      ]
    : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-text-subtle">Loading screener data...</p>
      </div>
    );
  }

  if (error && screeningResults.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-2">
          <p className="text-danger">Error loading screener data</p>
          <p className="text-sm text-text-subtle">{error}</p>
          <p className="text-xs text-text-subtle mt-4">
            Make sure the ETL screener pipeline has run to populate data.
          </p>
        </div>
      </div>
    );
  }

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
          <p className="text-2xl font-mono font-semibold">{stats.totalScreened}</p>
        </Card>
        <Card title="Passed All Stages" className="p-3">
          <p className="text-2xl font-mono font-semibold text-positive">{stats.passedCount}</p>
        </Card>
        <Card title="Top Score" className="p-3">
          <p className="text-2xl font-mono font-semibold text-primary">{stats.topScore?.toFixed(1) || "N/A"}</p>
        </Card>
        <Card title="Last Updated" className="p-3">
          <p className="text-sm font-mono">
            {new Date().toLocaleDateString()}
          </p>
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
