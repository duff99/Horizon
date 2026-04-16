import { createBrowserRouter, Navigate } from 'react-router-dom';

import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AdminBankAccountsPage } from '@/pages/AdminBankAccountsPage';
import { AdminEntitiesPage } from '@/pages/AdminEntitiesPage';
import { AdminUsersPage } from '@/pages/AdminUsersPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { LoginPage } from '@/pages/LoginPage';

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
      { path: '/administration/utilisateurs', element: <AdminUsersPage /> },
      { path: '/administration/societes', element: <AdminEntitiesPage /> },
      {
        path: '/administration/comptes-bancaires',
        element: <AdminBankAccountsPage />,
      },
    ],
  },
]);
