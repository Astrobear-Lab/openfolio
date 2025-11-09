import { cn } from "@/lib/utils";

export interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "primary" | "positive" | "warning" | "danger";
  className?: string;
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
        {
          "bg-surface border border-border text-text": variant === "default",
          "bg-primary/10 text-primary border border-primary/20": variant === "primary",
          "bg-positive/10 text-positive border border-positive/20": variant === "positive",
          "bg-warning/10 text-warning border border-warning/20": variant === "warning",
          "bg-danger/10 text-danger border border-danger/20": variant === "danger",
        },
        className
      )}
    >
      {children}
    </span>
  );
}
