import { Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';

import { AdminRoute } from '@/components/AdminRoute';
import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { lazyWithReload } from '@/lib/lazyWithReload';
import { LoginPage } from '@/pages/LoginPage';

// Route-based code-splitting. LoginPage reste eager (critical path + petit).
// `lazyWithReload` auto-recharge la page si un chunk fingerprinté a disparu
// après un déploiement (sinon on affichait "Failed to fetch dynamically
// imported module" → cf. erreurs client 2026-05-12).
const AdminAuditLogPage = lazyWithReload(() =>
  import('@/pages/AdminAuditLogPage').then((m) => ({ default: m.AdminAuditLogPage })),
);
const AdminClientErrorsPage = lazyWithReload(() =>
  import('@/pages/AdminClientErrorsPage').then((m) => ({ default: m.AdminClientErrorsPage })),
);
const AdminBackupsPage = lazyWithReload(() =>
  import('@/pages/AdminBackupsPage').then((m) => ({ default: m.AdminBackupsPage })),
);
const AdminBankAccountsPage = lazyWithReload(() =>
  import('@/pages/AdminBankAccountsPage').then((m) => ({ default: m.AdminBankAccountsPage })),
);
const AdminCategoriesPage = lazyWithReload(() =>
  import('@/pages/AdminCategoriesPage').then((m) => ({ default: m.AdminCategoriesPage })),
);
const AdminEntitiesPage = lazyWithReload(() =>
  import('@/pages/AdminEntitiesPage').then((m) => ({ default: m.AdminEntitiesPage })),
);
const AdminUsersPage = lazyWithReload(() =>
  import('@/pages/AdminUsersPage').then((m) => ({ default: m.AdminUsersPage })),
);
const AnalysePage = lazyWithReload(() =>
  import('@/pages/AnalysePage').then((m) => ({ default: m.AnalysePage })),
);
const CommitmentsPage = lazyWithReload(() =>
  import('@/pages/CommitmentsPage').then((m) => ({ default: m.CommitmentsPage })),
);
const CounterpartiesPage = lazyWithReload(() =>
  import('@/pages/CounterpartiesPage').then((m) => ({ default: m.CounterpartiesPage })),
);
const DashboardPage = lazyWithReload(() =>
  import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
);
const DocumentationPage = lazyWithReload(() =>
  import('@/pages/DocumentationPage').then((m) => ({ default: m.DocumentationPage })),
);
const ForecastV2Page = lazyWithReload(() =>
  import('@/pages/ForecastV2Page').then((m) => ({ default: m.ForecastV2Page })),
);
const RulesPage = lazyWithReload(() =>
  import('@/pages/RulesPage').then((m) => ({ default: m.RulesPage })),
);
const ImportHistoryPage = lazyWithReload(() =>
  import('@/pages/ImportHistoryPage').then((m) => ({ default: m.ImportHistoryPage })),
);
const ImportNewPage = lazyWithReload(() =>
  import('@/pages/ImportNewPage').then((m) => ({ default: m.ImportNewPage })),
);
const ProfilPage = lazyWithReload(() =>
  import('@/pages/ProfilPage').then((m) => ({ default: m.ProfilPage })),
);
const TransactionsPage = lazyWithReload(() =>
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
          <AdminRoute>
            <LazyPage>
              <AdminUsersPage />
            </LazyPage>
          </AdminRoute>
        ),
      },
      {
        path: '/administration/societes',
        element: (
          <AdminRoute>
            <LazyPage>
              <AdminEntitiesPage />
            </LazyPage>
          </AdminRoute>
        ),
      },
      {
        path: '/administration/comptes-bancaires',
        element: (
          <AdminRoute>
            <LazyPage>
              <AdminBankAccountsPage />
            </LazyPage>
          </AdminRoute>
        ),
      },
      {
        path: '/administration/categories',
        element: (
          <AdminRoute>
            <LazyPage>
              <AdminCategoriesPage />
            </LazyPage>
          </AdminRoute>
        ),
      },
      {
        path: '/administration/sauvegardes',
        element: (
          <AdminRoute>
            <LazyPage>
              <AdminBackupsPage />
            </LazyPage>
          </AdminRoute>
        ),
      },
      {
        path: '/administration/audit',
        element: (
          <AdminRoute>
            <LazyPage>
              <AdminAuditLogPage />
            </LazyPage>
          </AdminRoute>
        ),
      },
      {
        path: '/administration/erreurs-client',
        element: (
          <AdminRoute>
            <LazyPage>
              <AdminClientErrorsPage />
            </LazyPage>
          </AdminRoute>
        ),
      },
      {
        path: '/documentation',
        element: (
          <LazyPage>
            <DocumentationPage />
          </LazyPage>
        ),
      },
    ],
  },
]);
