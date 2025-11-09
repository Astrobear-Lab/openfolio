import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { apiSuccess, apiError } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const dateParam = searchParams.get("date");
  const stage = searchParams.get("stage");

  try {
    const where: any = {};

    if (dateParam) {
      where.date = new Date(dateParam);
    }

    if (stage) {
      where.stage = stage;
    }

    const logs = await prisma.decisionLog.findMany({
      where,
      orderBy: [{ date: "desc" }, { stage: "asc" }],
      take: 100,
    });

    return apiSuccess(
      {
        count: logs.length,
        logs: logs.map((l) => ({
          date: l.date.toISOString().split("T")[0],
          stage: l.stage,
          agent: l.agent,
          inputRef: l.inputRef,
          computedRef: l.computedRef,
          decision: l.decision,
          rationale: l.rationaleMd,
        })),
      },
      "Decision logs"
    );
  } catch (error) {
    console.error("Error fetching decision logs:", error);
    return apiError("Failed to fetch decision logs", 500);
  }
}
