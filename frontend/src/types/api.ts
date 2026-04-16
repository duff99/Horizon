export type UserRole = 'admin' | 'reader';

export type Me = {
  id: number;
  email: string;
  role: UserRole;
  fullName: string | null;
  isActive: boolean;
  createdAt: string;
  lastLoginAt: string | null;
};

export type Entity = {
  id: number;
  name: string;
  legalName: string;
  siret: string | null;
  parentEntityId: number | null;
  createdAt: string;
};

export type BankAccount = {
  id: number;
  entityId: number;
  name: string;
  iban: string;
  bic: string | null;
  bankName: string;
  bankCode: string;
  currency: string;
  isActive: boolean;
  createdAt: string;
};
