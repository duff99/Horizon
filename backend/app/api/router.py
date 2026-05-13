from fastapi import APIRouter

from app.api import (
    admin_audit,
    admin_backups,
    admin_client_errors,
    analysis,
    anomaly,
    auth,
    bank_accounts,
    bootstrap,
    categories,
    client_errors,
    commitments,
    counterparties,
    dashboard,
    drift_acks,
    entities,
    forecast,
    forecast_comparison,
    forecast_lines,
    forecast_pivot,
    forecast_scenarios,
    health,
    imports,
    me,
    rules,
    transactions,
    treasury,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)

# Alias legacy : /healthz à la racine pour les sondes nginx / kubelet existantes
# qui ne passent pas par le préfixe /api.
root_router = APIRouter()


@root_router.get("/healthz", include_in_schema=False, tags=["health"])
def healthz_legacy() -> dict[str, str]:
    """Alias de /api/healthz pour les sondes qui ne connaissent pas le préfixe /api."""
    return health.healthz()
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(bootstrap.router)
api_router.include_router(users.router)
api_router.include_router(entities.router)
api_router.include_router(bank_accounts.router)
api_router.include_router(imports.router)
api_router.include_router(transactions.router)
api_router.include_router(counterparties.router)
api_router.include_router(rules.router)
api_router.include_router(categories.router)
api_router.include_router(dashboard.router)
api_router.include_router(forecast.router)
api_router.include_router(forecast_scenarios.router)
api_router.include_router(forecast_lines.router)
api_router.include_router(forecast_pivot.router)
api_router.include_router(forecast_comparison.router)
api_router.include_router(commitments.router)
api_router.include_router(analysis.router)
api_router.include_router(admin_backups.router)
api_router.include_router(admin_audit.router)
api_router.include_router(client_errors.router)
api_router.include_router(admin_client_errors.router)
api_router.include_router(treasury.router)
api_router.include_router(drift_acks.router)
api_router.include_router(anomaly.router)
# Note : admin_backups inclut aussi /disk et /trigger (mêmes prefix /api/admin/backups)
