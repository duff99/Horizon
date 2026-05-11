import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { ApiError } from '@/api/client';
import { useEntities } from '@/api/entities';
import {
  grantUserEntityAccess,
  listUserEntityAccess,
  revokeUserEntityAccess,
} from '@/api/users';
import { Button } from '@/components/ui/button';

type Props = {
  userId: number;
  userEmail: string;
  open: boolean;
  onClose: () => void;
};

export function AdminUsersEntityAccessDialog({
  userId,
  userEmail,
  open,
  onClose,
}: Props) {
  const qc = useQueryClient();
  const accessQuery = useQuery({
    queryKey: ['user-entity-access', userId],
    queryFn: () => listUserEntityAccess(userId),
    enabled: open,
  });
  const entitiesQuery = useEntities();

  useEffect(() => {
    if (open) {
      qc.invalidateQueries({ queryKey: ['user-entity-access', userId] });
    }
  }, [open, userId, qc]);

  const grant = useMutation({
    mutationFn: (entityId: number) => grantUserEntityAccess(userId, entityId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['user-entity-access', userId] }),
    onError: (e) => alert(e instanceof ApiError ? e.detail : 'Erreur'),
  });

  const revoke = useMutation({
    mutationFn: (entityId: number) => revokeUserEntityAccess(userId, entityId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['user-entity-access', userId] }),
    onError: (e) => alert(e instanceof ApiError ? e.detail : 'Erreur'),
  });

  if (!open) return null;

  const accessibleIds = new Set(accessQuery.data ?? []);
  const entities = entitiesQuery.data ?? [];
  const loading = accessQuery.isLoading || entitiesQuery.isLoading;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="ea-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-lg rounded-xl border border-line-soft bg-panel p-6 shadow-card">
        <div>
          <h2 id="ea-title" className="text-[16px] font-semibold text-ink">
            Accès aux entités
          </h2>
          <p className="mt-0.5 text-[12.5px] text-muted-foreground">{userEmail}</p>
          <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-[12px] text-amber-900">
            Les readers ne voient que les entités cochées ici. Les admins voient
            toutes les entités quelle que soit cette liste.
          </p>
        </div>

        {loading ? (
          <div className="mt-6 text-center text-[13px] text-muted-foreground">
            Chargement…
          </div>
        ) : entities.length === 0 ? (
          <div className="mt-6 text-center text-[13px] text-muted-foreground">
            Aucune entité enregistrée.
          </div>
        ) : (
          <ul className="mt-4 divide-y divide-line-soft rounded-md border border-line-soft">
            {entities.map((ent) => {
              const has = accessibleIds.has(ent.id);
              const pending =
                (grant.isPending && grant.variables === ent.id) ||
                (revoke.isPending && revoke.variables === ent.id);
              return (
                <li
                  key={ent.id}
                  className="flex items-center justify-between gap-3 px-3 py-2"
                >
                  <div className="min-w-0">
                    <div className="truncate text-[13px] font-medium text-ink">
                      {ent.name}
                    </div>
                    <div className="truncate text-[11.5px] text-muted-foreground">
                      {ent.legalName}
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant={has ? 'ghost' : 'default'}
                    size="sm"
                    disabled={pending}
                    onClick={() => {
                      if (has) revoke.mutate(ent.id);
                      else grant.mutate(ent.id);
                    }}
                    title={
                      has
                        ? "Retire l'accès de cet utilisateur à cette entité (immédiat)."
                        : "Accorde l'accès en lecture à cette entité (immédiat)."
                    }
                  >
                    {pending ? '…' : has ? 'Révoquer' : 'Accorder'}
                  </Button>
                </li>
              );
            })}
          </ul>
        )}

        <div className="mt-6 flex justify-end">
          <Button type="button" variant="ghost" onClick={onClose}>
            Fermer
          </Button>
        </div>
      </div>
    </div>
  );
}
