"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ExternalLink, FileText } from "lucide-react";

export default function EventsStudioPage() {
  const [selectedEvent, setSelectedEvent] = useState<number | null>(null);

  // Mock events data
  const events = [
    {
      id: 1,
      ticker: "AAPL",
      datetime: "2024-11-01T16:30:00Z",
      type: "Earnings",
      title: "Q4 2024 Earnings Call",
      url: "https://sec.gov/...",
      sentiment: 0.82,
      guidance: "Positive - Strong Services momentum",
      surpriseEps: 2.5,
      topics: ["Services", "iPhone", "China"],
      quotes: [
        "We delivered our best Services quarter ever",
        "iPhone sales exceeded expectations across all regions",
      ],
      body: `Apple Inc. reported fourth quarter earnings that beat analyst expectations...`,
    },
    {
      id: 2,
      ticker: "MSFT",
      datetime: "2024-10-28T20:00:00Z",
      type: "8-K Filing",
      title: "Azure Growth Update",
      url: "https://sec.gov/...",
      sentiment: 0.75,
      guidance: "Positive - Cloud acceleration",
      surpriseEps: null,
      topics: ["Azure", "Cloud", "AI"],
      quotes: [
        "Azure revenue growth accelerated to 33%",
        "AI services contribute $10B+ annualized revenue",
      ],
      body: `Microsoft filed an 8-K update on Azure performance...`,
    },
    {
      id: 3,
      ticker: "TSLA",
      datetime: "2024-10-25T21:00:00Z",
      type: "Earnings",
      title: "Q3 2024 Earnings Call",
      url: "https://sec.gov/...",
      sentiment: -0.15,
      guidance: "Mixed - Production concerns",
      surpriseEps: -5.2,
      topics: ["Production", "Margins", "Cybertruck"],
      quotes: [
        "Margin pressure from increased competition",
        "Cybertruck production ramping slower than expected",
      ],
      body: `Tesla reported Q3 earnings that missed expectations...`,
    },
  ];

  const selectedEventData = events.find((e) => e.id === selectedEvent);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Events Studio</h1>
        <p className="text-text-subtle">
          SEC filings and earnings events with NLP sentiment analysis
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Event List */}
        <div className="space-y-4">
          <Card title="Recent Events" subtitle="Last 30 days">
            <div className="space-y-3">
              {events.map((event) => (
                <div
                  key={event.id}
                  className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                    selectedEvent === event.id
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-surface/50"
                  }`}
                  onClick={() => setSelectedEvent(event.id)}
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-text-subtle flex-shrink-0" />
                      <Badge variant="default" className="font-mono">
                        {event.ticker}
                      </Badge>
                      <Badge
                        variant={
                          event.type === "Earnings" ? "primary" : "default"
                        }
                      >
                        {event.type}
                      </Badge>
                    </div>
                    <Badge
                      variant={
                        event.sentiment > 0.5
                          ? "positive"
                          : event.sentiment < -0.2
                          ? "danger"
                          : "warning"
                      }
                    >
                      {event.sentiment > 0
                        ? `+${event.sentiment.toFixed(2)}`
                        : event.sentiment.toFixed(2)}
                    </Badge>
                  </div>

                  <h4 className="font-semibold text-sm mb-1">
                    {event.title}
                  </h4>
                  <p className="text-xs text-text-subtle">
                    {new Date(event.datetime).toLocaleString()}
                  </p>

                  {event.surpriseEps !== null && (
                    <div className="mt-2 text-xs">
                      <span className="text-text-subtle">EPS Surprise: </span>
                      <span
                        className={
                          event.surpriseEps > 0 ? "text-positive" : "text-danger"
                        }
                      >
                        {event.surpriseEps > 0 ? "+" : ""}
                        {event.surpriseEps}%
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Event Detail */}
        <div>
          {selectedEventData ? (
            <div className="space-y-4">
              <Card
                title={selectedEventData.title}
                subtitle={`${selectedEventData.ticker} • ${new Date(
                  selectedEventData.datetime
                ).toLocaleDateString()}`}
                actions={
                  <a
                    href={selectedEventData.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline flex items-center gap-1 text-sm"
                  >
                    Source <ExternalLink className="w-3 h-3" />
                  </a>
                }
              >
                <div className="space-y-4">
                  {/* Sentiment */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Sentiment</h4>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-2 bg-background rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            selectedEventData.sentiment > 0
                              ? "bg-positive"
                              : "bg-danger"
                          }`}
                          style={{
                            width: `${Math.abs(selectedEventData.sentiment) * 100}%`,
                          }}
                        />
                      </div>
                      <span className="font-mono text-sm w-12 text-right">
                        {selectedEventData.sentiment.toFixed(2)}
                      </span>
                    </div>
                  </div>

                  {/* Guidance */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Guidance</h4>
                    <p className="text-sm text-text-subtle">
                      {selectedEventData.guidance}
                    </p>
                  </div>

                  {/* Topics */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Topics</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedEventData.topics.map((topic) => (
                        <Badge key={topic} variant="default">
                          {topic}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Key Quotes */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Key Quotes</h4>
                    <div className="space-y-2">
                      {selectedEventData.quotes.map((quote, idx) => (
                        <blockquote
                          key={idx}
                          className="border-l-2 border-primary pl-3 text-sm text-text-subtle italic"
                        >
                          "{quote}"
                        </blockquote>
                      ))}
                    </div>
                  </div>

                  {/* Body Preview */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Summary</h4>
                    <p className="text-sm text-text-subtle">
                      {selectedEventData.body}
                    </p>
                  </div>
                </div>
              </Card>

              {/* NLP Metadata */}
              <Card title="NLP Analysis" subtitle="Model information">
                <div className="text-sm space-y-1 text-text-subtle">
                  <p>
                    <strong>Model:</strong> FinBERT + GPT-4-mini
                  </p>
                  <p>
                    <strong>Version:</strong> 1.0.0
                  </p>
                  <p>
                    <strong>Processed:</strong>{" "}
                    {new Date(selectedEventData.datetime).toLocaleString()}
                  </p>
                </div>
              </Card>
            </div>
          ) : (
            <Card title="No Event Selected">
              <p className="text-text-subtle text-center py-8">
                Select an event from the list to view details
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
