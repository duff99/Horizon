from fastapi import APIRouter

from app.api import (
    admin_audit,
    admin_backups,
    admin_client_errors,
    analysis,
    auth,
    bank_accounts,
    bootstrap,
    categories,
    client_errors,
    commitments,
    counterparties,
    dashboard,
    entities,
    forecast,
    forecast_lines,
    forecast_pivot,
    forecast_scenarios,
    health,
    imports,
    me,
    rules,
    transactions,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
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
api_router.include_router(commitments.router)
api_router.include_router(analysis.router)
api_router.include_router(admin_backups.router)
api_router.include_router(admin_audit.router)
api_router.include_router(client_errors.router)
api_router.include_router(admin_client_errors.router)
