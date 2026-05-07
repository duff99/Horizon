import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { AdminRoute } from '@/components/AdminRoute';

const useMeMock = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useMe: () => useMeMock(),
}));

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/connexion" element={<div>LOGIN</div>} />
          <Route path="/tableau-de-bord" element={<div>HOME</div>} />
          <Route
            path="/administration/utilisateurs"
            element={
              <AdminRoute>
                <div>ADMIN_OK</div>
              </AdminRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AdminRoute', () => {
  beforeEach(() => useMeMock.mockReset());

  it('shows loading while me is loading', () => {
    useMeMock.mockReturnValue({ isLoading: true, isError: false, data: null });
    renderAt('/administration/utilisateurs');
    expect(screen.getByText(/Chargement/)).toBeInTheDocument();
  });

  it('redirects to login when not authenticated', () => {
    useMeMock.mockReturnValue({ isLoading: false, isError: true, data: null });
    renderAt('/administration/utilisateurs');
    expect(screen.getByText('LOGIN')).toBeInTheDocument();
  });

  it('redirects reader to dashboard', () => {
    useMeMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: { id: 7, email: 'r@x', role: 'reader', fullName: 'R' },
    });
    renderAt('/administration/utilisateurs');
    expect(screen.getByText('HOME')).toBeInTheDocument();
    expect(screen.queryByText('ADMIN_OK')).toBeNull();
  });

  it('renders admin content for admin role', () => {
    useMeMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: { id: 1, email: 'a@x', role: 'admin', fullName: 'A' },
    });
    renderAt('/administration/utilisateurs');
    expect(screen.getByText('ADMIN_OK')).toBeInTheDocument();
  });
});
