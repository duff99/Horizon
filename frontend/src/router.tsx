import { createBrowserRouter, Navigate } from 'react-router-dom';

import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AdminBankAccountsPage } from '@/pages/AdminBankAccountsPage';
import { AdminEntitiesPage } from '@/pages/AdminEntitiesPage';
import { AdminUsersPage } from '@/pages/AdminUsersPage';
import { CounterpartiesPage } from '@/pages/CounterpartiesPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { ImportHistoryPage } from '@/pages/ImportHistoryPage';
import { ImportNewPage } from '@/pages/ImportNewPage';
import { LoginPage } from '@/pages/LoginPage';
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
      { path: '/imports', element: <ImportHistoryPage /> },
      { path: '/imports/nouveau', element: <ImportNewPage /> },
      { path: '/transactions', element: <TransactionsPage /> },
      { path: '/contreparties', element: <CounterpartiesPage /> },
      { path: '/administration/utilisateurs', element: <AdminUsersPage /> },
      { path: '/administration/societes', element: <AdminEntitiesPage /> },
      {
        path: '/administration/comptes-bancaires',
        element: <AdminBankAccountsPage />,
      },
    ],
  },
]);
