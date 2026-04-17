import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileDropzone } from "../components/FileDropzone";
import { uploadImport } from "../api/imports";
import type { ImportRecord } from "../types/api";

interface BankAccount {
  id: number;
  iban: string;
  name: string;
}

export function ImportNewPage() {
  const [selected, setSelected] = useState<number | "">("");
  const [result, setResult] = useState<ImportRecord | null>(null);

  const { data: accounts = [] } = useQuery({
    queryKey: ["bank-accounts"],
    queryFn: async () => {
      const r = await fetch("/api/bank-accounts", { credentials: "include" });
      return (await r.json()) as BankAccount[];
    },
  });

  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: (file: File) =>
      uploadImport({ bankAccountId: selected as number, file }),
    onSuccess: (rec) => {
      setResult(rec);
      qc.invalidateQueries({ queryKey: ["imports"] });
      qc.invalidateQueries({ queryKey: ["transactions"] });
    },
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">Importer un relevé bancaire</h1>

      <div className="space-y-2">
        <label className="text-sm font-medium">Compte bancaire</label>
        <select
          data-testid="bank-account-select"
          className="w-full rounded-md border px-3 py-2"
          value={selected}
          onChange={(e) => setSelected(e.target.value ? Number(e.target.value) : "")}
        >
          <option value="">— Sélectionner un compte —</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} ({a.iban})
            </option>
          ))}
        </select>
      </div>

      {selected && (
        <FileDropzone
          accept="application/pdf"
          onFileSelected={(f) => mutation.mutate(f)}
        />
      )}

      {mutation.isPending && (
        <p className="text-sm text-muted-foreground">Analyse en cours…</p>
      )}

      {mutation.isError && (
        <div className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
          Erreur : {(mutation.error as Error).message}
        </div>
      )}

      {result && (
        <div className="rounded-md border bg-muted/30 p-4">
          <h2 className="font-semibold">Import terminé</h2>
          <ul className="mt-2 space-y-1 text-sm">
            <li>✅ {result.imported_count} transaction(s) importée(s)</li>
            {result.duplicates_skipped > 0 && (
              <li>⏭️ {result.duplicates_skipped} doublon(s) ignoré(s)</li>
            )}
            {result.counterparties_pending_created > 0 && (
              <li>
                👥 {result.counterparties_pending_created} nouvelle(s) contrepartie(s) à valider
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
