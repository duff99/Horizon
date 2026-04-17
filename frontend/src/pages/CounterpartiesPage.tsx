import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCounterparties, updateCounterparty } from "../api/counterparties";

type Status = "pending" | "active" | "ignored";

const LABEL: Record<Status, string> = {
  pending: "À valider",
  active: "Actives",
  ignored: "Ignorées",
};

export function CounterpartiesPage() {
  const [tab, setTab] = useState<Status>("pending");
  const qc = useQueryClient();

  const { data = [] } = useQuery({
    queryKey: ["counterparties", tab],
    queryFn: () => fetchCounterparties(tab),
  });

  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: "active" | "ignored" }) =>
      updateCounterparty(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["counterparties"] }),
  });

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">Contreparties</h1>

      <div className="flex gap-2 border-b">
        {(Object.keys(LABEL) as Status[]).map((s) => (
          <button
            key={s}
            onClick={() => setTab(s)}
            className={`px-4 py-2 text-sm ${
              tab === s ? "border-b-2 border-primary font-medium" : "text-muted-foreground"
            }`}
          >
            {LABEL[s]}
          </button>
        ))}
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left">
            <th className="py-2">Nom</th>
            <th className="text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.map((cp) => (
            <tr key={cp.id} className="border-b">
              <td className="py-2">{cp.name}</td>
              <td className="text-right space-x-2">
                {cp.status === "pending" && (
                  <>
                    <button
                      onClick={() => mutation.mutate({ id: cp.id, status: "active" })}
                      className="rounded-md bg-primary px-3 py-1 text-xs text-primary-foreground"
                    >
                      Valider
                    </button>
                    <button
                      onClick={() => mutation.mutate({ id: cp.id, status: "ignored" })}
                      className="rounded-md border px-3 py-1 text-xs"
                    >
                      Ignorer
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Aucune contrepartie {LABEL[tab].toLowerCase()}.
        </p>
      )}
    </div>
  );
}
