import { createBrowserRouter, Navigate } from 'react-router-dom';

import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AdminBankAccountsPage } from '@/pages/AdminBankAccountsPage';
import { AdminEntitiesPage } from '@/pages/AdminEntitiesPage';
import { AdminUsersPage } from '@/pages/AdminUsersPage';
import { CommitmentsPage } from '@/pages/CommitmentsPage';
import { CounterpartiesPage } from '@/pages/CounterpartiesPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { ForecastPage } from '@/pages/ForecastPage';
import { RulesPage } from '@/pages/RulesPage';
import { ImportHistoryPage } from '@/pages/ImportHistoryPage';
import { ImportNewPage } from '@/pages/ImportNewPage';
import { LoginPage } from '@/pages/LoginPage';
import { ProfilPage } from '@/pages/ProfilPage';
import { TransactionsPage } from '@/pages/TransactionsPage';

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
      { path: '/tableau-de-bord', element: <DashboardPage /> },
      { path: '/previsionnel', element: <ForecastPage /> },
      { path: '/imports', element: <ImportHistoryPage /> },
      { path: '/imports/nouveau', element: <ImportNewPage /> },
      { path: '/transactions', element: <TransactionsPage /> },
      { path: '/engagements', element: <CommitmentsPage /> },
      { path: '/tiers', element: <CounterpartiesPage /> },
      { path: '/contreparties', element: <Navigate to="/tiers" replace /> },
      { path: '/regles', element: <RulesPage /> },
      { path: '/profil', element: <ProfilPage /> },
      { path: '/administration/utilisateurs', element: <AdminUsersPage /> },
      { path: '/administration/societes', element: <AdminEntitiesPage /> },
      {
        path: '/administration/comptes-bancaires',
        element: <AdminBankAccountsPage />,
      },
    ],
  },
]);
