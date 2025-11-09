import { NextRequest } from "next/server";
import { prisma } from "@/lib/prisma";
import { apiSuccess, apiError, parseRange } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const ticker = searchParams.get("ticker");
  const range = searchParams.get("range") || "30d";

  try {
    const { from, to } = parseRange(range);

    const where: any = {
      dt: {
        gte: from,
        lte: to,
      },
    };

    if (ticker) {
      where.ticker = ticker;
    }

    const events = await prisma.eventDoc.findMany({
      where,
      orderBy: { dt: "desc" },
      take: 100,
      select: {
        id: true,
        ticker: true,
        dt: true,
        type: true,
        url: true,
        title: true,
        body: true,
      },
    });

    return apiSuccess(
      {
        range: { from: from.toISOString(), to: to.toISOString() },
        count: events.length,
        events: events.map((e) => ({
          id: e.id.toString(),
          ticker: e.ticker,
          datetime: e.dt?.toISOString(),
          type: e.type,
          url: e.url,
          title: e.title,
          bodyPreview: e.body?.substring(0, 200),
        })),
      },
      "SEC EDGAR / IR feeds"
    );
  } catch (error) {
    console.error("Error fetching events:", error);
    return apiError("Failed to fetch events", 500);
  }
}
