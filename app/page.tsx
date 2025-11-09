import Link from "next/link";
import { Card } from "@/components/ui/Card";
import {
  TrendingUp,
  PieChart,
  Filter,
  FileText,
  BarChart3,
  Database,
} from "lucide-react";

export default function HomePage() {
  const features = [
    {
      title: "Macro Lab",
      description:
        "Economic regime analysis with raw data transparency and z-score methodology",
      icon: TrendingUp,
      href: "/macro",
      color: "text-primary",
    },
    {
      title: "Sector Board",
      description:
        "Top-down sector scoring with momentum, volatility, and regime tilts",
      icon: PieChart,
      href: "/sectors",
      color: "text-positive",
    },
    {
      title: "Screener",
      description:
        "Multi-stage stock screening with full evidence trail and scoring breakdown",
      icon: Filter,
      href: "/screener",
      color: "text-warning",
    },
    {
      title: "Events Studio",
      description:
        "SEC filings and IR events with NLP sentiment and guidance extraction",
      icon: FileText,
      href: "/events",
      color: "text-danger",
    },
    {
      title: "AI Compare",
      description:
        "Multi-agent portfolio comparison (Aggressive/Balanced/Defensive) with rationale logs",
      icon: BarChart3,
      href: "/ai-compare",
      color: "text-primary",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <section className="text-center space-y-4 py-12">
        <h1 className="text-4xl font-bold tracking-tight">
          Openfolio
        </h1>
        <p className="text-xl text-text-subtle max-w-2xl mx-auto">
          Transparent investment analysis platform combining top-down macro analysis,
          sector rotation, event-driven insights, and multi-AI portfolio strategies
        </p>
        <div className="flex items-center justify-center gap-2 text-sm text-text-subtle">
          <Database className="w-4 h-4" />
          <span>All raw data exposed • Daily EOD updates • Not investment advice</span>
        </div>
      </section>

      {/* Features Grid */}
      <section className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature) => {
          const Icon = feature.icon;
          return (
            <Link
              key={feature.href}
              href={feature.href}
              className="group block transition-transform hover:scale-[1.02]"
            >
              <Card
                title={feature.title}
                subtitle={feature.description}
              >
                <div className="flex items-center justify-center py-8">
                  <Icon
                    className={`w-16 h-16 ${feature.color} group-hover:scale-110 transition-transform`}
                  />
                </div>
              </Card>
            </Link>
          );
        })}
      </section>

      {/* Methodology Overview */}
      <section className="mt-12">
        <Card title="Methodology" subtitle="How Openfolio analyzes markets">
          <div className="grid md:grid-cols-2 gap-6 py-4">
            <div>
              <h4 className="font-semibold mb-2">Top-Down Framework</h4>
              <ol className="space-y-2 text-sm text-text-subtle">
                <li>1. Macro regime classification (Growth/Inflation/Liquidity)</li>
                <li>2. Sector scoring with regime tilts</li>
                <li>3. Stock screening (Quality/Value/Momentum/Events)</li>
                <li>4. Technical confirmation</li>
                <li>5. Multi-AI portfolio construction</li>
              </ol>
            </div>
            <div>
              <h4 className="font-semibold mb-2">Transparency Principles</h4>
              <ul className="space-y-2 text-sm text-text-subtle">
                <li>• All raw data sources linked and versioned</li>
                <li>• Z-score normalization with 36M rolling windows</li>
                <li>• Evidence panels show inputs, calculations, and citations</li>
                <li>• AI decision rationales logged with timestamps</li>
                <li>• Daily ETL pipeline with seed data for offline testing</li>
              </ul>
            </div>
          </div>
        </Card>
      </section>

      {/* Disclaimer */}
      <section className="text-center text-xs text-text-subtle border-t border-border pt-6">
        <p>
          <strong>Disclaimer:</strong> Openfolio is an educational research tool.
          Data may be delayed or inaccurate. This is not investment advice.
          Always consult a licensed financial advisor before making investment decisions.
        </p>
      </section>
    </div>
  );
}
