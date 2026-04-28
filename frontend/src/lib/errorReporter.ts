/**
 * errorReporter — capture et envoi des erreurs frontend au backend.
 *
 * Couvre 4 sources :
 * 1. window.onerror               — exceptions JS non capturées
 * 2. unhandledrejection           — promesses rejetées non capturées
 * 3. console.error                — appels explicites (wrapper)
 * 4. apifetch                     — exceptions ApiError remontant des hooks
 *    (envoyé par api/client.ts via reportApiError)
 *
 * L'envoi est best-effort : on ignore les échecs réseau / 5xx pour ne pas
 * créer de boucle (reporter qui plante → reporter qui plante → ...).
 *
 * On dédoublonne sur (message + stack) sur 5 secondes pour éviter de saturer
 * le backend si une erreur boucle (ex: render qui re-throw à chaque tick).
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

type Severity = 'debug' | 'info' | 'warning' | 'error' | 'fatal';
type Source =
  | 'window.onerror'
  | 'unhandledrejection'
  | 'console.error'
  | 'apifetch'
  | 'manual';

interface ReportInput {
  severity?: Severity;
  source: Source;
  message: string;
  stack?: string;
  url?: string;
  request_id?: string;
  context_json?: Record<string, unknown>;
}

const recentlySent = new Map<string, number>();
const DEDUP_WINDOW_MS = 5000;
const MAX_RECENT = 200;

function isDuplicate(key: string): boolean {
  const now = Date.now();
  // Garbage-collect les vieilles entrées
  if (recentlySent.size > MAX_RECENT) {
    for (const [k, t] of recentlySent) {
      if (now - t > DEDUP_WINDOW_MS) recentlySent.delete(k);
    }
  }
  const last = recentlySent.get(key);
  if (last !== undefined && now - last < DEDUP_WINDOW_MS) return true;
  recentlySent.set(key, now);
  return false;
}

async function send(input: ReportInput): Promise<void> {
  const key = `${input.source}|${input.message}|${input.stack ?? ''}`;
  if (isDuplicate(key)) return;

  const body = {
    severity: input.severity ?? 'error',
    source: input.source,
    message: (input.message ?? '').slice(0, 4000),
    stack: input.stack?.slice(0, 20000),
    url: (input.url ?? window.location.href).slice(0, 2000),
    user_agent: navigator.userAgent.slice(0, 500),
    request_id: input.request_id?.slice(0, 64),
    context_json: input.context_json ?? null,
  };

  try {
    await fetch(`${BASE_URL}/api/client-errors`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      // Best-effort : on ignore les délais (ne bloque pas la page)
      keepalive: true,
    });
  } catch {
    // Silencieux : pas de boucle reporter→reporter
  }
}

export function reportError(input: ReportInput): void {
  // fire-and-forget
  void send(input);
}

let initialized = false;

export function initErrorReporter(): void {
  if (initialized || typeof window === 'undefined') return;
  initialized = true;

  window.addEventListener('error', (event) => {
    const error = event.error;
    reportError({
      source: 'window.onerror',
      severity: 'error',
      message:
        error?.message ??
        event.message ??
        'Erreur JS inconnue',
      stack: error?.stack,
      url: event.filename
        ? `${window.location.href} (${event.filename}:${event.lineno}:${event.colno})`
        : undefined,
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    let message = 'Promise rejetée';
    let stack: string | undefined;
    if (reason instanceof Error) {
      message = reason.message;
      stack = reason.stack;
    } else if (typeof reason === 'string') {
      message = reason;
    } else if (reason && typeof reason === 'object') {
      try {
        message = JSON.stringify(reason).slice(0, 4000);
      } catch {
        message = String(reason);
      }
    }
    reportError({
      source: 'unhandledrejection',
      severity: 'error',
      message,
      stack,
    });
  });

  // Wrapper console.error : on garde le comportement natif (log dans la
  // console du navigateur) ET on envoie au backend.
  const originalConsoleError = console.error;
  console.error = (...args: unknown[]): void => {
    originalConsoleError.apply(console, args);
    try {
      const message = args
        .map((a) => {
          if (a instanceof Error) return a.message;
          if (typeof a === 'string') return a;
          try {
            return JSON.stringify(a);
          } catch {
            return String(a);
          }
        })
        .join(' ')
        .slice(0, 4000);
      const firstError = args.find((a): a is Error => a instanceof Error);
      reportError({
        source: 'console.error',
        severity: 'error',
        message,
        stack: firstError?.stack,
      });
    } catch {
      /* ignore */
    }
  };
}

/**
 * Hook utilisable depuis api/client.ts pour signaler une ApiError ≥ 500
 * ou une erreur réseau côté apiFetch sans dépendance circulaire.
 */
export function reportApiError(input: {
  status: number;
  detail: string;
  path: string;
  request_id?: string;
}): void {
  // 4xx attendus côté UI (validation, 401, 403) — pas de remontée auto
  if (input.status >= 400 && input.status < 500) return;
  reportError({
    source: 'apifetch',
    severity: input.status >= 500 ? 'error' : 'warning',
    message: `${input.status} ${input.detail} on ${input.path}`,
    request_id: input.request_id,
    context_json: { status: input.status, path: input.path },
  });
}
