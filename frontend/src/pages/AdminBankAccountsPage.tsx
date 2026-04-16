import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { ApiError } from '@/api/client';
import { createBankAccount, listBankAccounts } from '@/api/bankAccounts';
import { listEntities } from '@/api/entities';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Comptes bancaires</h1>

      <Card>
        <CardHeader>
          <CardTitle>Ajouter un compte bancaire</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="grid grid-cols-2 gap-4"
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
            <div className="space-y-2 col-span-2">
              <Label>Société</Label>
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

            <div className="space-y-2">
              <Label htmlFor="ba-name">Libellé du compte</Label>
              <Input
                id="ba-name"
                placeholder="Compte courant principal"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="ba-iban">IBAN</Label>
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
              {iban && <p className="text-xs text-slate-500">{formatIban(iban)}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="ba-bic">BIC (optionnel)</Label>
              <Input
                id="ba-bic"
                maxLength={11}
                value={bic}
                onChange={(e) => setBic(e.target.value.toUpperCase())}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="ba-bank">Banque</Label>
              <Input
                id="ba-bank"
                placeholder="Delubac"
                required
                value={bankName}
                onChange={(e) => setBankName(e.target.value)}
              />
            </div>

            <div className="space-y-2 col-span-2">
              <Label htmlFor="ba-bankcode">
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
              <p className="text-xs text-slate-500">
                Utilisé par le module d'import (Plan 1) pour sélectionner le bon
                analyseur. Exemples : <code>delubac</code>, <code>qonto</code>,{' '}
                <code>bnp</code>.
              </p>
            </div>

            {formError && (
              <p className="col-span-2 text-red-600 text-sm">{formError}</p>
            )}

            <div className="col-span-2">
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? 'Création…' : 'Créer'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Comptes enregistrés</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p>Chargement…</p>}
          {accounts && accounts.length === 0 && (
            <p className="text-slate-500">Aucun compte enregistré pour l'instant.</p>
          )}
          {accounts && accounts.length > 0 && (
            <table className="w-full text-sm">
              <thead className="text-left text-slate-600">
                <tr>
                  <th className="py-2">Société</th>
                  <th>Libellé</th>
                  <th>Banque</th>
                  <th>IBAN</th>
                  <th>Statut</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((a) => {
                  const entity = entities?.find((e) => e.id === a.entityId);
                  return (
                    <tr key={a.id} className="border-t border-slate-200">
                      <td className="py-2">{entity?.name ?? '—'}</td>
                      <td>{a.name}</td>
                      <td>{a.bankName}</td>
                      <td className="font-mono">{formatIban(a.iban)}</td>
                      <td>
                        {a.isActive ? (
                          <span className="text-green-700">Actif</span>
                        ) : (
                          <span className="text-slate-500">Inactif</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
