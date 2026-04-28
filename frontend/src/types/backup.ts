/**
 * Types pour la page UI Sauvegardes (/administration/sauvegardes).
 * Mirroir du schéma Pydantic `BackupHistoryRead` côté backend.
 */

export type BackupStatus =
  | 'pending'
  | 'running'
  | 'success'
  | 'failed'
  | 'verified';

export type BackupType =
  | 'scheduled'
  | 'manual'
  | 'pre-op'
  | 'restore-test';

export interface BackupHistoryRow {
  id: string; // UUID
  startedAt: string; // ISO datetime
  completedAt: string | null;
  status: BackupStatus;
  type: BackupType;
  filePath: string;
  sizeBytes: number | null;
  sha256: string | null;
  importsSizeBytes: number | null;
  importsSha256: string | null;
  rowCountsJson: Record<string, number> | null;
  errorMessage: string | null;
  errorStep: string | null;
  verifiedAt: string | null;
  createdAt: string;
}

export interface BackupDiskStats {
  mount: string;
  sizeGb: number;
  usedGb: number;
  availGb: number;
  usedPct: number;
  thresholdPct: number;
  status: 'ok' | 'alert';
}

export interface BackupTriggerResponse {
  rowId: string; // UUID
}

// L'UI permet uniquement 'manual' et 'restore-test' (les autres types
// proviennent du cron / safe-stop, jamais de l'utilisateur).
export type BackupTriggerType = 'manual' | 'restore-test';
