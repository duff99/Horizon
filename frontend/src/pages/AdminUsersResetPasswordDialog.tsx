import { useEffect, useState } from 'react';

import { ApiError } from '@/api/client';
import { useAdminResetPassword } from '@/api/password';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

type Props = {
  userId: number;
  userEmail: string;
  open: boolean;
  onClose: () => void;
};

export function AdminUsersResetPasswordDialog({
  userId,
  userEmail,
  open,
  onClose,
}: Props) {
  const reset = useAdminResetPassword(userId);
  const [newPassword, setNewPassword] = useState('');
  const [clientError, setClientError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!open) {
      setNewPassword('');
      setClientError(null);
      setServerError(null);
      setSuccess(false);
    }
  }, [open]);

  useEffect(() => {
    if (success) {
      const t = setTimeout(() => onClose(), 2000);
      return () => clearTimeout(t);
    }
  }, [success, onClose]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setClientError(null);
    setServerError(null);

    if (newPassword.length < 12) {
      setClientError('Minimum 12 caractères');
      return;
    }

    try {
      await reset.mutateAsync({ new_password: newPassword });
      setSuccess(true);
    } catch (err) {
      if (err instanceof ApiError) {
        setServerError(err.detail || 'Erreur inconnue');
      } else {
        setServerError('Erreur inconnue');
      }
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="reset-pwd-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md rounded-xl border border-line-soft bg-panel p-6 shadow-card">
        <div className="flex items-start justify-between">
          <div>
            <h2 id="reset-pwd-title" className="text-[16px] font-semibold text-ink">
              Réinitialiser le mot de passe
            </h2>
            <p className="mt-0.5 text-[12.5px] text-muted-foreground">{userEmail}</p>
          </div>
        </div>

        {success ? (
          <div className="mt-6 space-y-4">
            <div
              role="status"
              className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-[12.5px] text-emerald-800"
            >
              Mot de passe réinitialisé pour {userEmail}
            </div>
            <div className="flex justify-end">
              <Button type="button" onClick={onClose}>
                Fermer
              </Button>
            </div>
          </div>
        ) : (
          <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <Label
                htmlFor="admin-reset-pwd"
                className="text-[12.5px] font-medium text-ink-2"
              >
                Nouveau mot de passe (12 caractères min.)
              </Label>
              <Input
                id="admin-reset-pwd"
                type="password"
                required
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>

            {clientError && (
              <div
                role="alert"
                className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
              >
                {clientError}
              </div>
            )}
            {serverError && (
              <div
                role="alert"
                className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
              >
                {serverError}
              </div>
            )}

            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" onClick={onClose}>
                Annuler
              </Button>
              <Button type="submit" disabled={reset.isPending}>
                {reset.isPending ? 'Réinitialisation…' : 'Réinitialiser'}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
