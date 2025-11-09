import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { apiSuccess, apiError, getLatestDate } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const dateParam = searchParams.get("date");

  try {
    const targetDate = getLatestDate(dateParam);

    const scores = await prisma.sectorScore.findMany({
      where: {
        date: {
          lte: targetDate,
        },
      },
      orderBy: [{ date: "desc" }, { score: "desc" }],
      take: 20, // Assume ~11 sectors
    });

    if (scores.length === 0) {
      return apiError("No sector scores available", 404);
    }

    const latestDate = scores[0].date;
    const latestScores = scores.filter(
      (s) => s.date.getTime() === latestDate.getTime()
    );

    return apiSuccess(
      {
        date: latestDate.toISOString().split("T")[0],
        sectors: latestScores.map((s) => ({
          sector: s.sector,
          score: s.score?.toString(),
          components: s.componentsJson,
        })),
      },
      "Sector scoring engine"
    );
  } catch (error) {
    console.error("Error fetching sector scores:", error);
    return apiError("Failed to fetch sector scores", 500);
  }
}
