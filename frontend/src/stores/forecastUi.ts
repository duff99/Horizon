import { create } from "zustand";

interface ForecastUiState {
  scenarioId: number | null;
  accountIds: number[] | null; // null = all accounts of entity
  setScenarioId: (id: number | null) => void;
  setAccountIds: (ids: number[] | null) => void;
}

export const useForecastUi = create<ForecastUiState>((set) => ({
  scenarioId: null,
  accountIds: null,
  setScenarioId: (id) => set({ scenarioId: id }),
  setAccountIds: (ids) => set({ accountIds: ids }),
}));
