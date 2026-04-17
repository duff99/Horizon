import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchTransactions } from "../api/transactions";
import { TransactionFilters } from "../components/TransactionFilters";
import type { TransactionFilter } from "../types/api";

const EUR = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
});

export function TransactionsPage() {
  const [filters, setFilters] = useState<TransactionFilter>({ page: 1, per_page: 50 });
  const { data, isLoading } = useQuery({
    queryKey: ["transactions", filters],
    queryFn: () => fetchTransactions(filters),
  });

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">Transactions</h1>
      <TransactionFilters value={filters} onChange={setFilters} />

      {isLoading && <p>Chargement…</p>}

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="py-2">Date</th>
            <th>Libellé</th>
            <th>Contrepartie</th>
            <th>Catégorie</th>
            <th className="text-right">Montant</th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((tx) => (
            <tr
              key={tx.id}
              className={`border-b ${tx.is_aggregation_parent ? "bg-muted/30 font-medium" : ""}`}
            >
              <td className="py-2">
                {new Date(tx.operation_date).toLocaleDateString("fr-FR")}
              </td>
              <td>{tx.label}</td>
              <td>{tx.counterparty?.name ?? "—"}</td>
              <td>{tx.category?.name ?? "Non catégorisée"}</td>
              <td className={`text-right ${parseFloat(tx.amount) < 0 ? "text-destructive" : "text-emerald-700"}`}>
                {EUR.format(parseFloat(tx.amount))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data && (
        <div className="flex items-center justify-between text-sm">
          <span>
            {data.total} transaction(s) — page {data.page}
          </span>
          <div className="flex gap-2">
            <button
              disabled={data.page <= 1}
              onClick={() => setFilters({ ...filters, page: data.page - 1 })}
              className="rounded-md border px-3 py-1 disabled:opacity-40"
            >
              Précédent
            </button>
            <button
              disabled={data.page * data.per_page >= data.total}
              onClick={() => setFilters({ ...filters, page: data.page + 1 })}
              className="rounded-md border px-3 py-1 disabled:opacity-40"
            >
              Suivant
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
