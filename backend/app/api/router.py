from fastapi import APIRouter

from app.api import auth, bank_accounts, bootstrap, entities, health, imports, me, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(bootstrap.router)
api_router.include_router(users.router)
api_router.include_router(entities.router)
api_router.include_router(bank_accounts.router)
api_router.include_router(imports.router)
