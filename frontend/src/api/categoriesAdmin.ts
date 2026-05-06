/**
 * API admin pour la gestion des catégories utilisateur (création de
 * sous-catégories, renommage, suppression). Lecture via `useCategories`
 * (api/categories.ts) qui reste partagé entre tous les utilisateurs.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import type { CategoryOption } from "@/components/CategoryCombobox";

export interface CategoryCreatePayload {
  name: string;
  parent_category_id: number;
  color?: string | null;
}

export interface CategoryUpdatePayload {
  name?: string;
  color?: string | null;
}

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["categories"] });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (p: CategoryCreatePayload) =>
      apiFetch<CategoryOption>("/api/categories", {
        method: "POST",
        body: JSON.stringify(p),
      }),
    onSuccess: () => invalidate(qc),
  });
}

export function useUpdateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { id: number; patch: CategoryUpdatePayload }) =>
      apiFetch<CategoryOption>(`/api/categories/${input.id}`, {
        method: "PATCH",
        body: JSON.stringify(input.patch),
      }),
    onSuccess: () => invalidate(qc),
  });
}

export interface CategoryDeleteInput {
  id: number;
  /**
   * Si true, demande au backend de reclasser les transactions et règles
   * référençant cette catégorie vers la catégorie parente avant de la
   * supprimer. Sans ce flag, le backend renvoie 409 quand des références
   * existent (avec un payload structuré que la page Admin utilise pour
   * afficher une confirmation détaillée).
   */
  reassign_to_parent?: boolean;
}

export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reassign_to_parent }: CategoryDeleteInput) => {
      const qs = reassign_to_parent ? "?reassign_to_parent=true" : "";
      return apiFetch<void>(`/api/categories/${id}${qs}`, { method: "DELETE" });
    },
    onSuccess: () => invalidate(qc),
  });
}
