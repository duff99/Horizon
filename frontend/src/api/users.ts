import { apiFetch } from './client';
import type { Me, UserRole } from '@/types/api';

type RawUser = {
  id: number;
  email: string;
  role: UserRole;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
};

export type User = Me;

function mapUser(r: RawUser): User {
  return {
    id: r.id,
    email: r.email,
    role: r.role,
    fullName: r.full_name,
    isActive: r.is_active,
    createdAt: r.created_at,
    lastLoginAt: r.last_login_at,
  };
}

export async function listUsers(): Promise<User[]> {
  const raw = await apiFetch<RawUser[]>('/api/users');
  return raw.map(mapUser);
}

export type CreateUserInput = {
  email: string;
  password: string;
  role: UserRole;
  fullName?: string;
};

export async function createUser(input: CreateUserInput): Promise<User> {
  const r = await apiFetch<RawUser>('/api/users', {
    method: 'POST',
    body: JSON.stringify({
      email: input.email,
      password: input.password,
      role: input.role,
      full_name: input.fullName,
    }),
  });
  return mapUser(r);
}
