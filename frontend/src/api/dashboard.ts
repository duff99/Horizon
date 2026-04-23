import type {
  Alert,
  BankAccountBalance,
  CategoryBreakdown,
  DashboardPeriod,
  DashboardSummary,
  TopCounterparties,
} from "../types/api";

interface BaseArgs {
  period?: DashboardPeriod;
  entityId?: number;
  from?: string;
  to?: string;
}

function buildParams(args: BaseArgs): URLSearchParams {
  const params = new URLSearchParams();
  if (args.period) params.set("period", args.period);
  if (args.entityId !== undefined) params.set("entity_id", String(args.entityId));
  if (args.from) params.set("from", args.from);
  if (args.to) params.set("to", args.to);
  return params;
}

async function getJson<T>(url: string): Promise<T> {
  const resp = await fetch(url, { credentials: "include" });
  if (!resp.ok) {
    throw new Error(`GET ${url} → ${resp.status}`);
  }
  return resp.json();
}

export function fetchDashboardSummary(args: {
  period?: DashboardPeriod;
  entityId?: number;
  from?: string;
  to?: string;
}): Promise<DashboardSummary> {
  return getJson(`/api/dashboard/summary?${buildParams(args)}`);
}

export function fetchBankBalances(args: {
  entityId?: number;
}): Promise<BankAccountBalance[]> {
  return getJson(`/api/dashboard/bank-balances?${buildParams(args)}`);
}

export function fetchCategoryBreakdown(args: {
  period?: DashboardPeriod;
  entityId?: number;
  from?: string;
  to?: string;
}): Promise<CategoryBreakdown> {
  return getJson(`/api/dashboard/categories?${buildParams(args)}`);
}

export function fetchTopCounterparties(args: {
  period?: DashboardPeriod;
  entityId?: number;
  from?: string;
  to?: string;
}): Promise<TopCounterparties> {
  return getJson(`/api/dashboard/top-counterparties?${buildParams(args)}`);
}

export function fetchAlerts(args: { entityId?: number }): Promise<Alert[]> {
  return getJson(`/api/dashboard/alerts?${buildParams(args)}`);
}
