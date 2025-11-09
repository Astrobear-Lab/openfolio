import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { apiSuccess, apiError, parseRange } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const ticker = searchParams.get("ticker");
  const range = searchParams.get("range") || "1y";

  if (!ticker) {
    return apiError("Missing required parameter: ticker");
  }

  try {
    const { from, to } = parseRange(range);

    const taData = await prisma.taDaily.findMany({
      where: {
        ticker,
        date: {
          gte: from,
          lte: to,
        },
      },
      orderBy: { date: "desc" },
      take: 500,
    });

    return apiSuccess(
      {
        ticker,
        range: { from: from.toISOString(), to: to.toISOString() },
        count: taData.length,
        data: taData.map((ta) => ({
          date: ta.date.toISOString().split("T")[0],
          rsi14: ta.rsi14?.toString(),
          macd: ta.macd?.toString(),
          macdSignal: ta.macdSignal?.toString(),
          sma20: ta.sma20?.toString(),
          sma50: ta.sma50?.toString(),
          sma200: ta.sma200?.toString(),
          atr14: ta.atr14?.toString(),
          flags: ta.flags,
        })),
      },
      "Technical indicators engine"
    );
  } catch (error) {
    console.error("Error fetching TA data:", error);
    return apiError("Failed to fetch TA data", 500);
  }
}
