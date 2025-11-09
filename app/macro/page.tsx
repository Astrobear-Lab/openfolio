"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { KpiTile } from "@/components/ui/KpiTile";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EvidenceDrawer } from "@/components/evidence/EvidenceDrawer";
import { ExternalLink } from "lucide-react";

export default function MacroLabPage() {
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Mock data - will be replaced with API calls
  const regime = {
    date: "2024-11-08",
    regime: "Goldilocks",
    inputs: {
      growthZ: "1.2",
      inflationZ: "-0.5",
      liquidityZ: "0.8",
      ratesZ: "-0.3",
    },
  };

  const evidenceTabs = [
    {
      id: "inputs",
      label: "Raw Inputs",
      content: (
        <div className="space-y-3">
          <div className="text-sm">
            <strong>Growth Indicators:</strong>
            <ul className="mt-2 space-y-1 text-text-subtle">
              <li>• INDPRO (Industrial Production): 103.2 → z-score: +1.2</li>
              <li>• PAYEMS (Nonfarm Payrolls): 158.2M → z-score: +1.1</li>
              <li>• RSAFS (Retail Sales): $705B → z-score: +0.9</li>
            </ul>
          </div>
          <div className="text-sm">
            <strong>Inflation Indicators:</strong>
            <ul className="mt-2 space-y-1 text-text-subtle">
              <li>• CPIAUCSL (CPI All Items): 309.5 → z-score: -0.5</li>
              <li>• CPILFESL (Core CPI): 320.1 → z-score: -0.4</li>
            </ul>
          </div>
        </div>
      ),
    },
    {
      id: "calculation",
      label: "Z-Score Method",
      content: (
        <div className="space-y-2 text-sm text-text-subtle">
          <p>
            <strong>Rolling Window:</strong> 36 months
          </p>
          <p>
            <strong>Formula:</strong> z = (x - μ) / σ
          </p>
          <p>
            Where μ is the 36M mean and σ is the 36M standard deviation.
          </p>
          <p>
            Monthly/quarterly series are forward-filled to daily frequency before z-score calculation.
          </p>
        </div>
      ),
    },
    {
      id: "regime-rules",
      label: "Regime Rules",
      content: (
        <div className="space-y-2 text-sm">
          <div>
            <strong className="text-positive">Goldilocks</strong>
            <p className="text-text-subtle">Growth ↑, Inflation ↓</p>
          </div>
          <div>
            <strong className="text-warning">Reflation</strong>
            <p className="text-text-subtle">Growth ↑, Inflation ↑</p>
          </div>
          <div>
            <strong className="text-danger">Stagflation</strong>
            <p className="text-text-subtle">Growth ↓, Inflation ↑</p>
          </div>
          <div>
            <strong className="text-primary">Disinflation</strong>
            <p className="text-text-subtle">Growth ↓, Inflation ↓</p>
          </div>
        </div>
      ),
    },
    {
      id: "sources",
      label: "Sources",
      content: (
        <div className="space-y-2 text-sm">
          <a
            href="https://fred.stlouisfed.org"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 text-primary hover:underline"
          >
            FRED (Federal Reserve Economic Data)
            <ExternalLink className="w-3 h-3" />
          </a>
          <p className="text-text-subtle">Last updated: 2024-11-08 EOD</p>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Macro Lab</h1>
        <p className="text-text-subtle">
          Economic regime analysis with full transparency and data lineage
        </p>
      </div>

      {/* KPI Tiles */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KpiTile
          label="Current Regime"
          value={regime.regime}
          delta="Strong"
          positive={true}
        />
        <KpiTile label="Growth Z-Score" value={regime.inputs.growthZ} />
        <KpiTile label="Inflation Z-Score" value={regime.inputs.inflationZ} />
        <KpiTile label="Liquidity Z-Score" value={regime.inputs.liquidityZ} />
      </div>

      {/* Regime Card */}
      <Card
        title="Regime Classification"
        subtitle="Based on growth, inflation, liquidity, and rate signals"
        updatedAt="01:32 UTC"
        actions={
          <Button size="sm" onClick={() => setDrawerOpen(true)}>
            View Evidence
          </Button>
        }
      >
        <div className="space-y-4 py-4">
          <div className="flex items-center gap-3">
            <Badge variant="positive" className="text-lg px-4 py-2">
              {regime.regime}
            </Badge>
            <span className="text-sm text-text-subtle">
              Growth expanding, inflation cooling — favorable for risk assets
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-border">
            <div>
              <p className="text-xs text-text-subtle mb-1">Growth Z</p>
              <p className="text-xl font-mono font-semibold text-positive">
                +{regime.inputs.growthZ}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-subtle mb-1">Inflation Z</p>
              <p className="text-xl font-mono font-semibold text-text">
                {regime.inputs.inflationZ}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-subtle mb-1">Liquidity Z</p>
              <p className="text-xl font-mono font-semibold text-positive">
                +{regime.inputs.liquidityZ}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-subtle mb-1">Rates Z</p>
              <p className="text-xl font-mono font-semibold text-text">
                {regime.inputs.ratesZ}
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* Key Indicators Table */}
      <Card title="Key Economic Indicators" subtitle="Latest readings with z-scores">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Series</th>
                <th>Name</th>
                <th className="numeric">Latest Value</th>
                <th className="numeric">Z-Score</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="font-mono text-xs">INDPRO</td>
                <td>Industrial Production</td>
                <td className="numeric">103.2</td>
                <td className="numeric text-positive">+1.2</td>
                <td>
                  <a
                    href="https://fred.stlouisfed.org/series/INDPRO"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline text-xs"
                  >
                    FRED
                  </a>
                </td>
              </tr>
              <tr>
                <td className="font-mono text-xs">CPIAUCSL</td>
                <td>Consumer Price Index</td>
                <td className="numeric">309.5</td>
                <td className="numeric">-0.5</td>
                <td>
                  <a
                    href="https://fred.stlouisfed.org/series/CPIAUCSL"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline text-xs"
                  >
                    FRED
                  </a>
                </td>
              </tr>
              <tr>
                <td className="font-mono text-xs">M2SL</td>
                <td>M2 Money Supply</td>
                <td className="numeric">$21.1T</td>
                <td className="numeric text-positive">+0.8</td>
                <td>
                  <a
                    href="https://fred.stlouisfed.org/series/M2SL"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline text-xs"
                  >
                    FRED
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      {/* Evidence Drawer */}
      <EvidenceDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        tabs={evidenceTabs}
        title="Regime Evidence"
      />
    </div>
  );
}
