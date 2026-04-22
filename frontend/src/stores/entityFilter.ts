import { create } from "zustand";
import { persist } from "zustand/middleware";

interface EntityFilterState {
  entityId: number | null;
  setEntityId: (id: number | null) => void;
}

export const useEntityFilter = create<EntityFilterState>()(
  persist(
    (set) => ({
      entityId: null,
      setEntityId: (id) => set({ entityId: id }),
    }),
    { name: "horizon:entityFilter" }
  )
);
