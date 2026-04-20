export type UserRole = 'admin' | 'reader';

export type Me = {
  id: number;
  email: string;
  role: UserRole;
  fullName: string | null;
  isActive: boolean;
  createdAt: string;
  lastLoginAt: string | null;
};

export type Entity = {
  id: number;
  name: string;
  legalName: string;
  siret: string | null;
  parentEntityId: number | null;
  createdAt: string;
};

export type BankAccount = {
  id: number;
  entityId: number;
  name: string;
  iban: string;
  bic: string | null;
  bankName: string;
  bankCode: string;
  currency: string;
  isActive: boolean;
  createdAt: string;
};

export type ImportStatus = "pending" | "completed" | "failed";

// NOTE: tous les IDs exposés par l'API FastAPI sont des entiers (int).
// TypeScript les reçoit donc en `number` après JSON.parse.
export interface ImportRecord {
  id: number;
  bank_account_id: number;
  bank_code: string;
  status: ImportStatus;
  filename: string | null;
  file_sha256: string | null;
  imported_count: number;
  duplicates_skipped: number;
  counterparties_pending_created: number;
  period_start: string | null;
  period_end: string | null;
  opening_balance: string | null;
  closing_balance: string | null;
  error_message: string | null;
  created_at: string | null;
}

export interface CounterpartyNested {
  id: number;
  name: string;
  status: "pending" | "active" | "ignored";
}

export interface CategoryNested {
  id: number;
  name: string;
}

export interface Transaction {
  id: number;
  operation_date: string;
  value_date: string;
  label: string;
  raw_label: string;
  amount: string; // Decimal en string
  is_aggregation_parent: boolean;
  parent_transaction_id: number | null;
  counterparty: CounterpartyNested | null;
  category: CategoryNested | null;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  per_page: number;
}

export interface TransactionFilter {
  bank_account_id?: number;
  date_from?: string;
  date_to?: string;
  counterparty_id?: number;
  search?: string;
  page?: number;
  per_page?: number;
  uncategorized?: boolean;
}

export interface Counterparty {
  id: number;
  entity_id: number;
  name: string;
  status: "pending" | "active" | "ignored";
}

export type DashboardPeriod =
  | "current_month"
  | "previous_month"
  | "last_30d"
  | "last_90d";

export interface DailyCashflow {
  date: string;
  inflows: string;
  outflows: string;
}

export interface DashboardSummary {
  period: DashboardPeriod;
  period_label: string;
  period_start: string;
  period_end: string;
  total_balance: string;
  total_balance_asof: string | null;
  inflows: string;
  outflows: string;
  uncategorized_count: number;
  daily: DailyCashflow[];
}
