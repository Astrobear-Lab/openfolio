import { cn } from "@/lib/utils";

export interface CardProps {
  title: string;
  subtitle?: string;
  updatedAt?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export function Card({
  title,
  subtitle,
  updatedAt,
  actions,
  children,
  className,
}: CardProps) {
  return (
    <section
      className={cn(
        "rounded-lg bg-surface text-text shadow-card border border-border p-4",
        className
      )}
    >
      <header className="mb-3 flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h3 className="text-[18px] font-semibold leading-tight">{title}</h3>
          {subtitle && (
            <p className="text-text-subtle text-sm mt-1 leading-snug">
              {subtitle}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {updatedAt && (
            <span className="text-xs text-text-subtle whitespace-nowrap">
              Updated {updatedAt}
            </span>
          )}
          {actions}
        </div>
      </header>
      <div>{children}</div>
    </section>
  );
}
