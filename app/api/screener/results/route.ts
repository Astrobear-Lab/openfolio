import { NextRequest } from "next/server";
import { supabase } from "@/lib/supabase";
import { apiSuccess, apiError, getLatestDate } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const dateParam = searchParams.get("date");

  try {
    const targetDate = getLatestDate(dateParam);

    // Get latest rankings
    const { data: rankings, error } = await supabase
      .from("rankings")
      .select("*")
      .lte("date", targetDate.toISOString().split("T")[0])
      .order("date", { ascending: false })
      .order("rank", { ascending: true })
      .limit(50); // Top 50 stocks

    if (error) {
      return apiError("Failed to fetch rankings", 500);
    }

    if (!rankings || rankings.length === 0) {
      return apiSuccess({
        rankings: [],
        date: targetDate.toISOString().split("T")[0],
        message: "No screening results available"
      }, "Stock screener results");
    }

    const latestDate = rankings[0].date;
    const latestRankings = rankings.filter((r) => r.date === latestDate);

    // Get company names mapping
    const tickers = latestRankings.map(r => r.ticker);
    const companyNames: Record<string, string> = {
      "AAPL": "Apple Inc.",
      "MSFT": "Microsoft Corp.",
      "GOOGL": "Alphabet Inc.",
      "AMZN": "Amazon.com Inc.",
      "NVDA": "NVIDIA Corp.",
      "TSLA": "Tesla Inc.",
      "META": "Meta Platforms Inc.",
      "JPM": "JPMorgan Chase & Co.",
      "JNJ": "Johnson & Johnson",
      "V": "Visa Inc.",
      "PG": "Procter & Gamble Co.",
      "UNH": "UnitedHealth Group Inc.",
      "HD": "Home Depot Inc.",
      "MA": "Mastercard Inc.",
      "XOM": "Exxon Mobil Corp.",
      "CVX": "Chevron Corp.",
      "KO": "Coca-Cola Co.",
      "PEP": "PepsiCo Inc.",
      "COST": "Costco Wholesale Corp.",
      "WMT": "Walmart Inc."
    };

    // Sector mapping
    const sectorMap: Record<string, string> = {
      "XLK": "Technology",
      "XLF": "Financials",
      "XLY": "Consumer Discretionary",
      "XLP": "Consumer Staples",
      "XLE": "Energy",
      "XLV": "Healthcare",
      "XLI": "Industrials",
      "XLB": "Materials",
      "XLU": "Utilities",
      "XLRE": "Real Estate",
      "XLC": "Communication Services"
    };

    // Transform rankings data
    const results = latestRankings.map((ranking) => {
      const details = ranking.details_json || {};

      return {
        ticker: ranking.ticker,
        name: companyNames[ranking.ticker] || ranking.ticker,
        sector: Object.keys(sectorMap).find(sector =>
          // This would need sector data, for now use a simple mapping
          ranking.ticker === "AAPL" || ranking.ticker === "MSFT" || ranking.ticker === "GOOGL" ||
          ranking.ticker === "AMZN" || ranking.ticker === "NVDA" || ranking.ticker === "TSLA" ||
          ranking.ticker === "META" ? "XLK" :
          ranking.ticker === "JPM" ? "XLF" :
          ranking.ticker === "XOM" || ranking.ticker === "CVX" ? "XLE" :
          ranking.ticker === "JNJ" || ranking.ticker === "UNH" ? "XLV" :
          ranking.ticker === "PG" || ranking.ticker === "KO" || ranking.ticker === "PEP" ||
          ranking.ticker === "COST" || ranking.ticker === "WMT" ? "XLP" :
          "XLY"
        ),
        rank: ranking.rank,
        totalScore: ranking.total_score,
        decision: ranking.decision,
        stagesPassed: ranking.stages_passed,
        qualityPass: details.quality?.pass || false,
        qualityScore: details.quality?.score || 0,
        valuePass: details.value?.pass || false,
        valueScore: details.value?.score || 0,
        eventPass: details.events?.pass || false,
        eventScore: details.events?.score || 0,
        taPass: details.technical?.pass || false,
        taScore: details.technical?.score || 0,
        details: details
      };
    });

    return apiSuccess(
      {
        rankings: results,
        date: latestDate,
        totalScreened: results.length,
        passedCount: results.filter(r => r.decision === "BUY").length,
        topScore: results.length > 0 ? results[0].totalScore : 0
      },
      "Stock screener results"
    );
  } catch (error) {
    console.error("Error fetching screener results:", error);
    return apiError("Failed to fetch screener results", 500);
  }
}
