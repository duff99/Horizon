import { useEntities } from '@/api/entities';
import { useEntityFilter } from '@/stores/entityFilter';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export function EntitySelector() {
  const entitiesQuery = useEntities();
  const entityId = useEntityFilter((s) => s.entityId);
  const setEntityId = useEntityFilter((s) => s.setEntityId);
  const entities = entitiesQuery.data ?? [];

  const value = entityId === null ? 'all' : String(entityId);

  return (
    <Select
      value={value}
      onValueChange={(v) => setEntityId(v === 'all' ? null : Number(v))}
    >
      <SelectTrigger className="w-[220px]">
        <SelectValue placeholder="Toutes les sociétés" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">Toutes les sociétés</SelectItem>
        {entities.map((e) => (
          <SelectItem key={e.id} value={String(e.id)}>
            {e.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
