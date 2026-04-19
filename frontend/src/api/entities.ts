import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';
import type { Entity } from '@/types/api';

type RawEntity = {
  id: number;
  name: string;
  legal_name: string;
  siret: string | null;
  parent_entity_id: number | null;
  created_at: string;
};

function mapEntity(r: RawEntity): Entity {
  return {
    id: r.id,
    name: r.name,
    legalName: r.legal_name,
    siret: r.siret,
    parentEntityId: r.parent_entity_id,
    createdAt: r.created_at,
  };
}

export async function listEntities(): Promise<Entity[]> {
  const raw = await apiFetch<RawEntity[]>('/api/entities');
  return raw.map(mapEntity);
}

export type CreateEntityInput = {
  name: string;
  legalName: string;
  siret?: string;
  parentEntityId?: number | null;
};

export async function createEntity(input: CreateEntityInput): Promise<Entity> {
  const r = await apiFetch<RawEntity>('/api/entities', {
    method: 'POST',
    body: JSON.stringify({
      name: input.name,
      legal_name: input.legalName,
      siret: input.siret ?? null,
      parent_entity_id: input.parentEntityId ?? null,
    }),
  });
  return mapEntity(r);
}

export async function deleteEntity(id: number): Promise<void> {
  await apiFetch<unknown>(`/api/entities/${id}`, { method: 'DELETE' });
}

export function useEntities() {
  return useQuery({ queryKey: ['entities'], queryFn: listEntities });
}
