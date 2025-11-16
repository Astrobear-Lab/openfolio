"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { KpiTile } from "@/components/ui/KpiTile";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EvidenceDrawer } from "@/components/evidence/EvidenceDrawer";
import { ExternalLink } from "lucide-react";

interface RegimeData {
  date: string;
  regime: string;
  inputs: {
    growthZ: number;
    inflationZ: number;
    liquidityZ: number;
    ratesZ: number;
  };
  details?: any;
}

export default function MacroLabPage() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [regime, setRegime] = useState<RegimeData | null>(null);
  const [indicators, setIndicators] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        // Fetch regime data
        const regimeResponse = await fetch("/api/regime?date=latest");
        if (!regimeResponse.ok) {
          throw new Error("Failed to fetch regime data");
        }
        const regimeResult = await regimeResponse.json();
        setRegime(regimeResult.data);

        // Fetch indicators data
        const indicatorsResponse = await fetch("/api/macro-indicators?date=latest");
        if (!indicatorsResponse.ok) {
          throw new Error("Failed to fetch indicators data");
        }
        const indicatorsResult = await indicatorsResponse.json();
        setIndicators(indicatorsResult.data?.indicators || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-text-subtle">Loading macro data...</p>
      </div>
    );
  }

  if (error || !regime) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center space-y-2">
          <p className="text-danger">Error loading regime data</p>
          <p className="text-sm text-text-subtle">{error}</p>
          <p className="text-xs text-text-subtle mt-4">
            Make sure the ETL pipeline has run at least once to populate data.
          </p>
        </div>
      </div>
    );
  }

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
          delta="Live"
          positive={true}
        />
        <KpiTile
          label="Growth Z-Score"
          value={regime.inputs.growthZ.toFixed(2)}
        />
        <KpiTile
          label="Inflation Z-Score"
          value={regime.inputs.inflationZ.toFixed(2)}
        />
        <KpiTile
          label="Liquidity Z-Score"
          value={regime.inputs.liquidityZ.toFixed(2)}
        />
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
              <p
                className={`text-xl font-mono font-semibold ${
                  regime.inputs.growthZ > 0 ? "text-positive" : "text-danger"
                }`}
              >
                {regime.inputs.growthZ > 0 ? "+" : ""}
                {regime.inputs.growthZ.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-subtle mb-1">Inflation Z</p>
              <p
                className={`text-xl font-mono font-semibold ${
                  regime.inputs.inflationZ > 0 ? "text-danger" : "text-positive"
                }`}
              >
                {regime.inputs.inflationZ > 0 ? "+" : ""}
                {regime.inputs.inflationZ.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-subtle mb-1">Liquidity Z</p>
              <p
                className={`text-xl font-mono font-semibold ${
                  regime.inputs.liquidityZ > 0 ? "text-positive" : "text-danger"
                }`}
              >
                {regime.inputs.liquidityZ > 0 ? "+" : ""}
                {regime.inputs.liquidityZ.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs text-text-subtle mb-1">Rates Z</p>
              <p
                className={`text-xl font-mono font-semibold ${
                  regime.inputs.ratesZ < 0 ? "text-positive" : "text-danger"
                }`}
              >
                {regime.inputs.ratesZ > 0 ? "+" : ""}
                {regime.inputs.ratesZ.toFixed(2)}
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
              {indicators.length > 0 ? (
                indicators.map((indicator) => (
                  <tr key={indicator.code}>
                    <td className="font-mono text-xs">{indicator.code}</td>
                    <td>{indicator.name}</td>
                    <td className="numeric">
                      {indicator.code === "M2SL"
                        ? `$${Math.round(indicator.value / 1000)}T`
                        : indicator.code.includes("CPI")
                        ? indicator.value.toFixed(1)
                        : indicator.value.toFixed(1)
                      }
                    </td>
                    <td className={`numeric ${
                      indicator.zScore > 0 ? "text-positive" :
                      indicator.zScore < 0 ? "text-danger" : "text-text"
                    }`}>
                      {indicator.zScore > 0 ? "+" : ""}
                      {indicator.zScore?.toFixed(1) || "N/A"}
                    </td>
                    <td>
                      <a
                        href={`https://fred.stlouisfed.org/series/${indicator.code}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline text-xs"
                      >
                        {indicator.source}
                      </a>
                    </td>
                  </tr>
                ))
              ) : (
                // Fallback mock data when no indicators loaded
                <>
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
                </>
              )}
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
