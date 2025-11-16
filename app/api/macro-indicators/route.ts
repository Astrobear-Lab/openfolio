import { NextRequest } from "next/server";
import { supabase } from "@/lib/supabase";
import { apiSuccess, apiError, getLatestDate } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const dateParam = searchParams.get("date");

  try {
    const targetDate = getLatestDate(dateParam);

    // Get latest macro features (z-scores)
    const { data: features, error: featuresError } = await supabase
      .from("macro_features_daily")
      .select("*")
      .lte("date", targetDate.toISOString().split("T")[0])
      .order("date", { ascending: false })
      .limit(20); // Get multiple features

    if (featuresError) {
      return apiError("Failed to fetch macro features", 500);
    }

    // Get latest raw values from macro_points
    const { data: latestPoints, error: pointsError } = await supabase
      .from("macro_points")
      .select(`
        series_id,
        ts,
        value,
        macro_series!inner(code, name, source)
      `)
      .order("ts", { ascending: false });

    if (pointsError) {
      return apiError("Failed to fetch macro points", 500);
    }

    // Group latest points by series
    const latestValues: Record<string, any> = {};
    if (latestPoints) {
      for (const point of latestPoints) {
        const macroSeries = (point as any).macro_series;
        const code = macroSeries.code;
        if (!latestValues[code]) {
          latestValues[code] = {
            code,
            name: macroSeries.name,
            value: point.value,
            date: point.ts,
            source: macroSeries.source
          };
        }
      }
    }

    // Group features by type and get latest
    const latestFeatures: Record<string, any> = {};
    for (const feature of features) {
      if (!latestFeatures[feature.feature]) {
        latestFeatures[feature.feature] = {
          feature: feature.feature,
          value: feature.value,
          date: feature.date,
          details: feature.details_json
        };
      }
    }

    // Combine data
    const indicators = [];

    // Add growth indicators
    if (latestValues.INDPRO) {
      indicators.push({
        ...latestValues.INDPRO,
        zScore: latestFeatures.growth_indpro?.value || null,
        category: "growth"
      });
    }
    if (latestValues.PAYEMS) {
      indicators.push({
        ...latestValues.PAYEMS,
        zScore: latestFeatures.growth_payems?.value || null,
        category: "growth"
      });
    }
    if (latestValues.UNRATE) {
      indicators.push({
        ...latestValues.UNRATE,
        zScore: latestFeatures.growth_unrate?.value || null,
        category: "growth"
      });
    }

    // Add inflation indicators
    if (latestValues.CPIAUCSL) {
      indicators.push({
        ...latestValues.CPIAUCSL,
        zScore: latestFeatures.inflation_cpiaucsl?.value || null,
        category: "inflation"
      });
    }
    if (latestValues.CPILFESL) {
      indicators.push({
        ...latestValues.CPILFESL,
        zScore: latestFeatures.inflation_cpilfes1?.value || null,
        category: "inflation"
      });
    }

    // Add liquidity indicators
    if (latestValues.M2SL) {
      indicators.push({
        ...latestValues.M2SL,
        zScore: latestFeatures.liquidity_m2sl?.value || null,
        category: "liquidity"
      });
    }
    if (latestValues.WALCL) {
      indicators.push({
        ...latestValues.WALCL,
        zScore: latestFeatures.liquidity_walcl?.value || null,
        category: "liquidity"
      });
    }

    // Add rates indicators
    if (latestValues.DGS10) {
      indicators.push({
        ...latestValues.DGS10,
        zScore: latestFeatures.rates_dgs10?.value || null,
        category: "rates"
      });
    }
    if (latestValues.DGS2) {
      indicators.push({
        ...latestValues.DGS2,
        zScore: latestFeatures.rates_dgs2?.value || null,
        category: "rates"
      });
    }

    return apiSuccess(
      {
        indicators,
        latestDate: features[0]?.date || targetDate.toISOString().split("T")[0]
      },
      "Macro indicators with z-scores"
    );
  } catch (error) {
    console.error("Error fetching macro indicators:", error);
    return apiError("Failed to fetch macro indicators", 500);
  }
}
