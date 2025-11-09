import { NextResponse } from "next/server";

export const APP_VERSION = "1.0.0";
export const ETL_VERSION = "1.0.0";

export interface ApiResponse<T = any> {
  data: T;
  timestamp: string;
  source?: string;
  version?: string;
}

export function apiSuccess<T>(
  data: T,
  source?: string,
  version: string = APP_VERSION
): NextResponse<ApiResponse<T>> {
  return NextResponse.json({
    data,
    timestamp: new Date().toISOString(),
    source,
    version,
  });
}

export function apiError(message: string, status: number = 400) {
  return NextResponse.json(
    {
      error: message,
      timestamp: new Date().toISOString(),
    },
    { status }
  );
}

export function parseRange(range: string): { from: Date; to: Date } {
  const now = new Date();
  const to = new Date(now);
  to.setHours(23, 59, 59, 999);

  let from = new Date(now);

  if (range.endsWith("d")) {
    const days = parseInt(range);
    from.setDate(from.getDate() - days);
  } else if (range.endsWith("m")) {
    const months = parseInt(range);
    from.setMonth(from.getMonth() - months);
  } else if (range.endsWith("y")) {
    const years = parseInt(range);
    from.setFullYear(from.getFullYear() - years);
  } else {
    // Default to 30 days
    from.setDate(from.getDate() - 30);
  }

  from.setHours(0, 0, 0, 0);
  return { from, to };
}

export function getLatestDate(dateParam: string | null): Date {
  if (dateParam === "latest" || !dateParam) {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }
  return new Date(dateParam);
}
