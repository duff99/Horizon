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
    <section className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">
          Importer un relevé bancaire
        </h1>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          Déposez un PDF d'un compte bancaire pour extraire les transactions.
        </p>
      </div>

      <div className="space-y-4 rounded-xl border border-line-soft bg-panel p-6 shadow-card">
        <div className="space-y-1.5">
          <label className="text-[12.5px] font-medium text-ink-2">
            Compte bancaire
          </label>
          <select
            data-testid="bank-account-select"
            className="w-full rounded-md border border-line bg-panel px-3 py-2 text-[13px] text-ink outline-none focus:border-ink-2"
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
      </div>

      {mutation.isPending && (
        <div className="rounded-xl border border-line-soft bg-panel p-4 text-[13px] text-muted-foreground shadow-card">
          Analyse en cours…
        </div>
      )}

      {mutation.isError && (
        <div
          role="alert"
          className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
        >
          Erreur : {(mutation.error as Error).message}
        </div>
      )}

      {result && (
        <div className="rounded-xl border border-line-soft bg-panel p-5 shadow-card">
          <h2 className="text-[14px] font-semibold text-ink">Import terminé</h2>
          <ul className="mt-2 space-y-1 text-[13px] text-ink-2">
            <li>
              <span className="text-ink">
                {result.imported_count} transaction(s) importée(s)
              </span>
            </li>
            {result.duplicates_skipped > 0 && (
              <li>
                <span className="text-muted-foreground">
                  {result.duplicates_skipped} doublon(s) ignoré(s)
                </span>
              </li>
            )}
            {result.counterparties_pending_created > 0 && (
              <li>
                <span className="text-amber-700">
                  {result.counterparties_pending_created} nouveau(x) tiers à valider
                </span>
              </li>
            )}
          </ul>
        </div>
      )}
    </section>
  );
}
