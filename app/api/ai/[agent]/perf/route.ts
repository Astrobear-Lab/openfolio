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

    const performance = await prisma.aiPerformance.findMany({
      where: {
        agentId: agent.id,
        date: {
          gte: from,
          lte: to,
        },
      },
      orderBy: { date: "desc" },
      take: 1000,
    });

    return apiSuccess(
      {
        agent: agentName,
        range: { from: from.toISOString(), to: to.toISOString() },
        count: performance.length,
        performance: performance.map((p) => ({
          date: p.date.toISOString().split("T")[0],
          nav: p.nav?.toString(),
          cashWeight: p.cashWeight?.toString(),
          pnlDaily: p.pnlDaily?.toString(),
          sharpe: p.sharpe?.toString(),
          mdd: p.mdd?.toString(),
          benchmarkReturn: p.benchmarkReturn?.toString(),
        })),
      },
      `AI Agent Performance: ${agentName}`
    );
  } catch (error) {
    console.error("Error fetching AI performance:", error);
    return apiError("Failed to fetch AI performance", 500);
  }
}
