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

function SortableRow({
  rule, categories, onEdit, onDelete, canDelete,
}: {
  rule: Rule; categories: CategoryOption[];
  onEdit: (r: Rule) => void; onDelete: (r: Rule) => void; canDelete: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: rule.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };
  const cat = categories.find((c) => c.id === rule.category_id);
  return (
    <tr ref={setNodeRef} style={style} className="border-b">
      <td {...attributes} {...listeners} className="cursor-grab px-2">⋮⋮</td>
      <td className="px-2">{rule.priority}</td>
      <td className="px-2">
        {rule.name}
        {rule.is_system && (
          <Badge variant="secondary" className="ml-2">système</Badge>
        )}
      </td>
      <td className="px-2">{rule.label_operator} {rule.label_value}</td>
      <td className="px-2">{cat?.name ?? `#${rule.category_id}`}</td>
      <td className="px-2 flex gap-2">
        <Button size="sm" variant="ghost" onClick={() => onEdit(rule)}>Éditer</Button>
        {canDelete && !rule.is_system && (
          <Button size="sm" variant="ghost" onClick={() => onDelete(rule)}>Supprimer</Button>
        )}
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
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="px-2 w-6"></th>
            <th className="px-2">Prio</th>
            <th className="px-2">Nom</th>
            <th className="px-2">Filtre</th>
            <th className="px-2">Catégorie</th>
            <th className="px-2">Actions</th>
          </tr>
        </thead>
        <SortableContext
          items={props.rules.map((r) => r.id)}
          strategy={verticalListSortingStrategy}
        >
          <tbody>
            {props.rules.map((rule) => (
              <SortableRow
                key={rule.id}
                rule={rule}
                categories={props.categories}
                onEdit={props.onEdit}
                onDelete={props.onDelete}
                canDelete={props.canDelete}
              />
            ))}
          </tbody>
        </SortableContext>
      </table>
    </DndContext>
  );
}
