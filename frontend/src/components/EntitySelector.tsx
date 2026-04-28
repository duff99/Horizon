import { useEntities } from '@/api/entities';
import { useEntityFilter } from '@/stores/entityFilter';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface EntitySelectorProps {
  /**
   * Si false, masque l'option "Toutes les sociétés" — l'utilisateur DOIT
   * choisir une entité unique. À utiliser sur les pages où une vue agrégée
   * cross-entité n'a pas de sens métier (Analyse, Prévisionnel : KPI par
   * business, contextes financiers indépendants).
   * Default true (Dashboard, Transactions, etc.).
   */
  allowAll?: boolean;
}

export function EntitySelector({ allowAll = true }: EntitySelectorProps = {}) {
  const entitiesQuery = useEntities();
  const entityId = useEntityFilter((s) => s.entityId);
  const setEntityId = useEntityFilter((s) => s.setEntityId);
  const entities = entitiesQuery.data ?? [];

  const value = entityId === null ? 'all' : String(entityId);
  const placeholder = allowAll ? 'Toutes les sociétés' : 'Choisir une société';

  return (
    <Select
      value={value}
      onValueChange={(v) => setEntityId(v === 'all' ? null : Number(v))}
    >
      <SelectTrigger
        aria-label="Société"
        className="h-9 w-[210px] gap-2 rounded-md border-line-soft bg-panel px-3 text-[12.5px] font-medium text-ink shadow-card focus:ring-1 focus:ring-accent/40"
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
            <path d="M3 21h18" />
            <path d="M5 21V7l8-4v18" />
            <path d="M19 21V11l-6-4" />
            <path d="M9 9v.01" />
            <path d="M9 13v.01" />
            <path d="M9 17v.01" />
          </svg>
        </span>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent align="end">
        {allowAll && <SelectItem value="all">Toutes les sociétés</SelectItem>}
        {entities.map((e) => (
          <SelectItem key={e.id} value={String(e.id)}>
            {e.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
