import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { apiSuccess, apiError, getLatestDate } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const dateParam = searchParams.get("date");

  try {
    const targetDate = getLatestDate(dateParam);

    const regime = await prisma.macroRegimeDaily.findFirst({
      where: {
        date: {
          lte: targetDate,
        },
      },
      orderBy: { date: "desc" },
    });

    if (!regime) {
      return apiError("No regime data available", 404);
    }

    return apiSuccess(
      {
        date: regime.date.toISOString().split("T")[0],
        regime: regime.regime,
        inputs: {
          growthZ: regime.growthZ?.toString(),
          inflationZ: regime.inflationZ?.toString(),
          liquidityZ: regime.liquidityZ?.toString(),
          ratesZ: regime.ratesZ?.toString(),
        },
        details: regime.detailsJson,
      },
      "Regime classification engine"
    );
  } catch (error) {
    console.error("Error fetching regime:", error);
    return apiError("Failed to fetch regime", 500);
  }
}
