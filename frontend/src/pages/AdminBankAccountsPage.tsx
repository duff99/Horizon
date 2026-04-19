import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { ApiError } from '@/api/client';
import { createBankAccount, listBankAccounts } from '@/api/bankAccounts';
import { listEntities } from '@/api/entities';
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

function formatIban(raw: string): string {
  return raw
    .replace(/\s+/g, '')
    .replace(/(.{4})/g, '$1 ')
    .trim();
}

export function AdminBankAccountsPage() {
  const qc = useQueryClient();
  const { data: accounts, isLoading } = useQuery({
    queryKey: ['bank-accounts'],
    queryFn: listBankAccounts,
  });
  const { data: entities } = useQuery({
    queryKey: ['entities'],
    queryFn: listEntities,
  });

  const [entityId, setEntityId] = useState<string>('');
  const [name, setName] = useState('');
  const [iban, setIban] = useState('');
  const [bic, setBic] = useState('');
  const [bankName, setBankName] = useState('');
  const [bankCode, setBankCode] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: createBankAccount,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bank-accounts'] });
      setName('');
      setIban('');
      setBic('');
      setBankName('');
      setBankCode('');
      setEntityId('');
      setFormError(null);
    },
    onError: (e) => setFormError(e instanceof ApiError ? e.detail : 'Erreur inconnue'),
  });

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">
          Comptes bancaires
        </h1>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          {accounts?.length ?? 0} compte{(accounts?.length ?? 0) > 1 ? 's' : ''} enregistré
          {(accounts?.length ?? 0) > 1 ? 's' : ''}
        </p>
      </div>

      <div className="rounded-xl border border-line-soft bg-panel p-6 shadow-card">
        <h2 className="text-[14px] font-semibold text-ink">Ajouter un compte bancaire</h2>
        <form
          className="mt-4 grid grid-cols-2 gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (!entityId) {
              setFormError('Veuillez sélectionner une société');
              return;
            }
            create.mutate({
              entityId: Number(entityId),
              name,
              iban,
              bic: bic || undefined,
              bankName,
              bankCode,
            });
          }}
        >
          <div className="col-span-2 space-y-1.5">
            <Label className="text-[12.5px] font-medium text-ink-2">Société</Label>
            <Select value={entityId} onValueChange={setEntityId}>
              <SelectTrigger>
                <SelectValue placeholder="Choisir une société" />
              </SelectTrigger>
              <SelectContent>
                {entities?.map((e) => (
                  <SelectItem key={e.id} value={String(e.id)}>
                    {e.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ba-name" className="text-[12.5px] font-medium text-ink-2">
              Libellé du compte
            </Label>
            <Input
              id="ba-name"
              placeholder="Compte courant principal"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ba-iban" className="text-[12.5px] font-medium text-ink-2">
              IBAN
            </Label>
            <Input
              id="ba-iban"
              pattern="^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$"
              title="IBAN : 2 lettres + 2 chiffres + 10 à 30 caractères alphanumériques"
              required
              value={iban}
              onChange={(e) =>
                setIban(e.target.value.toUpperCase().replace(/\s/g, ''))
              }
            />
            {iban && (
              <p className="font-mono text-[11.5px] tabular-nums text-muted-foreground">
                {formatIban(iban)}
              </p>
            )}
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ba-bic" className="text-[12.5px] font-medium text-ink-2">
              BIC (optionnel)
            </Label>
            <Input
              id="ba-bic"
              maxLength={11}
              value={bic}
              onChange={(e) => setBic(e.target.value.toUpperCase())}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ba-bank" className="text-[12.5px] font-medium text-ink-2">
              Banque
            </Label>
            <Input
              id="ba-bank"
              placeholder="Delubac"
              required
              value={bankName}
              onChange={(e) => setBankName(e.target.value)}
            />
          </div>

          <div className="col-span-2 space-y-1.5">
            <Label htmlFor="ba-bankcode" className="text-[12.5px] font-medium text-ink-2">
              Code analyseur interne (pour le parser d'import)
            </Label>
            <Input
              id="ba-bankcode"
              placeholder="delubac"
              required
              pattern="^[a-z0-9_-]+$"
              title="Minuscules, chiffres, tirets et underscores uniquement"
              value={bankCode}
              onChange={(e) =>
                setBankCode(e.target.value.toLowerCase().replace(/\s/g, ''))
              }
            />
            <p className="text-[11.5px] text-muted-foreground">
              Utilisé par le module d'import (Plan 1) pour sélectionner le bon
              analyseur. Exemples :{' '}
              <code className="rounded bg-panel-2 px-1 font-mono text-[11px]">delubac</code>,{' '}
              <code className="rounded bg-panel-2 px-1 font-mono text-[11px]">qonto</code>,{' '}
              <code className="rounded bg-panel-2 px-1 font-mono text-[11px]">bnp</code>.
            </p>
          </div>

          {formError && (
            <div
              role="alert"
              className="col-span-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
            >
              {formError}
            </div>
          )}

          <div className="col-span-2">
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? 'Création…' : 'Créer'}
            </Button>
          </div>
        </form>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Chargement…
        </div>
      ) : !accounts || accounts.length === 0 ? (
        <div className="rounded-xl border border-line-soft bg-panel p-10 text-center text-[13px] text-muted-foreground shadow-card">
          Aucun compte enregistré pour l'instant.
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line-soft bg-panel shadow-card">
          <table className="w-full">
            <thead>
              <tr className="border-b border-line-soft bg-panel-2">
                <th className="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Société
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Libellé
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Banque
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  IBAN
                </th>
                <th className="px-3 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Statut
                </th>
              </tr>
            </thead>
            <tbody>
              {accounts.map((a) => {
                const entity = entities?.find((e) => e.id === a.entityId);
                return (
                  <tr
                    key={a.id}
                    className="border-b border-line-soft transition-colors hover:bg-panel-2"
                  >
                    <td className="px-4 py-3 text-[13px] text-ink-2">
                      {entity?.name ?? '—'}
                    </td>
                    <td className="px-3 py-3 text-[13px] font-medium text-ink">
                      {a.name}
                    </td>
                    <td className="px-3 py-3 text-[13px] text-ink-2">
                      {a.bankName}
                    </td>
                    <td className="px-3 py-3 font-mono text-[12.5px] tabular-nums text-ink-2">
                      {formatIban(a.iban)}
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11.5px] font-medium ${
                          a.isActive
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                            : 'border-line-soft bg-panel-2 text-muted-foreground'
                        }`}
                      >
                        {a.isActive ? 'Actif' : 'Inactif'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
