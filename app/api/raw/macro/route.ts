import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { apiSuccess, apiError, parseRange } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const seriesCode = searchParams.get("series");
  const fromParam = searchParams.get("from");

  if (!seriesCode) {
    return apiError("Missing required parameter: series");
  }

  try {
    const series = await prisma.macroSeries.findUnique({
      where: { code: seriesCode },
    });

    if (!series) {
      return apiError(`Series not found: ${seriesCode}`, 404);
    }

    const where: any = {
      seriesId: series.id,
    };

    if (fromParam) {
      where.ts = {
        gte: new Date(fromParam),
      };
    }

    const points = await prisma.macroPoint.findMany({
      where,
      orderBy: { ts: "desc" },
      take: 1000, // Limit for performance
    });

    return apiSuccess(
      {
        series: {
          code: series.code,
          name: series.name,
          source: series.source,
          freq: series.freq,
        },
        points: points.map((p) => ({
          date: p.ts.toISOString().split("T")[0],
          value: p.value?.toString(),
          revisionOf: p.revisionOf?.toISOString().split("T")[0],
          url: p.url,
          rawJson: p.rawJson,
        })),
      },
      series.source || "FRED"
    );
  } catch (error) {
    console.error("Error fetching macro data:", error);
    return apiError("Failed to fetch macro data", 500);
  }
}
