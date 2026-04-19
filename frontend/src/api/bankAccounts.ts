import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';
import type { BankAccount } from '@/types/api';

type RawBA = {
  id: number;
  entity_id: number;
  name: string;
  iban: string;
  bic: string | null;
  bank_name: string;
  bank_code: string;
  account_number: string | null;
  currency: string;
  is_active: boolean;
  created_at: string;
};

function mapBA(r: RawBA): BankAccount {
  return {
    id: r.id,
    entityId: r.entity_id,
    name: r.name,
    iban: r.iban,
    bic: r.bic,
    bankName: r.bank_name,
    bankCode: r.bank_code,
    currency: r.currency,
    isActive: r.is_active,
    createdAt: r.created_at,
  };
}

export async function listBankAccounts(): Promise<BankAccount[]> {
  const raw = await apiFetch<RawBA[]>('/api/bank-accounts');
  return raw.map(mapBA);
}

export type CreateBankAccountInput = {
  entityId: number;
  name: string;
  iban: string;
  bic?: string;
  bankName: string;
  bankCode: string;
  currency?: string;
};

export async function createBankAccount(
  i: CreateBankAccountInput
): Promise<BankAccount> {
  const r = await apiFetch<RawBA>('/api/bank-accounts', {
    method: 'POST',
    body: JSON.stringify({
      entity_id: i.entityId,
      name: i.name,
      iban: i.iban,
      bic: i.bic ?? null,
      bank_name: i.bankName,
      bank_code: i.bankCode,
      currency: i.currency ?? 'EUR',
    }),
  });
  return mapBA(r);
}

export function useBankAccounts() {
  return useQuery({ queryKey: ['bankAccounts'], queryFn: listBankAccounts });
}
