import { NextRequest } from "next/server";
import { supabase } from "@/lib/supabase";
import { apiSuccess, apiError, getLatestDate } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const dateParam = searchParams.get("date");

  try {
    const targetDate = getLatestDate(dateParam);

    const { data: regime, error } = await supabase
      .from("macro_regime_daily")
      .select("*")
      .lte("date", targetDate.toISOString().split("T")[0])
      .order("date", { ascending: false })
      .limit(1)
      .single();

    if (error || !regime) {
      return apiError("No regime data available", 404);
    }

    return apiSuccess(
      {
        date: regime.date,
        regime: regime.regime,
        inputs: {
          growthZ: regime.growth_z,
          inflationZ: regime.inflation_z,
          liquidityZ: regime.liquidity_z,
          ratesZ: regime.rates_z,
        },
        details: regime.details_json,
      },
      "Regime classification engine"
    );
  } catch (error) {
    console.error("Error fetching regime:", error);
    return apiError("Failed to fetch regime", 500);
  }
}
