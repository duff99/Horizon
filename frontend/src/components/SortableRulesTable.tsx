import { DndContext, closestCenter, type DragEndEvent } from "@dnd-kit/core";
import {
  SortableContext, useSortable, verticalListSortingStrategy, arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Rule } from "@/api/rules";
import type { CategoryOption } from "./CategoryCombobox";

interface Props {
  rules: Rule[];
  categories: CategoryOption[];
  onReorder: (reordered: Array<{ id: number; priority: number }>) => void;
  onEdit: (rule: Rule) => void;
  onDelete: (rule: Rule) => void;
  canDelete: boolean;
}

function operatorLabel(op: string) {
  const map: Record<string, string> = {
    contains: "contient",
    equals: "=",
    starts_with: "commence par",
    ends_with: "finit par",
    regex: "regex",
  };
  return map[op] ?? op;
}

function SortableRow({
  rule, categories, onEdit, onDelete, canDelete,
}: {
  rule: Rule; categories: CategoryOption[];
  onEdit: (r: Rule) => void; onDelete: (r: Rule) => void; canDelete: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: rule.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };
  const cat = categories.find((c) => c.id === rule.category_id);
  return (
    <tr
      ref={setNodeRef}
      style={style}
      className="border-b border-line-soft transition-colors hover:bg-panel-2"
    >
      <td
        {...attributes}
        {...listeners}
        className="w-[38px] cursor-grab select-none px-4 py-3 text-center text-[15px] text-muted-foreground hover:text-ink-2 active:cursor-grabbing"
        aria-label="Glisser pour réordonner"
      >
        ⋮⋮
      </td>
      <td className="px-3 py-3 text-[12.5px] font-mono tabular-nums text-muted-foreground">
        {rule.priority}
      </td>
      <td className="px-3 py-3 text-[13.5px]">
        <div className="font-medium text-ink">{rule.name}</div>
        {rule.is_system && (
          <Badge
            variant="secondary"
            className="mt-1 h-[18px] border-line-soft bg-panel-2 px-2 text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground"
          >
            Système
          </Badge>
        )}
      </td>
      <td className="px-3 py-3 text-[12.5px]">
        <span className="inline-flex items-center gap-1.5 rounded-md border border-line-soft bg-panel-2 px-2 py-0.5 font-mono text-[11.5px] text-ink-2">
          <span className="text-muted-foreground">{operatorLabel(rule.label_operator ?? "")}</span>
          <span className="font-semibold text-ink">« {rule.label_value ?? ""} »</span>
        </span>
      </td>
      <td className="px-3 py-3 text-[13px]">
        <span className="inline-flex items-center gap-1.5 rounded-md border border-line-soft bg-panel-2 px-2 py-0.5 text-[12px] font-medium text-ink-2">
          <span className="h-2 w-2 rounded-sm bg-slate-400" />
          {cat?.name ?? `#${rule.category_id}`}
        </span>
      </td>
      <td className="px-3 py-3 text-right">
        <div className="flex justify-end gap-1">
          <Button size="sm" variant="ghost" onClick={() => onEdit(rule)}>
            Éditer
          </Button>
          {canDelete && !rule.is_system && (
            <Button
              size="sm"
              variant="ghost"
              className="text-debit hover:text-debit"
              onClick={() => onDelete(rule)}
            >
              Supprimer
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
}

export function SortableRulesTable(props: Props) {
  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = props.rules.findIndex((r) => r.id === active.id);
    const newIndex = props.rules.findIndex((r) => r.id === over.id);
    const moved = arrayMove(props.rules, oldIndex, newIndex);
    const reordered = moved.map((r, idx) => ({
      id: r.id,
      priority: (idx + 1) * 10 + 100000,
    }));
    props.onReorder(reordered);
  }

  return (
    <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
        <table className="w-full">
          <thead>
            <tr className="border-b border-line-soft bg-panel-2">
              <th className="w-[38px] px-4 py-2.5" aria-label="réorg."></th>
              <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Prio
              </th>
              <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Nom
              </th>
              <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Condition
              </th>
              <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Catégorie
              </th>
              <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Actions
              </th>
            </tr>
          </thead>
          <SortableContext
            items={props.rules.map((r) => r.id)}
            strategy={verticalListSortingStrategy}
          >
            <tbody>
              {props.rules.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-10 text-center text-[13px] text-muted-foreground">
                    Aucune règle. Cliquez sur « Nouvelle règle » pour commencer.
                  </td>
                </tr>
              ) : (
                props.rules.map((rule) => (
                  <SortableRow
                    key={rule.id}
                    rule={rule}
                    categories={props.categories}
                    onEdit={props.onEdit}
                    onDelete={props.onDelete}
                    canDelete={props.canDelete}
                  />
                ))
              )}
            </tbody>
          </SortableContext>
        </table>
      </div>
    </DndContext>
  );
}
