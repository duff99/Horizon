#!/usr/bin/env bash
# show-client-errors.sh — interroge la table client_errors et affiche un
# résumé lisible. Outil de debug pour Claude (pas pour les utilisateurs).
#
# Usage :
#   ./scripts/dev/show-client-errors.sh [options]
#
# Options :
#   --since <duration>   ex: 1h, 24h, 30m, 7d (défaut: 1h)
#   --url <substring>    filtre les erreurs dont l'url contient ce substring
#                        (ex: --url /analyse, --url /administration/sauvegardes)
#   --user <email>       filtre par email utilisateur
#   --source <source>    filtre par source (window.onerror, unhandledrejection,
#                        console.error, apifetch, manual)
#   --severity <sev>     filtre par sévérité (debug, info, warning, error, fatal)
#   --limit <n>          nombre max d'erreurs à afficher (défaut: 50)
#   --full               affiche les stack traces complètes (sinon tronquées 200c)
#
# Exemples :
#   ./show-client-errors.sh                              # toutes les erreurs < 1h
#   ./show-client-errors.sh --url /analyse --since 24h   # erreurs Analyse < 24h
#   ./show-client-errors.sh --severity fatal --since 7d  # fatales < 7j
#
# Exit codes : 0 = OK (avec ou sans erreurs trouvées), 1 = problème DB.

set -euo pipefail

DB_CONTAINER="horizon-db-1"
DB_USER="tresorerie"
DB_NAME="tresorerie"

SINCE="1 hour"
URL_FILTER=""
USER_FILTER=""
SOURCE_FILTER=""
SEVERITY_FILTER=""
LIMIT=50
FULL_STACK=false

# Parse durée → INTERVAL Postgres
parse_since() {
  local raw="$1"
  case "$raw" in
    *m) echo "${raw%m} minutes" ;;
    *h) echo "${raw%h} hours" ;;
    *d) echo "${raw%d} days" ;;
    *) echo "$raw" ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --since) SINCE="$(parse_since "$2")"; shift 2 ;;
    --url) URL_FILTER="$2"; shift 2 ;;
    --user) USER_FILTER="$2"; shift 2 ;;
    --source) SOURCE_FILTER="$2"; shift 2 ;;
    --severity) SEVERITY_FILTER="$2"; shift 2 ;;
    --limit) LIMIT="$2"; shift 2 ;;
    --full) FULL_STACK=true; shift ;;
    -h|--help)
      grep -E '^# ' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

# Construit la clause WHERE
WHERE="ce.occurred_at > now() - interval '$SINCE'"
if [[ -n "$URL_FILTER" ]]; then
  esc="${URL_FILTER//\'/\'\'}"
  WHERE="$WHERE AND ce.url ILIKE '%$esc%'"
fi
if [[ -n "$USER_FILTER" ]]; then
  esc="${USER_FILTER//\'/\'\'}"
  WHERE="$WHERE AND u.email = '$esc'"
fi
if [[ -n "$SOURCE_FILTER" ]]; then
  esc="${SOURCE_FILTER//\'/\'\'}"
  WHERE="$WHERE AND ce.source = '$esc'"
fi
if [[ -n "$SEVERITY_FILTER" ]]; then
  esc="${SEVERITY_FILTER//\'/\'\'}"
  WHERE="$WHERE AND ce.severity = '$esc'"
fi

# Compteur global
TOTAL=$(docker exec "$DB_CONTAINER" psql -q -U "$DB_USER" -d "$DB_NAME" -At -c "
  SELECT count(*)
  FROM client_errors ce
  LEFT JOIN users u ON u.id = ce.user_id
  WHERE $WHERE;
" 2>/dev/null | head -n1)

echo "─── client_errors (depuis $SINCE) ───"
echo "Filtres : url=${URL_FILTER:-*} user=${USER_FILTER:-*} source=${SOURCE_FILTER:-*} severity=${SEVERITY_FILTER:-*}"
echo "Total trouvé : $TOTAL  |  affichés : $(( TOTAL > LIMIT ? LIMIT : TOTAL ))"
echo

if [[ "$TOTAL" == "0" ]]; then
  echo "✓ Aucune erreur sur la fenêtre demandée."
  exit 0
fi

# Top URLs (résumé) si plus de 5 erreurs
if [[ "$TOTAL" -ge 5 ]]; then
  echo "─── Top URLs touchées ───"
  docker exec "$DB_CONTAINER" psql -q -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT split_part(ce.url, '?', 1) AS path, count(*) AS n
    FROM client_errors ce
    LEFT JOIN users u ON u.id = ce.user_id
    WHERE $WHERE
    GROUP BY 1 ORDER BY 2 DESC LIMIT 10;
  " 2>&1
  echo
  echo "─── Top messages ───"
  docker exec "$DB_CONTAINER" psql -q -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT substring(ce.message from 1 for 80) AS message, count(*) AS n
    FROM client_errors ce
    LEFT JOIN users u ON u.id = ce.user_id
    WHERE $WHERE
    GROUP BY 1 ORDER BY 2 DESC LIMIT 10;
  " 2>&1
  echo
fi

echo "─── Détail (50 max, plus récent en premier) ───"
STACK_LEN=200
if [[ "$FULL_STACK" == "true" ]]; then
  STACK_LEN=20000
fi

docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
  SELECT
    to_char(ce.occurred_at, 'YYYY-MM-DD HH24:MI:SS') AS at,
    ce.severity AS sev,
    ce.source,
    COALESCE(u.email, '(anonyme)') AS user_email,
    substring(ce.url from 1 for 80) AS url,
    substring(ce.message from 1 for 200) AS message,
    CASE
      WHEN ce.stack IS NULL THEN ''
      ELSE substring(ce.stack from 1 for $STACK_LEN)
    END AS stack
  FROM client_errors ce
  LEFT JOIN users u ON u.id = ce.user_id
  WHERE $WHERE
  ORDER BY ce.occurred_at DESC
  LIMIT $LIMIT;
" 2>&1
