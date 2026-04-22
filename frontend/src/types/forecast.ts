export type ForecastMethod =
  | "RECURRING_FIXED"
  | "AVG_3M"
  | "AVG_6M"
  | "AVG_12M"
  | "PREVIOUS_MONTH"
  | "SAME_MONTH_LAST_YEAR"
  | "BASED_ON_CATEGORY"
  | "FORMULA";

export interface Scenario {
  id: number;
  entity_id: number;
  name: string;
  description: string | null;
  is_default: boolean;
  created_at: string;
}

export interface ScenarioCreate {
  entity_id: number;
  name: string;
  description?: string | null;
  is_default?: boolean;
}

export interface ScenarioUpdate {
  name?: string;
  description?: string | null;
  is_default?: boolean;
}

export interface ForecastLine {
  id: number;
  scenario_id: number;
  entity_id: number;
  category_id: number;
  method: ForecastMethod;
  amount_cents: number | null;
  base_category_id: number | null;
  ratio: string | null; // Decimal serialized as string
  formula_expr: string | null;
  start_month: string | null;
  end_month: string | null;
  updated_at: string;
}

export interface LineUpsert {
  scenario_id: number;
  category_id: number;
  method: ForecastMethod;
  amount_cents?: number | null;
  base_category_id?: number | null;
  ratio?: string | null;
  formula_expr?: string | null;
  start_month?: string | null;
  end_month?: string | null;
}

export interface PivotCell {
  month: string;
  realized_cents: number;
  committed_cents: number;
  forecast_cents: number;
  total_cents: number;
  line_method: ForecastMethod | null;
  line_params: Record<string, unknown> | null;
}

export interface PivotRow {
  category_id: number;
  parent_id: number | null;
  label: string;
  level: number;
  direction: "in" | "out";
  cells: PivotCell[];
}

export interface PivotSeries {
  month: string;
  in_cents: number;
  out_cents: number;
}

export interface PivotResult {
  months: string[];
  opening_balance_cents: number;
  closing_balance_projection_cents: number[];
  rows: PivotRow[];
  realized_series: PivotSeries[];
  forecast_series: PivotSeries[];
}

export interface ValidateFormulaResponse {
  valid: boolean;
  error: string | null;
}
