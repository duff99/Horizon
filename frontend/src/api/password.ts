import { useMutation } from '@tanstack/react-query';

import { apiFetch } from './client';

export type ChangeOwnPasswordInput = {
  current_password: string;
  new_password: string;
};

export async function changeOwnPassword(input: ChangeOwnPasswordInput): Promise<void> {
  await apiFetch<void>('/api/me/password', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export type AdminResetPasswordInput = {
  new_password: string;
};

export async function adminResetPassword(
  userId: number,
  input: AdminResetPasswordInput
): Promise<void> {
  await apiFetch<void>(`/api/users/${userId}/password`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function useChangeOwnPassword() {
  return useMutation({
    mutationFn: (body: ChangeOwnPasswordInput) => changeOwnPassword(body),
  });
}

export function useAdminResetPassword(userId: number) {
  return useMutation({
    mutationFn: (body: AdminResetPasswordInput) => adminResetPassword(userId, body),
  });
}
