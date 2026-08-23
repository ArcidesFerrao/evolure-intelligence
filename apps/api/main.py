"""
Fase 1 - Foundation
API mínima só para validar que o Docker Compose está tudo a comunicar:
FastAPI <-> PostgreSQL, e que o dashboard consegue chamar a API.

Nada de lógica de negócio aqui ainda - isso entra na Fase 2 (Data Hub)
e Fase 3 (Analytics Engine).
"""
import os
import logging
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Header, HTTPException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evolure.api")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "")


def check_db() -> bool:
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("DB check failed: %s", exc)
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Evolure Intelligence API a arrancar...")
    yield
    logger.info("Evolure Intelligence API a desligar...")


app = FastAPI(title="Evolure Intelligence API", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    """Endpoint de saude: usado pelo docker-compose e por monitorização futura."""
    db_ok = check_db()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
    }


def require_internal_key(x_internal_key: str = Header(default="")):
    """Autenticação simples entre serviços internos (dashboard/workers -> api).
    Não substitui autenticação de utilizador final - isso é NextAuth no dashboard.
    """
    if not INTERNAL_API_KEY or x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Chave interna inválida ou ausente")
    return True


@app.get("/internal/ping")
def internal_ping(_: bool = require_internal_key):  # pragma: no cover - smoke endpoint
    """Confirma que a chave interna funciona antes de construirmos os connectors reais."""
    return {"pong": True}
