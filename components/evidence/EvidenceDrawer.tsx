"use client";

import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface EvidenceTab {
  id: string;
  label: string;
  content: React.ReactNode;
}

export interface EvidenceDrawerProps {
  open: boolean;
  onClose: () => void;
  tabs: EvidenceTab[];
  title?: string;
}

export function EvidenceDrawer({
  open,
  onClose,
  tabs,
  title = "Evidence",
}: EvidenceDrawerProps) {
  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-black/50 transition-opacity z-40",
          open ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn(
          "fixed top-0 right-0 h-full w-full md:w-[520px] bg-surface border-l border-border transition-transform z-50 flex flex-col",
          open ? "translate-x-0" : "translate-x-full"
        )}
      >
        {/* Header */}
        <header className="flex-shrink-0 p-4 border-b border-border flex items-center justify-between">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-md border border-border hover:bg-background transition-colors"
            aria-label="Close evidence panel"
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {tabs.map((tab) => (
            <section key={tab.id} id={tab.id}>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-text-subtle mb-3">
                {tab.label}
              </h3>
              <div className="prose prose-invert prose-sm max-w-none">
                {tab.content}
              </div>
            </section>
          ))}
        </div>
      </aside>
    </>
  );
}
