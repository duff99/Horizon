import type { DashboardPeriod, DashboardSummary } from "../types/api";

export async function fetchDashboardSummary(args: {
  period: DashboardPeriod;
  entityId?: number;
}): Promise<DashboardSummary> {
  const params = new URLSearchParams({ period: args.period });
  if (args.entityId !== undefined) {
    params.set("entity_id", String(args.entityId));
  }
  const resp = await fetch(`/api/dashboard/summary?${params}`, {
    credentials: "include",
  });
  if (!resp.ok) {
    throw new Error(`GET /api/dashboard/summary → ${resp.status}`);
  }
  return resp.json();
}
