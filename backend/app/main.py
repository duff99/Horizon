from fastapi import FastAPI

app = FastAPI(
    title="Outil de trésorerie",
    description="API de l'outil de gestion de trésorerie auto-hébergé",
    version="0.1.0",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "name": "tresorerie-backend"}
