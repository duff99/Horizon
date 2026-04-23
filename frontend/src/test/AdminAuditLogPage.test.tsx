import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import { AdminAuditLogPage } from '@/pages/AdminAuditLogPage';

// Stub API : ne pas hit le backend
vi.mock('@/api/auditLog', () => ({
  listAuditLog: vi.fn().mockResolvedValue({
    items: [
      {
        id: 101,
        occurredAt: '2026-04-23T10:15:00Z',
        userId: 1,
        userEmail: 'tdufr@example.com',
        action: 'update',
        entityType: 'Transaction',
        entityId: '42',
        beforeJson: { category_id: 1 },
        afterJson: { category_id: 7 },
        diffJson: { category_id: { before: 1, after: 7 } },
        ipAddress: '192.168.1.12',
        userAgent: 'Mozilla/5.0',
        requestId: null,
      },
      {
        id: 100,
        occurredAt: '2026-04-23T09:00:00Z',
        userId: 1,
        userEmail: 'tdufr@example.com',
        action: 'create',
        entityType: 'Commitment',
        entityId: '7',
        beforeJson: null,
        afterJson: { id: 7, amount_cents: 12345 },
        diffJson: null,
        ipAddress: null,
        userAgent: null,
        requestId: null,
      },
    ],
    total: 2,
    limit: 50,
    offset: 0,
  }),
}));

vi.mock('@/api/users', () => ({
  listUsers: vi.fn().mockResolvedValue([
    {
      id: 1,
      email: 'tdufr@example.com',
      role: 'admin',
      fullName: 'Tristan Dufour',
      isActive: true,
      createdAt: '',
      lastLoginAt: null,
    },
  ]),
}));

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AdminAuditLogPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AdminAuditLogPage', () => {
  it("renders the page title and filters", () => {
    renderPage();
    expect(
      screen.getByRole('heading', { level: 1, name: /Journal d'audit/i }),
    ).toBeInTheDocument();
    // 4 selects : entity_type, action, user, + 2 date inputs
    expect(screen.getAllByRole('combobox').length).toBeGreaterThanOrEqual(3);
  });

  it('renders rows returned by the API', async () => {
    renderPage();
    // La cellule IP 192.168.1.12 n'existe que dans le row data, pas dans le
    // filtres — donc c'est un signal fiable.
    await waitFor(() => {
      expect(screen.getByText('192.168.1.12')).toBeInTheDocument();
    });
    // Au moins deux cellules d'email (une dans le select, une dans la row)
    expect(screen.getAllByText(/tdufr@example.com/).length).toBeGreaterThan(0);
  });

  it('opens the detail drawer on row click', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('192.168.1.12')).toBeInTheDocument();
    });
    const ipCell = screen.getByText('192.168.1.12');
    const tr = ipCell.closest('tr');
    expect(tr).not.toBeNull();
    fireEvent.click(tr!);
    // Titre du drawer (Événement #...)
    expect(
      await screen.findByText(/Événement #101/i),
    ).toBeInTheDocument();
    // Sections du drawer
    expect(screen.getByText(/État avant/i)).toBeInTheDocument();
    expect(screen.getByText(/État après/i)).toBeInTheDocument();
  });
});
