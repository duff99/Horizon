/**
 * Tests unitaires pour AdminClientErrorsPage.
 * Vérifie : rendu, bandeau d'introduction, affichage des données, bouton acquittement.
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AdminClientErrorsPage } from "./AdminClientErrorsPage";
import * as clientErrorsApi from "@/api/clientErrors";

// Mock du module API complet
vi.mock("@/api/clientErrors", async (importOriginal) => {
  const actual = await importOriginal<typeof clientErrorsApi>();
  return {
    ...actual,
    useClientErrors: vi.fn(),
    useAcknowledgeClientError: vi.fn(),
  };
});

const mockItem = {
  id: 1,
  occurred_at: "2026-05-07T10:00:00Z",
  user_id: 42,
  user_email: "user@example.com",
  severity: "error",
  source: "browser",
  message: "Uncaught TypeError: Cannot read property",
  stack: null,
  url: "/transactions",
  user_agent: null,
  request_id: null,
  context_json: null,
  acknowledged_at: null,
};

const mockAckedItem = {
  ...mockItem,
  id: 2,
  acknowledged_at: "2026-05-07T11:00:00Z",
};

function Wrapped() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <AdminClientErrorsPage />
    </QueryClientProvider>
  );
}

describe("AdminClientErrorsPage", () => {
  beforeEach(() => {
    vi.mocked(clientErrorsApi.useAcknowledgeClientError).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof clientErrorsApi.useAcknowledgeClientError>);
  });

  it("affiche le bandeau d'introduction permanent", () => {
    vi.mocked(clientErrorsApi.useClientErrors).mockReturnValue({
      data: { items: [], total: 0, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof clientErrorsApi.useClientErrors>);

    render(<Wrapped />);
    expect(screen.getByRole("note")).toBeInTheDocument();
    expect(
      screen.getByText(/erreurs JavaScript survenues dans le navigateur/i),
    ).toBeInTheDocument();
  });

  it("affiche une ligne d'erreur avec badge A traiter", () => {
    vi.mocked(clientErrorsApi.useClientErrors).mockReturnValue({
      data: { items: [mockItem], total: 1, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof clientErrorsApi.useClientErrors>);

    render(<Wrapped />);
    expect(screen.getByText("user@example.com")).toBeInTheDocument();
    expect(screen.getByText(/A traiter/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Marquer acquitte/i }),
    ).toBeInTheDocument();
  });

  it("affiche badge Acquitte et masque le bouton si acknowledged_at non null", () => {
    vi.mocked(clientErrorsApi.useClientErrors).mockReturnValue({
      data: { items: [mockAckedItem], total: 1, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof clientErrorsApi.useClientErrors>);

    render(<Wrapped />);
    // Le tableau contient au moins un badge "Acquitte" (span dans le td Statut)
    const badges = screen.getAllByText(/^Acquitte$/i);
    expect(badges.length).toBeGreaterThan(0);
    expect(
      screen.queryByRole("button", { name: /Marquer acquitte/i }),
    ).not.toBeInTheDocument();
  });

  it("appelle mutate lors du clic sur Marquer acquitte", () => {
    const mutateFn = vi.fn();
    vi.mocked(clientErrorsApi.useAcknowledgeClientError).mockReturnValue({
      mutate: mutateFn,
      isPending: false,
    } as unknown as ReturnType<typeof clientErrorsApi.useAcknowledgeClientError>);

    vi.mocked(clientErrorsApi.useClientErrors).mockReturnValue({
      data: { items: [mockItem], total: 1, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof clientErrorsApi.useClientErrors>);

    render(<Wrapped />);
    fireEvent.click(screen.getByRole("button", { name: /Marquer acquitte/i }));
    expect(mutateFn).toHaveBeenCalledWith(1);
  });

  it("affiche un message si aucune erreur ne correspond aux filtres", () => {
    vi.mocked(clientErrorsApi.useClientErrors).mockReturnValue({
      data: { items: [], total: 0, limit: 50, offset: 0 },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof clientErrorsApi.useClientErrors>);

    render(<Wrapped />);
    expect(
      screen.getByText(/aucune erreur ne correspond aux filtres/i),
    ).toBeInTheDocument();
  });

  it("affiche un etat de chargement", () => {
    vi.mocked(clientErrorsApi.useClientErrors).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof clientErrorsApi.useClientErrors>);

    render(<Wrapped />);
    expect(screen.getByText(/Chargement/i)).toBeInTheDocument();
  });
});
