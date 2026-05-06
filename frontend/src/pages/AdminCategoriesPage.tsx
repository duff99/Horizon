/**
 * AdminCategoriesPage — gestion des sous-catégories utilisateur.
 *
 * Affiche l'arborescence Racines → Sous-catégories. Permet à un
 * administrateur de créer une nouvelle sous-catégorie sous une racine
 * existante, de renommer une sous-catégorie utilisateur, ou de la
 * supprimer (uniquement si elle n'est plus référencée par des
 * transactions, des règles ou des sous-catégories).
 *
 * Les catégories système (seedées par les migrations) sont en lecture
 * seule : nom et couleur figés, suppression interdite.
 */
import { useMemo, useState } from "react";

import { useCategories } from "@/api/categories";
import {
  useCreateCategory,
  useDeleteCategory,
  useUpdateCategory,
} from "@/api/categoriesAdmin";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/api/client";

interface CreateState {
  parentId: number;
  name: string;
}

export function AdminCategoriesPage() {
  const categoriesQuery = useCategories();
  const createMut = useCreateCategory();
  const updateMut = useUpdateCategory();
  const deleteMut = useDeleteCategory();

  const [createState, setCreateState] = useState<CreateState | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const categories = categoriesQuery.data ?? [];
  const grouped = useMemo(() => {
    const roots = categories
      .filter((c) => c.parent_category_id === null)
      .sort((a, b) => a.name.localeCompare(b.name, "fr"));
    return roots.map((root) => ({
      root,
      children: categories
        .filter((c) => c.parent_category_id === root.id)
        .sort((a, b) => a.name.localeCompare(b.name, "fr")),
    }));
  }, [categories]);

  function clearError() {
    setError(null);
  }

  async function handleCreate() {
    if (!createState) return;
    const trimmed = createState.name.trim();
    if (!trimmed) {
      setError("Saisissez un nom de catégorie.");
      return;
    }
    try {
      await createMut.mutateAsync({
        name: trimmed,
        parent_category_id: createState.parentId,
      });
      setCreateState(null);
      clearError();
    } catch (e) {
      setError(formatError(e));
    }
  }

  async function handleEditCommit(id: number) {
    const trimmed = editName.trim();
    if (!trimmed) {
      setError("Le nom ne peut pas être vide.");
      return;
    }
    try {
      await updateMut.mutateAsync({ id, patch: { name: trimmed } });
      setEditId(null);
      clearError();
    } catch (e) {
      setError(formatError(e));
    }
  }

  async function handleDelete(id: number, name: string) {
    if (
      !window.confirm(
        `Supprimer la catégorie "${name}" ? Cette action est irréversible.`,
      )
    ) {
      return;
    }
    try {
      await deleteMut.mutateAsync({ id });
      clearError();
      return;
    } catch (e) {
      // Si le backend bloque parce que des transactions ou règles pointent
      // encore vers cette catégorie, il renvoie un 409 avec un payload
      // structuré décrivant les compteurs et la catégorie parente cible.
      // On propose alors une seconde confirmation pour cascader la
      // reclassification vers le parent puis supprimer en un seul appel.
      if (
        e instanceof ApiError &&
        e.status === 409 &&
        e.data?.code === "REFS_BLOCKING"
      ) {
        const tx = Number(e.data.tx_count ?? 0);
        const rl = Number(e.data.rule_count ?? 0);
        const parentName =
          typeof e.data.parent_name === "string" ? e.data.parent_name : null;
        const bits: string[] = [];
        if (tx > 0) bits.push(`${tx} transaction${tx > 1 ? "s" : ""}`);
        if (rl > 0) bits.push(`${rl} règle${rl > 1 ? "s" : ""}`);
        const target = parentName ?? "la catégorie parente";
        const msg =
          `Cette catégorie est encore référencée par ${bits.join(" et ")}.\n\n` +
          `Les déplacer vers « ${target} » puis supprimer "${name}" ?`;
        if (!window.confirm(msg)) {
          setError(
            "Suppression annulée. Reclassez manuellement les références " +
              "ou choisissez de les déplacer vers la catégorie parente.",
          );
          return;
        }
        try {
          await deleteMut.mutateAsync({ id, reassign_to_parent: true });
          clearError();
          return;
        } catch (e2) {
          setError(formatError(e2));
          return;
        }
      }
      setError(formatError(e));
    }
  }

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 p-6">
      <header>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">
          Catégories
        </h1>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          Personnalisez l'arborescence des catégories : ajoutez des
          sous-catégories propres à votre activité (ex : « SolarFacility »
          sous Charges externes), renommez ou supprimez vos catégories
          utilisateur. Les catégories système restent en lecture seule.
        </p>
      </header>

      {error && (
        <div
          role="alert"
          className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-[13px] text-rose-900"
        >
          {error}
        </div>
      )}

      {categoriesQuery.isLoading ? (
        <div className="text-[13px] text-muted-foreground">Chargement…</div>
      ) : (
        <div className="space-y-5">
          {grouped.map(({ root, children }) => {
            const isCreatingHere = createState?.parentId === root.id;
            return (
              <section
                key={root.id}
                className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card"
              >
                <header className="flex items-center justify-between border-b border-line-soft bg-panel-2 px-5 py-3">
                  <div className="text-[14px] font-semibold text-ink">
                    {root.name}
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      setCreateState({ parentId: root.id, name: "" })
                    }
                  >
                    Ajouter une sous-catégorie
                  </Button>
                </header>
                <ul className="divide-y divide-line-soft">
                  {isCreatingHere && (
                    <li className="flex items-center gap-2 bg-emerald-50/40 px-5 py-2.5">
                      <Label
                        htmlFor={`new-cat-${root.id}`}
                        className="sr-only"
                      >
                        Nom de la nouvelle sous-catégorie
                      </Label>
                      <Input
                        id={`new-cat-${root.id}`}
                        autoFocus
                        value={createState.name}
                        onChange={(e) =>
                          setCreateState((s) =>
                            s ? { ...s, name: e.target.value } : s,
                          )
                        }
                        placeholder="Nom (ex : SolarFacility)"
                      />
                      <Button
                        size="sm"
                        onClick={handleCreate}
                        disabled={createMut.isPending}
                      >
                        {createMut.isPending ? "…" : "Créer"}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setCreateState(null);
                          clearError();
                        }}
                      >
                        Annuler
                      </Button>
                    </li>
                  )}
                  {children.length === 0 && !isCreatingHere && (
                    <li className="px-5 py-3 text-[12.5px] text-muted-foreground">
                      Aucune sous-catégorie pour l'instant.
                    </li>
                  )}
                  {children.map((c) => {
                    const isSystem = c.is_system !== false;
                    const isEditing = editId === c.id;
                    return (
                      <li
                        key={c.id}
                        className="flex items-center justify-between gap-3 px-5 py-2"
                      >
                        {isEditing ? (
                          <div className="flex flex-1 items-center gap-2">
                            <Input
                              autoFocus
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                            />
                            <Button
                              size="sm"
                              onClick={() => handleEditCommit(c.id)}
                              disabled={updateMut.isPending}
                            >
                              Enregistrer
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setEditId(null);
                                clearError();
                              }}
                            >
                              Annuler
                            </Button>
                          </div>
                        ) : (
                          <>
                            <div className="flex items-center gap-2 text-[13px] text-ink">
                              <span>{c.name}</span>
                              {isSystem && (
                                <span className="inline-flex items-center rounded-sm bg-slate-100 px-1.5 py-0.5 text-[10.5px] font-medium uppercase tracking-wider text-slate-600">
                                  Système
                                </span>
                              )}
                            </div>
                            {!isSystem && (
                              <div className="flex items-center gap-1">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => {
                                    setEditId(c.id);
                                    setEditName(c.name);
                                    clearError();
                                  }}
                                >
                                  Renommer
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleDelete(c.id, c.name)}
                                  disabled={deleteMut.isPending}
                                >
                                  Supprimer
                                </Button>
                              </div>
                            )}
                          </>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}

function formatError(e: unknown): string {
  if (e instanceof ApiError) return e.detail;
  if (e instanceof Error) return e.message;
  return "Erreur inconnue";
}
