import { reportApiError } from '@/lib/errorReporter';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(init.headers ?? {}),
      },
      ...init,
    });
  } catch (networkError) {
    // Erreur réseau (offline, DNS, CORS...). On remonte au backend (best-effort
    // : si le backend est lui-même injoignable, le reporter avalera l'erreur).
    const message =
      networkError instanceof Error
        ? networkError.message
        : 'Erreur réseau inconnue';
    reportApiError({
      status: 0,
      detail: `Network error: ${message}`,
      path,
    });
    throw new ApiError(0, message);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    // Remontée auto au backend pour 5xx (4xx restent silencieux côté reporter
    // — c'est de l'attendu : 401, 403, 422 sur input invalide, etc.).
    reportApiError({
      status: res.status,
      detail,
      path,
      request_id: res.headers.get('X-Request-ID') ?? undefined,
    });
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
