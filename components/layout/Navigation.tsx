"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  TrendingUp,
  PieChart,
  Filter,
  FileText,
  BarChart3,
  Home,
} from "lucide-react";

const navItems = [
  { href: "/", icon: Home, label: "Home" },
  { href: "/macro", icon: TrendingUp, label: "Macro Lab" },
  { href: "/sectors", icon: PieChart, label: "Sectors" },
  { href: "/screener", icon: Filter, label: "Screener" },
  { href: "/events", icon: FileText, label: "Events" },
  { href: "/ai-compare", icon: BarChart3, label: "AI Compare" },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav
      className="w-20 bg-surface border-r border-border flex flex-col items-center py-6 space-y-4"
      aria-label="Main navigation"
    >
      {/* Logo */}
      <div className="mb-4">
        <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center">
          <span className="text-lg font-bold text-white">O</span>
        </div>
      </div>

      {/* Nav Items */}
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href;

        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "w-12 h-12 rounded-lg flex items-center justify-center transition-colors relative group",
              isActive
                ? "bg-primary text-white"
                : "text-text-subtle hover:bg-background hover:text-text"
            )}
            aria-label={item.label}
            aria-current={isActive ? "page" : undefined}
          >
            <Icon className="w-5 h-5" />

            {/* Tooltip */}
            <span className="absolute left-16 bg-surface border border-border px-2 py-1 rounded text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
              {item.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
