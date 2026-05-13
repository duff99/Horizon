import { lazy, type ComponentType } from "react";

const RELOAD_FLAG = "horizon:chunk-reload-attempt";
const CHUNK_ERROR_REGEX =
  /Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed|Loading chunk \d+ failed/i;

/**
 * Wraps `React.lazy` to recover from stale-chunk errors after a deploy.
 *
 * Vite émet des chunks fingerprintés (`AdminUsersPage-BsW0Mqoa.js`). Un
 * utilisateur qui avait l'onglet ouvert au moment du `docker compose build`
 * détient l'index pré-build mais demandera des chunks supprimés → 404 → l'app
 * affiche "Unexpected Application Error". Plutôt que de laisser planter, on
 * recharge la page une fois (le nouvel index.html référence les bons hash).
 *
 * Garde-fou : sessionStorage flag pour ne pas boucler si le reload ne suffit
 * pas (ex. réseau réellement coupé).
 */
export function lazyWithReload<T extends ComponentType<unknown>>(
  loader: () => Promise<{ default: T }>,
): ReturnType<typeof lazy<T>> {
  return lazy(async () => {
    try {
      const mod = await loader();
      sessionStorage.removeItem(RELOAD_FLAG);
      return mod;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const isChunkError = CHUNK_ERROR_REGEX.test(message);
      const alreadyTried = sessionStorage.getItem(RELOAD_FLAG);
      if (isChunkError && !alreadyTried) {
        sessionStorage.setItem(RELOAD_FLAG, String(Date.now()));
        window.location.reload();
        return new Promise<{ default: T }>(() => {});
      }
      throw err;
    }
  });
}
