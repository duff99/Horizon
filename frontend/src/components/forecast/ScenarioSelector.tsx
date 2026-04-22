import { useEffect } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  useCreateScenario,
  useDeleteScenario,
  useScenarios,
  useUpdateScenario,
} from "@/api/forecastScenarios";
import { useForecastUi } from "@/stores/forecastUi";

interface Props {
  entityId: number | null;
}

export function ScenarioSelector({ entityId }: Props) {
  const { data: scenarios = [], isLoading } = useScenarios(entityId);
  const scenarioId = useForecastUi((s) => s.scenarioId);
  const setScenarioId = useForecastUi((s) => s.setScenarioId);

  const createMut = useCreateScenario();
  const updateMut = useUpdateScenario();
  const deleteMut = useDeleteScenario();

  // Initialize active scenario : default or first available
  useEffect(() => {
    if (scenarios.length === 0) return;
    if (scenarioId != null && scenarios.some((s) => s.id === scenarioId)) {
      return; // already valid
    }
    const def =
      scenarios.find((s) => s.is_default) ?? scenarios[0];
    if (def) setScenarioId(def.id);
  }, [scenarios, scenarioId, setScenarioId]);

  const active = scenarios.find((s) => s.id === scenarioId);

  function handleCreate() {
    if (entityId == null) return;
    // eslint-disable-next-line no-alert
    const name = window.prompt("Nom du nouveau scénario");
    if (!name || !name.trim()) return;
    createMut.mutate(
      {
        entity_id: entityId,
        name: name.trim(),
        is_default: scenarios.length === 0,
      },
      {
        onSuccess: (sc) => {
          setScenarioId(sc.id);
        },
      },
    );
  }

  function handleRename() {
    if (!active) return;
    // eslint-disable-next-line no-alert
    const name = window.prompt("Nouveau nom du scénario", active.name);
    if (!name || !name.trim() || name === active.name) return;
    updateMut.mutate({ id: active.id, name: name.trim() });
  }

  function handleDelete() {
    if (!active) return;
    // eslint-disable-next-line no-alert
    const ok = window.confirm(
      `Supprimer le scénario "${active.name}" ? Cette action est irréversible.`,
    );
    if (!ok) return;
    deleteMut.mutate(active.id, {
      onSuccess: () => {
        const other = scenarios.find((s) => s.id !== active.id);
        setScenarioId(other?.id ?? null);
      },
    });
  }

  return (
    <div className="flex items-center gap-1">
      <Select
        value={scenarioId != null ? String(scenarioId) : ""}
        onValueChange={(v) => setScenarioId(v ? Number(v) : null)}
        disabled={isLoading || scenarios.length === 0}
      >
        <SelectTrigger
          aria-label="Scénario"
          className="h-9 w-[200px] gap-2 rounded-md border-line-soft bg-panel px-3 text-[12.5px] font-medium text-ink shadow-card focus:ring-1 focus:ring-accent/40"
        >
          <span
            aria-hidden
            className="flex h-5 w-5 shrink-0 items-center justify-center rounded-[5px] bg-accent/10 text-accent"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.75}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-3 w-3"
            >
              <path d="M12 2v20" />
              <path d="M2 12h20" />
              <circle cx="12" cy="12" r="9" />
            </svg>
          </span>
          <SelectValue
            placeholder={
              scenarios.length === 0 ? "Aucun scénario" : "Choisir un scénario"
            }
          />
        </SelectTrigger>
        <SelectContent align="end">
          {scenarios.map((s) => (
            <SelectItem key={s.id} value={String(s.id)}>
              {s.name}
              {s.is_default ? " (défaut)" : ""}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Popover>
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-label="Actions scénario"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-line-soft bg-panel text-ink-2 shadow-card hover:text-ink focus:outline-none focus:ring-1 focus:ring-accent/40"
          >
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={1.75}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-4 w-4"
            >
              <circle cx="5" cy="12" r="1.25" />
              <circle cx="12" cy="12" r="1.25" />
              <circle cx="19" cy="12" r="1.25" />
            </svg>
          </button>
        </PopoverTrigger>
        <PopoverContent
          align="end"
          className="w-[220px] border-line-soft bg-panel p-1 shadow-card"
        >
          <button
            type="button"
            onClick={handleCreate}
            disabled={entityId == null}
            className="block w-full rounded-sm px-2.5 py-1.5 text-left text-[12.5px] text-ink hover:bg-panel-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Nouveau scénario…
          </button>
          <button
            type="button"
            onClick={handleRename}
            disabled={!active}
            className="block w-full rounded-sm px-2.5 py-1.5 text-left text-[12.5px] text-ink hover:bg-panel-2 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Renommer le scénario actif
          </button>
          <div className="my-1 border-t border-line-soft" />
          <button
            type="button"
            onClick={handleDelete}
            disabled={!active}
            className="block w-full rounded-sm px-2.5 py-1.5 text-left text-[12.5px] text-rose-700 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Supprimer
          </button>
        </PopoverContent>
      </Popover>
    </div>
  );
}
