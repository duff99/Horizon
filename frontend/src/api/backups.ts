/**
 * Client API + hooks pour /api/admin/backups.
 *
 * Polling adaptatif via useBackupHistory : 3s tant qu'une opération est
 * pending|running, sinon 30s. Évite la pression sur le backend en idle.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiFetch } from './client';
import type {
  BackupDiskStats,
  BackupHistoryRow,
  BackupTriggerResponse,
  BackupTriggerType,
} from '@/types/backup';

type RawRow = {
  id: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  type: string;
  file_path: string;
  size_bytes: number | null;
  sha256: string | null;
  imports_size_bytes: number | null;
  imports_sha256: string | null;
  row_counts_json: Record<string, number> | null;
  error_message: string | null;
  error_step: string | null;
  verified_at: string | null;
  created_at: string;
};

function mapRow(r: RawRow): BackupHistoryRow {
  return {
    id: r.id,
    startedAt: r.started_at,
    completedAt: r.completed_at,
    status: r.status as BackupHistoryRow['status'],
    type: r.type as BackupHistoryRow['type'],
    filePath: r.file_path,
    sizeBytes: r.size_bytes,
    sha256: r.sha256,
    importsSizeBytes: r.imports_size_bytes,
    importsSha256: r.imports_sha256,
    rowCountsJson: r.row_counts_json,
    errorMessage: r.error_message,
    errorStep: r.error_step,
    verifiedAt: r.verified_at,
    createdAt: r.created_at,
  };
}

export async function listBackups(): Promise<BackupHistoryRow[]> {
  const raw = await apiFetch<RawRow[]>('/api/admin/backups');
  return raw.map(mapRow);
}

export async function getBackupDiskStats(): Promise<BackupDiskStats> {
  const raw = await apiFetch<{
    mount: string;
    size_gb: number;
    used_gb: number;
    avail_gb: number;
    used_pct: number;
    threshold_pct: number;
    status: 'ok' | 'alert';
  }>('/api/admin/backups/disk');
  return {
    mount: raw.mount,
    sizeGb: raw.size_gb,
    usedGb: raw.used_gb,
    availGb: raw.avail_gb,
    usedPct: raw.used_pct,
    thresholdPct: raw.threshold_pct,
    status: raw.status,
  };
}

export async function triggerBackup(
  type: BackupTriggerType
): Promise<BackupTriggerResponse> {
  const raw = await apiFetch<{ row_id: string }>(
    '/api/admin/backups/trigger',
    {
      method: 'POST',
      body: JSON.stringify({ type }),
    }
  );
  return { rowId: raw.row_id };
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

const KEY_LIST = ['admin', 'backups', 'list'];
const KEY_DISK = ['admin', 'backups', 'disk'];

const POLL_FAST_MS = 3_000; // pendant pending|running
const POLL_SLOW_MS = 30_000; // idle

export function useBackupHistory() {
  return useQuery({
    queryKey: KEY_LIST,
    queryFn: listBackups,
    refetchInterval: (query) => {
      const data = query.state.data as BackupHistoryRow[] | undefined;
      const inFlight = data?.some(
        (r) => r.status === 'pending' || r.status === 'running'
      );
      return inFlight ? POLL_FAST_MS : POLL_SLOW_MS;
    },
    refetchIntervalInBackground: false,
  });
}

export function useBackupDiskStats() {
  return useQuery({
    queryKey: KEY_DISK,
    queryFn: getBackupDiskStats,
    staleTime: 60_000,
  });
}

export function useTriggerBackup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (type: BackupTriggerType) => triggerBackup(type),
    onSuccess: () => {
      // Refetch immédiat pour voir la row pending apparaître
      queryClient.invalidateQueries({ queryKey: KEY_LIST });
    },
  });
}
