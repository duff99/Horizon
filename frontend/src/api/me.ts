import { apiFetch } from './client';
import type { Me, UserRole } from '@/types/api';

type RawMe = {
  id: number;
  email: string;
  role: UserRole;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
};

export async function getMe(): Promise<Me> {
  const raw = await apiFetch<RawMe>('/api/me');
  return {
    id: raw.id,
    email: raw.email,
    role: raw.role,
    fullName: raw.full_name,
    isActive: raw.is_active,
    createdAt: raw.created_at,
    lastLoginAt: raw.last_login_at,
  };
}
