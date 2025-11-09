"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EvidenceDrawer } from "@/components/evidence/EvidenceDrawer";

export default function SectorBoardPage() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedSector, setSelectedSector] = useState<string | null>(null);

  // Mock data
  const sectors = [
    {
      sector: "XLK",
      name: "Technology",
      score: 8.5,
      rank: 1,
      momentum1m: 5.2,
      momentum3m: 12.8,
      volatility: 18.5,
      regimeTilt: "Positive",
    },
    {
      sector: "XLF",
      name: "Financials",
      score: 6.3,
      rank: 2,
      momentum1m: 3.1,
      momentum3m: 8.4,
      volatility: 15.2,
      regimeTilt: "Positive",
    },
    {
      sector: "XLY",
      name: "Consumer Discretionary",
      score: 5.1,
      rank: 3,
      momentum1m: 2.8,
      momentum3m: 6.9,
      volatility: 16.8,
      regimeTilt: "Neutral",
    },
    {
      sector: "XLE",
      name: "Energy",
      score: -2.3,
      rank: 10,
      momentum1m: -4.2,
      momentum3m: -8.1,
      volatility: 24.5,
      regimeTilt: "Negative",
    },
    {
      sector: "XLU",
      name: "Utilities",
      score: -3.1,
      rank: 11,
      momentum1m: -1.2,
      momentum3m: -3.5,
      volatility: 12.1,
      regimeTilt: "Negative",
    },
  ];

  const handleViewEvidence = (sector: string) => {
    setSelectedSector(sector);
    setDrawerOpen(true);
  };

  const evidenceTabs = selectedSector
    ? [
        {
          id: "components",
          label: "Score Components",
          content: (
            <div className="space-y-3 text-sm">
              <div>
                <strong>Momentum (1M):</strong>
                <p className="text-text-subtle">
                  Raw: +5.2% → Z-score: +1.3 → Weighted: +1.3
                </p>
              </div>
              <div>
                <strong>Momentum (3M):</strong>
                <p className="text-text-subtle">
                  Raw: +12.8% → Z-score: +1.8 → Weighted: +1.8
                </p>
              </div>
              <div>
                <strong>Volatility (3M):</strong>
                <p className="text-text-subtle">
                  Raw: 18.5% → Z-score: +0.5 → Weighted: -0.25 (penalized)
                </p>
              </div>
              <div>
                <strong>Regime Tilt:</strong>
                <p className="text-text-subtle">
                  Goldilocks regime favors growth sectors → Boost: +2.0
                </p>
              </div>
              <div className="pt-2 border-t border-border">
                <strong>Total Score:</strong>
                <p className="text-lg font-mono text-positive">+8.5</p>
              </div>
            </div>
          ),
        },
        {
          id: "calculation",
          label: "Scoring Formula",
          content: (
            <div className="space-y-2 text-sm text-text-subtle">
              <p>
                <strong>Formula:</strong>
              </p>
              <code className="block bg-background p-2 rounded text-xs">
                score = z(ret1m) + z(ret3m) + 0.5*z(ret6m)
                <br />
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;− 0.5*z(vol3m) +
                regime_tilt
              </code>
              <p className="pt-2">
                All returns and volatility are standardized using 36M rolling
                z-scores.
              </p>
              <p>
                Regime tilt adds +2 for favored sectors, 0 for neutral, -1 for
                disfavored.
              </p>
            </div>
          ),
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Sector Board</h1>
        <p className="text-text-subtle">
          Top-down sector rotation signals based on momentum, volatility, and
          regime
        </p>
      </div>

      {/* Top/Bottom Sectors */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card title="Top Sectors" subtitle="Strongest scores">
          <div className="space-y-2 py-2">
            {sectors.slice(0, 3).map((s) => (
              <div
                key={s.sector}
                className="flex items-center justify-between p-3 rounded-md border border-border hover:bg-surface/50"
              >
                <div className="flex items-center gap-3">
                  <Badge variant="positive" className="font-mono">
                    {s.sector}
                  </Badge>
                  <div>
                    <p className="font-medium">{s.name}</p>
                    <p className="text-xs text-text-subtle">
                      1M: {s.momentum1m > 0 ? "+" : ""}
                      {s.momentum1m}% • 3M: {s.momentum3m > 0 ? "+" : ""}
                      {s.momentum3m}%
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xl font-mono font-semibold text-positive">
                    +{s.score}
                  </p>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleViewEvidence(s.sector)}
                    className="text-xs"
                  >
                    Evidence
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Bottom Sectors" subtitle="Weakest scores">
          <div className="space-y-2 py-2">
            {sectors.slice(-2).map((s) => (
              <div
                key={s.sector}
                className="flex items-center justify-between p-3 rounded-md border border-border hover:bg-surface/50"
              >
                <div className="flex items-center gap-3">
                  <Badge variant="danger" className="font-mono">
                    {s.sector}
                  </Badge>
                  <div>
                    <p className="font-medium">{s.name}</p>
                    <p className="text-xs text-text-subtle">
                      1M: {s.momentum1m}% • 3M: {s.momentum3m}%
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xl font-mono font-semibold text-danger">
                    {s.score}
                  </p>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleViewEvidence(s.sector)}
                    className="text-xs"
                  >
                    Evidence
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Full Ranking Table */}
      <Card title="All Sectors" subtitle="Complete ranking with components">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Sector</th>
                <th>Name</th>
                <th className="numeric">Score</th>
                <th className="numeric">1M %</th>
                <th className="numeric">3M %</th>
                <th className="numeric">Vol %</th>
                <th>Regime Tilt</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sectors.map((s) => (
                <tr key={s.sector}>
                  <td>{s.rank}</td>
                  <td className="font-mono font-semibold">{s.sector}</td>
                  <td>{s.name}</td>
                  <td
                    className={`numeric font-mono font-semibold ${
                      s.score > 0 ? "text-positive" : "text-danger"
                    }`}
                  >
                    {s.score > 0 ? "+" : ""}
                    {s.score}
                  </td>
                  <td
                    className={`numeric ${
                      s.momentum1m > 0 ? "text-positive" : "text-danger"
                    }`}
                  >
                    {s.momentum1m > 0 ? "+" : ""}
                    {s.momentum1m}
                  </td>
                  <td
                    className={`numeric ${
                      s.momentum3m > 0 ? "text-positive" : "text-danger"
                    }`}
                  >
                    {s.momentum3m > 0 ? "+" : ""}
                    {s.momentum3m}
                  </td>
                  <td className="numeric">{s.volatility}</td>
                  <td>
                    <Badge
                      variant={
                        s.regimeTilt === "Positive"
                          ? "positive"
                          : s.regimeTilt === "Negative"
                          ? "danger"
                          : "default"
                      }
                    >
                      {s.regimeTilt}
                    </Badge>
                  </td>
                  <td>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleViewEvidence(s.sector)}
                    >
                      Details
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
        title={`Sector Evidence: ${selectedSector}`}
      />
    </div>
  );
}
