import { NextRequest } from "next/server";
import { supabase } from "@/lib/supabase";
import { apiSuccess, apiError, getLatestDate } from "@/lib/api-utils";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const dateParam = searchParams.get("date");

  try {
    const targetDate = getLatestDate(dateParam);

    // Get all agents
    const { data: agents, error: agentsError } = await supabase
      .from("ai_agents")
      .select("*")
      .order("id", { ascending: true });

    if (agentsError || !agents) {
      return apiError("Failed to fetch agents", 500);
    }

    // Get latest weights
    const { data: weights, error: weightsError } = await supabase
      .from("ai_weights_history")
      .select("*")
      .lte("date", targetDate.toISOString().split("T")[0])
      .order("date", { ascending: false })
      .limit(1000);

    if (weightsError || !weights || weights.length === 0) {
      return apiError("No weight data available", 404);
    }

    const latestDate = weights[0].date;
    const latestWeights = weights.filter((w) => w.date === latestDate);

    // Group by agent
    const byAgent = agents.map((agent) => {
      const agentWeights = latestWeights
        .filter((w) => w.agent_id === agent.id)
        .reduce((acc, w) => {
          acc[w.ticker] = {
            weight: w.weight,
            reason: w.reason_json,
          };
          return acc;
        }, {} as Record<string, any>);

      return {
        agentId: agent.id,
        agentName: agent.name,
        riskProfile: agent.risk_profile,
        weights: agentWeights,
      };
    });

    return apiSuccess(
      {
        date: latestDate,
        agents: byAgent,
      },
      "AI Agents Comparison"
    );
  } catch (error) {
    console.error("Error comparing AI weights:", error);
    return apiError("Failed to compare AI weights", 500);
  }
}
