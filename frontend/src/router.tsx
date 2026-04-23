import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';

import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { LoginPage } from '@/pages/LoginPage';

// Route-based code-splitting. LoginPage reste eager (critical path + petit).
const AdminBankAccountsPage = lazy(() =>
  import('@/pages/AdminBankAccountsPage').then((m) => ({ default: m.AdminBankAccountsPage })),
);
const AdminEntitiesPage = lazy(() =>
  import('@/pages/AdminEntitiesPage').then((m) => ({ default: m.AdminEntitiesPage })),
);
const AdminUsersPage = lazy(() =>
  import('@/pages/AdminUsersPage').then((m) => ({ default: m.AdminUsersPage })),
);
const AnalysePage = lazy(() =>
  import('@/pages/AnalysePage').then((m) => ({ default: m.AnalysePage })),
);
const CommitmentsPage = lazy(() =>
  import('@/pages/CommitmentsPage').then((m) => ({ default: m.CommitmentsPage })),
);
const CounterpartiesPage = lazy(() =>
  import('@/pages/CounterpartiesPage').then((m) => ({ default: m.CounterpartiesPage })),
);
const DashboardPage = lazy(() =>
  import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
);
const ForecastV2Page = lazy(() =>
  import('@/pages/ForecastV2Page').then((m) => ({ default: m.ForecastV2Page })),
);
const RulesPage = lazy(() =>
  import('@/pages/RulesPage').then((m) => ({ default: m.RulesPage })),
);
const ImportHistoryPage = lazy(() =>
  import('@/pages/ImportHistoryPage').then((m) => ({ default: m.ImportHistoryPage })),
);
const ImportNewPage = lazy(() =>
  import('@/pages/ImportNewPage').then((m) => ({ default: m.ImportNewPage })),
);
const ProfilPage = lazy(() =>
  import('@/pages/ProfilPage').then((m) => ({ default: m.ProfilPage })),
);
const TransactionsPage = lazy(() =>
  import('@/pages/TransactionsPage').then((m) => ({ default: m.TransactionsPage })),
);

function PageLoadingFallback() {
  return (
    <div className="mx-auto w-full max-w-6xl space-y-4 p-6">
      <div className="h-8 w-64 animate-pulse rounded bg-slate-100" />
      <div className="h-40 animate-pulse rounded bg-slate-100" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="h-48 animate-pulse rounded bg-slate-100" />
        <div className="h-48 animate-pulse rounded bg-slate-100" />
      </div>
    </div>
  );
}

function LazyPage({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<PageLoadingFallback />}>{children}</Suspense>;
}

export const router = createBrowserRouter([
  { path: '/connexion', element: <LoginPage /> },
  {
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { path: '/', element: <Navigate to="/tableau-de-bord" replace /> },
      {
        path: '/tableau-de-bord',
        element: (
          <LazyPage>
            <DashboardPage />
          </LazyPage>
        ),
      },
      {
        path: '/analyse',
        element: (
          <LazyPage>
            <AnalysePage />
          </LazyPage>
        ),
      },
      {
        path: '/previsionnel',
        element: (
          <LazyPage>
            <ForecastV2Page />
          </LazyPage>
        ),
      },
      {
        path: '/imports',
        element: (
          <LazyPage>
            <ImportHistoryPage />
          </LazyPage>
        ),
      },
      {
        path: '/imports/nouveau',
        element: (
          <LazyPage>
            <ImportNewPage />
          </LazyPage>
        ),
      },
      {
        path: '/transactions',
        element: (
          <LazyPage>
            <TransactionsPage />
          </LazyPage>
        ),
      },
      {
        path: '/engagements',
        element: (
          <LazyPage>
            <CommitmentsPage />
          </LazyPage>
        ),
      },
      {
        path: '/tiers',
        element: (
          <LazyPage>
            <CounterpartiesPage />
          </LazyPage>
        ),
      },
      { path: '/contreparties', element: <Navigate to="/tiers" replace /> },
      {
        path: '/regles',
        element: (
          <LazyPage>
            <RulesPage />
          </LazyPage>
        ),
      },
      {
        path: '/profil',
        element: (
          <LazyPage>
            <ProfilPage />
          </LazyPage>
        ),
      },
      {
        path: '/administration/utilisateurs',
        element: (
          <LazyPage>
            <AdminUsersPage />
          </LazyPage>
        ),
      },
      {
        path: '/administration/societes',
        element: (
          <LazyPage>
            <AdminEntitiesPage />
          </LazyPage>
        ),
      },
      {
        path: '/administration/comptes-bancaires',
        element: (
          <LazyPage>
            <AdminBankAccountsPage />
          </LazyPage>
        ),
      },
    ],
  },
]);
