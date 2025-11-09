import { cn } from "@/lib/utils";

export interface KpiTileProps {
  label: string;
  value: string;
  delta?: string;
  positive?: boolean;
  className?: string;
}

export function KpiTile({
  label,
  value,
  delta,
  positive,
  className,
}: KpiTileProps) {
  return (
    <div
      className={cn(
        "rounded-md border border-border bg-surface p-3",
        className
      )}
    >
      <p className="text-sm text-text-subtle mb-1">{label}</p>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-semibold font-mono">{value}</span>
        {delta && (
          <span
            className={cn(
              "text-xs px-1.5 py-0.5 rounded font-medium",
              positive
                ? "bg-positive/10 text-positive"
                : "bg-danger/10 text-danger"
            )}
          >
            {delta}
          </span>
        )}
      </div>
    </div>
  );
}
