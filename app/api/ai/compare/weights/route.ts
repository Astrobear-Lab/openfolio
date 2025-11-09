import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { apiSuccess, apiError, getLatestDate } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const dateParam = searchParams.get("date");

  try {
    const targetDate = getLatestDate(dateParam);

    const agents = await prisma.aiAgent.findMany({
      orderBy: { id: "asc" },
    });

    const weights = await prisma.aiWeightHistory.findMany({
      where: {
        date: {
          lte: targetDate,
        },
      },
      orderBy: { date: "desc" },
      take: 1000,
    });

    // Get latest date
    const latestDate = weights[0]?.date;
    if (!latestDate) {
      return apiError("No weight data available", 404);
    }

    const latestWeights = weights.filter(
      (w) => w.date.getTime() === latestDate.getTime()
    );

    // Group by agent
    const byAgent: Record<number, any> = {};
    agents.forEach((a) => {
      byAgent[a.id] = {
        agentId: a.id,
        agentName: a.name,
        riskProfile: a.riskProfile,
        weights: {},
      };
    });

    latestWeights.forEach((w) => {
      if (byAgent[w.agentId]) {
        byAgent[w.agentId].weights[w.ticker] = {
          weight: w.weight?.toString(),
          reason: w.reasonJson,
        };
      }
    });

    return apiSuccess(
      {
        date: latestDate.toISOString().split("T")[0],
        agents: Object.values(byAgent),
      },
      "AI Agents Comparison"
    );
  } catch (error) {
    console.error("Error comparing AI weights:", error);
    return apiError("Failed to compare AI weights", 500);
  }
}
