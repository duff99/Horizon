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

export type UpdateEntityInput = Partial<CreateEntityInput>;

export async function updateEntity(id: number, input: UpdateEntityInput): Promise<Entity> {
  const payload: Record<string, unknown> = {};
  if (input.name !== undefined) payload.name = input.name;
  if (input.legalName !== undefined) payload.legal_name = input.legalName;
  if (input.siret !== undefined) payload.siret = input.siret ?? null;
  if (input.parentEntityId !== undefined) payload.parent_entity_id = input.parentEntityId;
  const r = await apiFetch<RawEntity>(`/api/entities/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
  return mapEntity(r);
}

export async function deleteEntity(id: number): Promise<void> {
  await apiFetch<unknown>(`/api/entities/${id}`, { method: 'DELETE' });
}

export function useEntities() {
  return useQuery({ queryKey: ['entities'], queryFn: listEntities });
}
