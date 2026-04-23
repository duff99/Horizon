/**
 * Client API pour `/api/admin/audit-log`.
 */
import { apiFetch } from './client';
import type {
  AuditAction,
  AuditLogEntry,
  AuditLogFilters,
  AuditLogListResponse,
} from '@/types/auditLog';

type RawAuditLogEntry = {
  id: number;
  occurred_at: string;
  user_id: number | null;
  user_email: string | null;
  action: AuditAction;
  entity_type: string;
  entity_id: string;
  before_json: Record<string, unknown> | null;
  after_json: Record<string, unknown> | null;
  diff_json: Record<string, { before: unknown; after: unknown }> | null;
  ip_address: string | null;
  user_agent: string | null;
  request_id: string | null;
};

type RawAuditLogListResponse = {
  items: RawAuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
};

function mapEntry(r: RawAuditLogEntry): AuditLogEntry {
  return {
    id: r.id,
    occurredAt: r.occurred_at,
    userId: r.user_id,
    userEmail: r.user_email,
    action: r.action,
    entityType: r.entity_type,
    entityId: r.entity_id,
    beforeJson: r.before_json,
    afterJson: r.after_json,
    diffJson: r.diff_json,
    ipAddress: r.ip_address,
    userAgent: r.user_agent,
    requestId: r.request_id,
  };
}

export async function listAuditLog(
  filters: AuditLogFilters = {}
): Promise<AuditLogListResponse> {
  const params = new URLSearchParams();
  if (filters.entityType) params.set('entity_type', filters.entityType);
  if (filters.entityId) params.set('entity_id', filters.entityId);
  if (filters.userId !== undefined)
    params.set('user_id', String(filters.userId));
  if (filters.action) params.set('action', filters.action);
  if (filters.from) params.set('from', filters.from);
  if (filters.to) params.set('to', filters.to);
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters.offset !== undefined)
    params.set('offset', String(filters.offset));

  const qs = params.toString();
  const raw = await apiFetch<RawAuditLogListResponse>(
    `/api/admin/audit-log${qs ? `?${qs}` : ''}`
  );
  return {
    items: raw.items.map(mapEntry),
    total: raw.total,
    limit: raw.limit,
    offset: raw.offset,
  };
}
