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
      include: {
        nlp: true,
      },
    });

    const eventsWithNlp = events.filter((e) => e.nlp);

    return apiSuccess(
      {
        range: { from: from.toISOString(), to: to.toISOString() },
        count: eventsWithNlp.length,
        events: eventsWithNlp.map((e) => ({
          id: e.id.toString(),
          ticker: e.ticker,
          datetime: e.dt?.toISOString(),
          type: e.type,
          title: e.title,
          nlp: {
            sentiment: e.nlp!.sentiment,
            guidance: e.nlp!.guidance,
            surpriseEps: e.nlp!.surpriseEps,
            topics: e.nlp!.topics,
            quotes: e.nlp!.quotes,
            model: e.nlp!.model,
            version: e.nlp!.version,
          },
        })),
      },
      "FinBERT + LLM summarization"
    );
  } catch (error) {
    console.error("Error fetching event NLP:", error);
    return apiError("Failed to fetch event NLP", 500);
  }
}
