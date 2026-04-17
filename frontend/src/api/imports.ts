import type { ImportRecord } from "../types/api";

const DEFAULT_OPTIONS: RequestInit = { credentials: "include" };

export async function fetchImports(): Promise<ImportRecord[]> {
  const resp = await fetch("/api/imports", DEFAULT_OPTIONS);
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
