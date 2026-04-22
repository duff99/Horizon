import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import { ProfilPage } from '@/pages/ProfilPage';

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
}));

const mutateAsync = vi.fn().mockResolvedValue(undefined);
vi.mock('@/api/password', () => ({
  useChangeOwnPassword: () => ({
    mutateAsync,
    isPending: false,
  }),
}));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ProfilPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProfilPage', () => {
  it('renders email and full name', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: /mon profil/i })).toBeInTheDocument();
    expect(screen.getByText('tdufr@example.com')).toBeInTheDocument();
    expect(screen.getByText('Tristan Dufour')).toBeInTheDocument();
  });

  it('shows client error when new password is too short', async () => {
    renderPage();
    fireEvent.change(screen.getByLabelText(/mot de passe actuel/i), {
      target: { value: 'oldpassword12' },
    });
    fireEvent.change(screen.getByLabelText(/^Nouveau mot de passe/i), {
      target: { value: 'short' },
    });
    fireEvent.change(screen.getByLabelText(/confirmer le nouveau/i), {
      target: { value: 'short' },
    });
    fireEvent.click(screen.getByRole('button', { name: /mettre à jour/i }));
    await waitFor(() => {
      expect(screen.getByText('Minimum 12 caractères')).toBeInTheDocument();
    });
  });

  it('submits and shows success message on happy path', async () => {
    mutateAsync.mockResolvedValueOnce(undefined);
    renderPage();
    fireEvent.change(screen.getByLabelText(/mot de passe actuel/i), {
      target: { value: 'oldpassword12' },
    });
    fireEvent.change(screen.getByLabelText(/^Nouveau mot de passe/i), {
      target: { value: 'newpassword1234' },
    });
    fireEvent.change(screen.getByLabelText(/confirmer le nouveau/i), {
      target: { value: 'newpassword1234' },
    });
    fireEvent.click(screen.getByRole('button', { name: /mettre à jour/i }));
    await waitFor(() => {
      expect(screen.getByText('Mot de passe mis à jour')).toBeInTheDocument();
    });
    expect(mutateAsync).toHaveBeenCalledWith({
      current_password: 'oldpassword12',
      new_password: 'newpassword1234',
    });
  });
});
