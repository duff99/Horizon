import { reportApiError } from '@/lib/errorReporter';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

/**
 * Payload structuré renvoyé par certains endpoints (ex. DELETE
 * /api/categories) pour permettre au front d'afficher une UI riche
 * (compteurs, code d'erreur). Toujours accompagné d'un champ `message`
 * lisible côté `ApiError.detail`.
 */
export interface ApiErrorData {
  code?: string;
  [k: string]: unknown;
}

export class ApiError extends Error {
  /** Texte lisible pour affichage utilisateur (toujours un string). */
  public detail: string;
  /** Payload structuré quand le backend renvoie un objet (sinon undefined). */
  public data?: ApiErrorData;

  constructor(status: number, detail: unknown) {
    let message: string;
    let data: ApiErrorData | undefined;
    if (typeof detail === 'string') {
      message = detail;
    } else if (detail && typeof detail === 'object') {
      const obj = detail as ApiErrorData & { message?: unknown };
      message = typeof obj.message === 'string' ? obj.message : 'Erreur API';
      data = obj;
    } else {
      message = 'Erreur API';
    }
    super(message);
    this.status = status;
    this.detail = message;
    this.data = data;
  }

  public status: number;
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
    let detail: unknown = res.statusText;
    try {
      const body = await res.json();
      if (body && body.detail !== undefined) detail = body.detail;
    } catch {
      /* ignore */
    }
    const reportedDetail =
      typeof detail === 'string'
        ? detail
        : detail && typeof detail === 'object' && 'message' in detail &&
            typeof (detail as { message?: unknown }).message === 'string'
          ? (detail as { message: string }).message
          : JSON.stringify(detail);
    // Remontée auto au backend pour 5xx (4xx restent silencieux côté reporter
    // — c'est de l'attendu : 401, 403, 422 sur input invalide, etc.).
    reportApiError({
      status: res.status,
      detail: reportedDetail,
      path,
      request_id: res.headers.get('X-Request-ID') ?? undefined,
    });
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
