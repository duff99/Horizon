import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { ApiError } from '@/api/client';
import {
  createUser,
  deactivateUser,
  listUsers,
  updateUser,
  type User,
} from '@/api/users';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { UserRole } from '@/types/api';

export function AdminUsersPage() {
  const qc = useQueryClient();
  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: listUsers,
  });

  const [editingId, setEditingId] = useState<number | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState<UserRole>('reader');
  const [isActive, setIsActive] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);

  const isEditing = editingId !== null;

  function resetForm() {
    setEditingId(null);
    setEmail('');
    setPassword('');
    setFullName('');
    setRole('reader');
    setIsActive(true);
    setFormError(null);
  }

  function startEdit(u: User) {
    setEditingId(u.id);
    setEmail(u.email);
    setPassword('');
    setFullName(u.fullName ?? '');
    setRole(u.role);
    setIsActive(u.isActive);
    setFormError(null);
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  const create = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      resetForm();
    },
    onError: (e) => {
      setFormError(e instanceof ApiError ? e.detail : 'Erreur inconnue');
    },
  });

  const update = useMutation({
    mutationFn: (input: {
      id: number;
      fullName: string | null;
      role: UserRole;
      isActive: boolean;
    }) =>
      updateUser(input.id, {
        fullName: input.fullName,
        role: input.role,
        isActive: input.isActive,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      resetForm();
    },
    onError: (e) => {
      setFormError(e instanceof ApiError ? e.detail : 'Erreur inconnue');
    },
  });

  const deactivate = useMutation({
    mutationFn: deactivateUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
    onError: (e) => alert(e instanceof ApiError ? e.detail : 'Erreur'),
  });

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">
          Utilisateurs
        </h1>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          {users?.length ?? 0} utilisateur{(users?.length ?? 0) > 1 ? 's' : ''}
        </p>
      </div>

      <div className="rounded-xl border border-line-soft bg-panel p-6 shadow-card">
        <h2 className="text-[14px] font-semibold text-ink">
          {isEditing ? "Modifier l'utilisateur" : 'Créer un utilisateur'}
        </h2>
        <form
          className="mt-4 grid grid-cols-2 gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (isEditing && editingId !== null) {
              update.mutate({
                id: editingId,
                fullName: fullName || null,
                role,
                isActive,
              });
            } else {
              create.mutate({
                email,
                password,
                role,
                fullName: fullName || undefined,
              });
            }
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="u-email" className="text-[12.5px] font-medium text-ink-2">
              Email
            </Label>
            <Input
              id="u-email"
              type="email"
              required
              disabled={isEditing}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {isEditing && (
              <p className="text-[11.5px] text-muted-foreground">
                L'email ne peut pas être modifié.
              </p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="u-name" className="text-[12.5px] font-medium text-ink-2">
              Nom complet
            </Label>
            <Input
              id="u-name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
          {!isEditing && (
            <div className="space-y-1.5">
              <Label htmlFor="u-pwd" className="text-[12.5px] font-medium text-ink-2">
                Mot de passe (12 caractères min.)
              </Label>
              <Input
                id="u-pwd"
                type="password"
                minLength={12}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          )}
          <div className="space-y-1.5">
            <Label className="text-[12.5px] font-medium text-ink-2">Rôle</Label>
            <Select value={role} onValueChange={(v) => setRole(v as UserRole)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="reader">Lecture</SelectItem>
                <SelectItem value="admin">Administrateur</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {isEditing && (
            <div className="col-span-2">
              <label className="flex cursor-pointer items-center gap-2 text-[13px] text-ink-2">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-accent"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                />
                Utilisateur actif
              </label>
            </div>
          )}
          {formError && (
            <div
              role="alert"
              className="col-span-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
            >
              {formError}
            </div>
          )}
          <div className="col-span-2 flex gap-2">
            <Button type="submit" disabled={create.isPending || update.isPending}>
              {isEditing
                ? update.isPending
                  ? 'Enregistrement…'
                  : 'Enregistrer'
                : create.isPending
                ? 'Création…'
                : 'Créer'}
            </Button>
            {isEditing && (
              <Button type="button" variant="ghost" onClick={resetForm}>
                Annuler
              </Button>
            )}
          </div>
        </form>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Chargement…
        </div>
      ) : !users || users.length === 0 ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Aucun utilisateur enregistré.
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
          <table className="w-full">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2">
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Email
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Nom
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Rôle
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Statut
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Créé le
                </th>
                <th className="px-3 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr
                  key={u.id}
                  className="border-b border-line-soft transition-colors hover:bg-panel-2"
                >
                  <td className="px-4 py-3 text-[13px] font-medium text-ink">
                    {u.email}
                  </td>
                  <td className="px-3 py-3 text-[13px] text-ink-2">
                    {u.fullName ?? '—'}
                  </td>
                  <td className="px-3 py-3 text-[13px] text-ink-2">
                    {u.role === 'admin' ? 'Administrateur' : 'Lecture'}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11.5px] font-medium ${
                        u.isActive
                          ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                          : 'border-line-soft bg-panel-2 text-muted-foreground'
                      }`}
                    >
                      {u.isActive ? 'Actif' : 'Inactif'}
                    </span>
                  </td>
                  <td className="px-3 py-3 font-mono text-[12.5px] tabular-nums text-muted-foreground">
                    {new Date(u.createdAt).toLocaleDateString('fr-FR')}
                  </td>
                  <td className="px-3 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="sm" onClick={() => startEdit(u)}>
                        Éditer
                      </Button>
                      {u.isActive && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-debit hover:text-debit"
                          onClick={() => {
                            if (confirm(`Désactiver "${u.email}" ?`)) {
                              deactivate.mutate(u.id);
                            }
                          }}
                        >
                          Désactiver
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
