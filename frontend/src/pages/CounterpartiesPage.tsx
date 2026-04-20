import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCounterparties, updateCounterparty } from "../api/counterparties";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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
    <section className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">
          Tiers
        </h1>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          Validez ou ignorez les tiers (clients, fournisseurs…) détectés lors des imports.
        </p>
      </div>

      <div className="flex gap-1 border-b border-line-soft">
        {(Object.keys(LABEL) as Status[]).map((s) => (
          <button
            key={s}
            onClick={() => setTab(s)}
            className={cn(
              "relative px-4 py-2 text-[13px] font-medium transition-colors",
              tab === s
                ? "text-ink"
                : "text-muted-foreground hover:text-ink-2"
            )}
          >
            {LABEL[s]}
            {tab === s && (
              <span className="absolute inset-x-0 -bottom-px h-0.5 bg-accent" />
            )}
          </button>
        ))}
      </div>

      {data.length === 0 ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Aucun tiers {LABEL[tab].toLowerCase()}.
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
          <table className="w-full">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2">
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Nom
                </th>
                <th className="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {data.map((cp) => (
                <tr
                  key={cp.id}
                  className="border-b border-line-soft transition-colors hover:bg-panel-2"
                >
                  <td className="px-4 py-3 text-[13px] font-medium text-ink">
                    {cp.name}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {cp.status === "pending" && (
                      <div className="flex justify-end gap-1">
                        <Button
                          size="sm"
                          onClick={() =>
                            mutation.mutate({ id: cp.id, status: "active" })
                          }
                        >
                          Valider
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            mutation.mutate({ id: cp.id, status: "ignored" })
                          }
                        >
                          Ignorer
                        </Button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
