import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { CategoryOption } from "@/components/CategoryCombobox";

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: () => apiFetch<CategoryOption[]>("/api/categories"),
  });
}
