/**
 * Utilitaires d'export CSV pour les pages Horizon (G11).
 *
 * `downloadExport` : déclenche un téléchargement de fichier sans ouvrir un
 * nouvel onglet. Passe par fetch avec credentials pour respecter la session
 * cookie (contrairement à un simple <a href>).
 *
 * openpyxl est absent du container prod actuel → seul le format CSV est
 * exposé dans l'interface. Les fonctions ci-dessous supportent le paramètre
 * format pour le jour où XLSX sera disponible.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type ExportFormat = "csv";
// XLSX différé (openpyxl absent en prod) : "csv" | "xlsx"

/**
 * Télécharge un export depuis l'URL donnée et déclenche le téléchargement
 * navigateur avec le filename fourni.
 *
 * @param url    URL relative du backend (ex: "/api/transactions/export?entity_id=1")
 * @param filename Nom de fichier suggéré (ex: "transactions_2026-05-07.csv")
 */
export async function downloadExport(url: string, filename: string): Promise<void> {
  const resp = await fetch(`${BASE_URL}${url}`, {
    credentials: "include",
  });

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // ignore
    }
    throw new Error(`Erreur export (${resp.status}) : ${detail}`);
  }

  const blob = await resp.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(href);
}

/**
 * Construit la date du jour au format ISO (YYYY-MM-DD) pour les noms de
 * fichiers d'export.
 */
export function todayISO(): string {
  return new Date().toISOString().split("T")[0];
}
