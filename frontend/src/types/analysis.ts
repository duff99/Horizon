/**
 * Types miroir des endpoints `/api/analysis/*`.
 *
 * Tous les montants sont en centimes (int) sauf mention contraire.
 * Voir `backend/app/schemas/analysis.py` pour la source de vérité.
 */

// ---------------------------------------------------------------------------
// 1. Category drift
// ---------------------------------------------------------------------------

export interface CategoryDriftRow {
  category_id: number;
  label: string;
  current_cents: number;
  avg3m_cents: number;
  delta_cents: number;
  delta_pct: number;
  status: "alert" | "normal";
}

export interface CategoryDriftResponse {
  rows: CategoryDriftRow[];
  seuil_pct: number;
}

// ---------------------------------------------------------------------------
// 2. Top movers
// ---------------------------------------------------------------------------

export interface TopMoverRow {
  category_id: number;
  label: string;
  direction: "in" | "out";
  delta_cents: number;
  sparkline_3m_cents: number[];
}

export interface TopMoversResponse {
  increases: TopMoverRow[];
  decreases: TopMoverRow[];
}

// ---------------------------------------------------------------------------
// 3. Runway
// ---------------------------------------------------------------------------

export interface RunwayResponse {
  burn_rate_cents: number;
  current_balance_cents: number;
  runway_months: number | null;
  forecast_balance_6m_cents: number[];
  status: "critical" | "warning" | "ok" | "none";
}

// ---------------------------------------------------------------------------
// 4. Year-over-year
// ---------------------------------------------------------------------------

export interface YoYPoint {
  month: string; // "YYYY-MM"
  revenues_current: number;
  revenues_previous: number;
  expenses_current: number;
  expenses_previous: number;
}

export interface YoYResponse {
  months: string[];
  series: YoYPoint[];
}

// ---------------------------------------------------------------------------
// 5. Client concentration
// ---------------------------------------------------------------------------

export interface ClientSlice {
  counterparty_id: number | null;
  name: string;
  amount_cents: number;
  share_pct: number;
}

export interface ClientConcentrationResponse {
  total_revenue_cents: number;
  top5: ClientSlice[];
  others_cents: number;
  others_share_pct: number;
  hhi: number;
  risk_level: "low" | "medium" | "high";
}

// ---------------------------------------------------------------------------
// 6. Entities comparison
// ---------------------------------------------------------------------------

export interface EntityCompareRow {
  entity_id: number;
  name: string;
  revenues_cents: number;
  expenses_cents: number;
  net_variation_cents: number;
  current_balance_cents: number;
  burn_rate_cents: number;
  runway_months: number | null;
}

export interface EntitiesComparisonResponse {
  entities: EntityCompareRow[];
}
