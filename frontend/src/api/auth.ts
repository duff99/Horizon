import { apiFetch } from './client';

export type LoginInput = { email: string; password: string };

export async function login(input: LoginInput): Promise<void> {
  await apiFetch<unknown>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export async function logout(): Promise<void> {
  await apiFetch<unknown>('/api/auth/logout', { method: 'POST' });
}
