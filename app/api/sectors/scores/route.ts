import { NextRequest } from "next/server";
import { supabase } from "@/lib/supabase";
import { apiSuccess, apiError, getLatestDate } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const dateParam = searchParams.get("date");

  try {
    const targetDate = getLatestDate(dateParam);

    const { data: scores, error } = await supabase
      .from("sector_scores")
      .select("*")
      .lte("date", targetDate.toISOString().split("T")[0])
      .order("date", { ascending: false })
      .order("score", { ascending: false })
      .limit(20);

    if (error || !scores || scores.length === 0) {
      return apiError("No sector scores available", 404);
    }

    const latestDate = scores[0].date;
    const latestScores = scores.filter((s) => s.date === latestDate);

    return apiSuccess(
      {
        date: latestDate,
        sectors: latestScores.map((s) => ({
          sector: s.sector,
          score: s.score,
          components: s.components_json,
        })),
      },
      "Sector scoring engine"
    );
  } catch (error) {
    console.error("Error fetching sector scores:", error);
    return apiError("Failed to fetch sector scores", 500);
  }
}
