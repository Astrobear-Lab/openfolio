import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { apiSuccess, apiError, getLatestDate } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const dateParam = searchParams.get("date");

  try {
    const targetDate = getLatestDate(dateParam);

    const features = await prisma.macroFeatureDaily.findMany({
      where: {
        date: {
          lte: targetDate,
        },
      },
      orderBy: { date: "desc" },
      take: 100,
    });

    // Group by date, then by feature
    const byDate: Record<string, any> = {};
    features.forEach((f) => {
      const dateKey = f.date.toISOString().split("T")[0];
      if (!byDate[dateKey]) {
        byDate[dateKey] = { date: dateKey, features: {} };
      }
      byDate[dateKey].features[f.feature] = {
        value: f.value?.toString(),
        details: f.detailsJson,
      };
    });

    const result = Object.values(byDate);

    return apiSuccess(
      {
        latest: result[0] || null,
        history: result,
      },
      "Computed from FRED/BLS"
    );
  } catch (error) {
    console.error("Error fetching macro features:", error);
    return apiError("Failed to fetch macro features", 500);
  }
}
