import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { apiSuccess, apiError, parseRange } from "@/lib/api-utils";

export async function GET(
  request: NextRequest,
  { params }: { params: { agent: string } }
) {
  const searchParams = request.nextUrl.searchParams;
  const range = searchParams.get("range") || "2y";
  const agentName = params.agent;

  try {
    const agent = await prisma.aiAgent.findUnique({
      where: { name: agentName },
    });

    if (!agent) {
      return apiError(`Agent not found: ${agentName}`, 404);
    }

    const { from, to } = parseRange(range);

    const weights = await prisma.aiWeightHistory.findMany({
      where: {
        agentId: agent.id,
        date: {
          gte: from,
          lte: to,
        },
      },
      orderBy: [{ date: "desc" }, { ticker: "asc" }],
      take: 5000,
    });

    // Group by date
    const byDate: Record<string, any> = {};
    weights.forEach((w) => {
      const dateKey = w.date.toISOString().split("T")[0];
      if (!byDate[dateKey]) {
        byDate[dateKey] = { date: dateKey, weights: {} };
      }
      byDate[dateKey].weights[w.ticker] = {
        weight: w.weight?.toString(),
        reason: w.reasonJson,
      };
    });

    return apiSuccess(
      {
        agent: agentName,
        range: { from: from.toISOString(), to: to.toISOString() },
        history: Object.values(byDate),
      },
      `AI Agent: ${agentName}`
    );
  } catch (error) {
    console.error("Error fetching AI weights:", error);
    return apiError("Failed to fetch AI weights", 500);
  }
}
