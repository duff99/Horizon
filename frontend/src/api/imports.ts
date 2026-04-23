import type { ImportRecord } from "../types/api";

const DEFAULT_OPTIONS: RequestInit = { credentials: "include" };

export async function fetchImports(
  args: { entityId?: number | null; from?: string; to?: string } = {},
): Promise<ImportRecord[]> {
  const params = new URLSearchParams();
  if (args.entityId != null) params.set("entity_id", String(args.entityId));
  if (args.from) params.set("from", args.from);
  if (args.to) params.set("to", args.to);
  const qs = params.toString() ? `?${params}` : "";
  const resp = await fetch(`/api/imports${qs}`, DEFAULT_OPTIONS);
  if (!resp.ok) throw new Error(`GET /api/imports → ${resp.status}`);
  return resp.json();
}

export async function fetchImport(id: number): Promise<ImportRecord> {
  const resp = await fetch(`/api/imports/${id}`, DEFAULT_OPTIONS);
  if (!resp.ok) throw new Error(`GET /api/imports/${id} → ${resp.status}`);
  return resp.json();
}

export async function uploadImport(args: {
  bankAccountId: number;
  file: File;
  overrideDuplicates?: boolean;
}): Promise<ImportRecord> {
  const body = new FormData();
  body.append("bank_account_id", String(args.bankAccountId));
  body.append("file", args.file);
  if (args.overrideDuplicates) body.append("override_duplicates", "true");
  const resp = await fetch("/api/imports", {
    method: "POST",
    credentials: "include",
    body,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail ?? `Erreur ${resp.status}`);
  }
  return resp.json();
}
