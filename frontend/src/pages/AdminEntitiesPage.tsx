import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { ApiError } from '@/api/client';
import { createEntity, deleteEntity, listEntities } from '@/api/entities';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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

  const [name, setName] = useState('');
  const [legalName, setLegalName] = useState('');
  const [siret, setSiret] = useState('');
  const [parentId, setParentId] = useState<string>('none');
  const [formError, setFormError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: createEntity,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entities'] });
      setName('');
      setLegalName('');
      setSiret('');
      setParentId('none');
      setFormError(null);
    },
    onError: (e) => setFormError(e instanceof ApiError ? e.detail : 'Erreur'),
  });

  const del = useMutation({
    mutationFn: deleteEntity,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['entities'] }),
    onError: (e) => alert(e instanceof ApiError ? e.detail : 'Erreur'),
  });

  const ordered = entities ? toTreeOrder(entities) : [];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Sociétés</h1>

      <Card>
        <CardHeader>
          <CardTitle>Créer une société</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="grid grid-cols-2 gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              create.mutate({
                name,
                legalName,
                siret: siret || undefined,
                parentEntityId: parentId === 'none' ? null : Number(parentId),
              });
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="e-name">Nom usuel</Label>
              <Input
                id="e-name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="e-legal">Raison sociale</Label>
              <Input
                id="e-legal"
                required
                value={legalName}
                onChange={(e) => setLegalName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="e-siret">SIRET</Label>
              <Input
                id="e-siret"
                value={siret}
                onChange={(e) => setSiret(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Société parente</Label>
              <Select value={parentId} onValueChange={setParentId}>
                <SelectTrigger>
                  <SelectValue placeholder="Aucune (société racine)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Aucune (société racine)</SelectItem>
                  {entities?.map((e) => (
                    <SelectItem key={e.id} value={String(e.id)}>
                      {e.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {formError && (
              <p className="col-span-2 text-red-600 text-sm">{formError}</p>
            )}
            <div className="col-span-2">
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? 'Création…' : 'Créer'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Liste des sociétés</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p>Chargement…</p>}
          {ordered.length === 0 && !isLoading && (
            <p className="text-slate-500">Aucune société enregistrée.</p>
          )}
          {ordered.length > 0 && (
            <ul className="space-y-1">
              {ordered.map((e) => (
                <li
                  key={e.id}
                  className="flex items-center justify-between py-1 border-b border-slate-100"
                >
                  <span style={{ paddingLeft: `${e.depth * 24}px` }}>
                    {e.depth > 0 && '↳ '}
                    <strong>{e.name}</strong>
                    <span className="text-slate-500 ml-2">— {e.legalName}</span>
                    {e.siret && (
                      <span className="text-slate-400 ml-2">SIRET {e.siret}</span>
                    )}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      if (confirm(`Supprimer "${e.name}" ?`)) del.mutate(e.id);
                    }}
                  >
                    Supprimer
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
