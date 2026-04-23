/**
 * Types pour le journal d'audit (entité `audit_log` côté backend).
 *
 * Voir `backend/app/schemas/audit_log.py` et `backend/app/models/audit_log.py`.
 */

export type AuditAction = 'create' | 'update' | 'delete';

export interface AuditLogEntry {
  id: number;
  occurredAt: string;
  userId: number | null;
  userEmail: string | null;
  action: AuditAction;
  entityType: string;
  entityId: string;
  beforeJson: Record<string, unknown> | null;
  afterJson: Record<string, unknown> | null;
  diffJson: Record<string, { before: unknown; after: unknown }> | null;
  ipAddress: string | null;
  userAgent: string | null;
  requestId: string | null;
}

export interface AuditLogListResponse {
  items: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditLogFilters {
  entityType?: string;
  entityId?: string;
  userId?: number;
  action?: AuditAction;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}
