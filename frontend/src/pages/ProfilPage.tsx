import { useState } from 'react';

import { ApiError } from '@/api/client';
import { useChangeOwnPassword } from '@/api/password';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useMe } from '@/hooks/useAuth';

export function ProfilPage() {
  const { data: me } = useMe();
  const change = useChangeOwnPassword();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [clientError, setClientError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function resetForm() {
    setCurrentPassword('');
    setNewPassword('');
    setConfirm('');
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setClientError(null);
    setServerError(null);
    setSuccess(null);

    if (newPassword.length < 12) {
      setClientError('Minimum 12 caractères');
      return;
    }
    if (newPassword !== confirm) {
      setClientError('Les deux mots de passe ne correspondent pas');
      return;
    }

    try {
      await change.mutateAsync({
        current_password: currentPassword,
        new_password: newPassword,
      });
      resetForm();
      setSuccess('Mot de passe mis à jour');
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 400) {
          setServerError('Mot de passe actuel incorrect');
        } else {
          setServerError(err.detail || 'Erreur inconnue');
        }
      } else {
        setServerError('Erreur inconnue');
      }
    }
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">
          Mon profil
        </h1>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          Informations personnelles et sécurité du compte
        </p>
      </div>

      <div className="rounded-xl border border-line-soft bg-panel p-6 shadow-card">
        <h2 className="text-[14px] font-semibold text-ink">Informations</h2>
        <dl className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <dt className="text-[11.5px] uppercase tracking-wider text-muted-foreground">
              Email
            </dt>
            <dd className="mt-1 text-[13px] text-ink">{me?.email ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-[11.5px] uppercase tracking-wider text-muted-foreground">
              Nom complet
            </dt>
            <dd className="mt-1 text-[13px] text-ink">{me?.fullName ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-[11.5px] uppercase tracking-wider text-muted-foreground">
              Rôle
            </dt>
            <dd className="mt-1 text-[13px] text-ink">
              {me?.role === 'admin' ? 'Administrateur' : me?.role === 'reader' ? 'Lecture' : '—'}
            </dd>
          </div>
        </dl>
      </div>

      <div className="rounded-xl border border-line-soft bg-panel p-6 shadow-card">
        <h2 className="text-[14px] font-semibold text-ink">
          Changer mon mot de passe
        </h2>
        <form className="mt-4 grid max-w-md gap-4" onSubmit={handleSubmit}>
          <div className="space-y-1.5">
            <Label htmlFor="current-pwd" className="text-[12.5px] font-medium text-ink-2">
              Mot de passe actuel
            </Label>
            <Input
              id="current-pwd"
              type="password"
              required
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new-pwd" className="text-[12.5px] font-medium text-ink-2">
              Nouveau mot de passe (12 caractères min.)
            </Label>
            <Input
              id="new-pwd"
              type="password"
              required
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm-pwd" className="text-[12.5px] font-medium text-ink-2">
              Confirmer le nouveau mot de passe
            </Label>
            <Input
              id="confirm-pwd"
              type="password"
              required
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
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
          {success && (
            <div
              role="status"
              className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-[12.5px] text-emerald-800"
            >
              {success}
            </div>
          )}

          <div>
            <Button type="submit" disabled={change.isPending}>
              {change.isPending ? 'Mise à jour…' : 'Mettre à jour le mot de passe'}
            </Button>
          </div>
        </form>
      </div>
    </section>
  );
}
