import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { ApiError } from '@/api/client';
import { createEntity, deleteEntity, listEntities, updateEntity } from '@/api/entities';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { Entity } from '@/types/api';

function toTreeOrder(entities: Entity[]): Array<Entity & { depth: number }> {
  const byParent = new Map<number | null, Entity[]>();
  for (const e of entities) {
    const k = e.parentEntityId;
    if (!byParent.has(k)) byParent.set(k, []);
    byParent.get(k)!.push(e);
  }
  const out: Array<Entity & { depth: number }> = [];
  function walk(parentId: number | null, depth: number) {
    for (const e of (byParent.get(parentId) ?? []).sort((a, b) =>
      a.name.localeCompare(b.name, 'fr')
    )) {
      out.push({ ...e, depth });
      walk(e.id, depth + 1);
    }
  }
  walk(null, 0);
  return out;
}

export function AdminEntitiesPage() {
  const qc = useQueryClient();
  const { data: entities, isLoading } = useQuery({
    queryKey: ['entities'],
    queryFn: listEntities,
  });

  const [editingId, setEditingId] = useState<number | null>(null);
  const [name, setName] = useState('');
  const [legalName, setLegalName] = useState('');
  const [siret, setSiret] = useState('');
  const [parentId, setParentId] = useState<string>('none');
  const [formError, setFormError] = useState<string | null>(null);

  function resetForm() {
    setEditingId(null);
    setName('');
    setLegalName('');
    setSiret('');
    setParentId('none');
    setFormError(null);
  }

  function startEdit(e: Entity) {
    setEditingId(e.id);
    setName(e.name);
    setLegalName(e.legalName);
    setSiret(e.siret ?? '');
    setParentId(e.parentEntityId == null ? 'none' : String(e.parentEntityId));
    setFormError(null);
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  const create = useMutation({
    mutationFn: createEntity,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entities'] });
      resetForm();
    },
    onError: (e) => setFormError(e instanceof ApiError ? e.detail : 'Erreur'),
  });

  const update = useMutation({
    mutationFn: (input: { id: number; name: string; legalName: string; siret?: string; parentEntityId: number | null }) =>
      updateEntity(input.id, {
        name: input.name,
        legalName: input.legalName,
        siret: input.siret,
        parentEntityId: input.parentEntityId,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entities'] });
      resetForm();
    },
    onError: (e) => setFormError(e instanceof ApiError ? e.detail : 'Erreur'),
  });

  const del = useMutation({
    mutationFn: deleteEntity,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['entities'] }),
    onError: (e) => alert(e instanceof ApiError ? e.detail : 'Erreur'),
  });

  const ordered = entities ? toTreeOrder(entities) : [];
  const isEditing = editingId !== null;

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">
          Sociétés
        </h1>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          {ordered.length} société{ordered.length > 1 ? 's' : ''} enregistrée
          {ordered.length > 1 ? 's' : ''}
        </p>
      </div>

      <div className="rounded-xl border border-line-soft bg-panel p-6 shadow-card">
        <h2 className="text-[14px] font-semibold text-ink">
          {isEditing ? 'Modifier la société' : 'Créer une société'}
        </h2>
        <form
          className="mt-4 grid grid-cols-2 gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            const parent = parentId === 'none' ? null : Number(parentId);
            if (isEditing && editingId !== null) {
              update.mutate({
                id: editingId,
                name,
                legalName,
                siret: siret || undefined,
                parentEntityId: parent,
              });
            } else {
              create.mutate({
                name,
                legalName,
                siret: siret || undefined,
                parentEntityId: parent,
              });
            }
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="e-name" className="text-[12.5px] font-medium text-ink-2">
              Nom usuel
            </Label>
            <Input
              id="e-name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="e-legal" className="text-[12.5px] font-medium text-ink-2">
              Raison sociale
            </Label>
            <Input
              id="e-legal"
              required
              value={legalName}
              onChange={(e) => setLegalName(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="e-siret" className="text-[12.5px] font-medium text-ink-2">
              SIRET
            </Label>
            <Input
              id="e-siret"
              value={siret}
              onChange={(e) => setSiret(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-[12.5px] font-medium text-ink-2">
              Société parente
            </Label>
            <Select value={parentId} onValueChange={setParentId}>
              <SelectTrigger>
                <SelectValue placeholder="Aucune (société racine)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Aucune (société racine)</SelectItem>
                {entities
                  ?.filter((e) => e.id !== editingId)
                  .map((e) => (
                    <SelectItem key={e.id} value={String(e.id)}>
                      {e.name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>
          {formError && (
            <div
              role="alert"
              className="col-span-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
            >
              {formError}
            </div>
          )}
          <div className="col-span-2 flex gap-2">
            <Button type="submit" disabled={create.isPending || update.isPending}>
              {isEditing
                ? update.isPending
                  ? 'Enregistrement…'
                  : 'Enregistrer'
                : create.isPending
                ? 'Création…'
                : 'Créer'}
            </Button>
            {isEditing && (
              <Button type="button" variant="ghost" onClick={resetForm}>
                Annuler
              </Button>
            )}
          </div>
        </form>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Chargement…
        </div>
      ) : ordered.length === 0 ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Aucune société enregistrée.
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
          <ul>
            {ordered.map((e) => (
              <li
                key={e.id}
                className="flex items-center justify-between border-b border-line-soft px-5 py-3 transition-colors last:border-b-0 hover:bg-panel-2"
              >
                <div
                  className="flex items-center gap-2 text-[13px]"
                  style={{ paddingLeft: `${e.depth * 20}px` }}
                >
                  {e.depth > 0 && (
                    <span className="text-muted-foreground">↳</span>
                  )}
                  <span className="font-medium text-ink">{e.name}</span>
                  <span className="text-ink-2">— {e.legalName}</span>
                  {e.siret && (
                    <span className="ml-1 font-mono text-[11.5px] tabular-nums text-muted-foreground">
                      SIRET {e.siret}
                    </span>
                  )}
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => startEdit(e)}
                  >
                    Éditer
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-debit hover:text-debit"
                    onClick={() => {
                      if (confirm(`Supprimer "${e.name}" ?`)) del.mutate(e.id);
                    }}
                  >
                    Supprimer
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
