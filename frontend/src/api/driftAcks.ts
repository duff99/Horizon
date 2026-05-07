/**
 * Clients fetch + hooks TanStack Query pour /api/analysis/drift-acks (G12).
 *
 * Permet de snoozier (mettre en veille) une alerte de dérive pour 30 jours.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "./client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DriftAckRead {
  id: number;
  entity_id: number;
  category_id: number;
  snoozed_until: string; // "YYYY-MM-DD"
  acknowledged_at: string; // ISO datetime
  acknowledged_by_id: number | null;
  note: string | null;
}

export interface DriftSnoozeRequest {
  entity_id: number;
  category_id: number;
  snooze_days?: number; // default 30
  note?: string | null;
}

// ---------------------------------------------------------------------------
// Fetchers
// ---------------------------------------------------------------------------

export function fetchDriftAcks(args: {
  entityId: number;
}): Promise<DriftAckRead[]> {
  return apiFetch<DriftAckRead[]>(
    `/api/analysis/drift-acks/?entity_id=${args.entityId}`,
  );
}

export function postDriftAck(body: DriftSnoozeRequest): Promise<DriftAckRead> {
  return apiFetch<DriftAckRead>("/api/analysis/drift-acks/", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function deleteDriftAck(ackId: number): Promise<void> {
  return apiFetch<void>(`/api/analysis/drift-acks/${ackId}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useDriftAcks(args: { entityId?: number }) {
  return useQuery({
    queryKey: ["analysis", "drift-acks", args.entityId],
    queryFn: () => fetchDriftAcks({ entityId: args.entityId! }),
    staleTime: 2 * 60_000,
    enabled: args.entityId !== undefined,
  });
}

export function useSnoozeDrift() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: DriftSnoozeRequest) => postDriftAck(body),
    onSuccess: (_data, variables) => {
      // Invalider la query de dérive pour que le tableau se rafraîchisse
      queryClient.invalidateQueries({
        queryKey: ["analysis", "category-drift"],
      });
      queryClient.invalidateQueries({
        queryKey: ["analysis", "drift-acks", variables.entity_id],
      });
    },
  });
}
