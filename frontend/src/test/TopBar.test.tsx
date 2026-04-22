import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import { TopBar } from '@/components/TopBar';
import { useEntityFilter } from '@/stores/entityFilter';

vi.mock('@/api/entities', () => ({
  useEntities: () => ({
    data: [
      { id: 1, name: 'ACREED', legalName: 'ACREED SAS', siret: null, parentEntityId: null, createdAt: '' },
      { id: 2, name: 'Filiale', legalName: 'Filiale SAS', siret: null, parentEntityId: null, createdAt: '' },
    ],
    isLoading: false,
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useMe: () => ({
    data: {
      id: 1,
      email: 'tdufr@example.com',
      role: 'admin',
      fullName: 'Tristan Dufour',
      isActive: true,
      createdAt: '',
      lastLoginAt: null,
    },
  }),
  useLogout: () => ({ mutate: vi.fn() }),
}));

function renderTopBar() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <TopBar />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('TopBar', () => {
  beforeEach(() => {
    localStorage.clear();
    useEntityFilter.setState({ entityId: null });
  });

  it('renders the entity selector placeholder', () => {
    renderTopBar();
    expect(screen.getByText('Toutes les sociétés')).toBeInTheDocument();
  });

  it('displays the current user', () => {
    renderTopBar();
    expect(screen.getByTestId('topbar-user')).toHaveTextContent('Tristan Dufour');
  });

  it('exposes a logout action and profile link', () => {
    renderTopBar();
    expect(screen.getByRole('button', { name: /se déconnecter/i })).toBeInTheDocument();
    const profileLink = screen.getByRole('link', { name: /mon profil/i });
    expect(profileLink).toHaveAttribute('href', '/profil');
  });
});
