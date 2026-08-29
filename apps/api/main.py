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
from psycopg.rows import dict_row

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


@app.get("/ingestion/status")
def ingestion_status():
    """Fase 2 - última corrida de ingestão por (source, entity). Usado pelo
    dashboard para mostrar o estado do Data Hub sem expor a base de dados."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (source, entity)
                    source, entity, status, records_processed, error_message,
                    started_at, finished_at
                FROM raw.ingestion_log
                ORDER BY source, entity, started_at DESC
                """
            )
            rows = cur.fetchall()
    return {"runs": rows}


@app.get("/analytics/metrics")
def analytics_metrics():
    """Fase 3 - métricas mais recentes calculadas pelos Analyzers."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT metric, value, change, period, status, computed_at
                FROM analytics.metrics
                ORDER BY period DESC, metric
                """
            )
            rows = cur.fetchall()
    return {"metrics": rows}


@app.get("/analytics/anomalies")
def analytics_anomalies():
    """Fase 3 - anomalias detetadas pelo Anomaly Engine (desvios face ao
    histórico de cada métrica)."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT metric, period, expected_value, actual_value,
                       deviation_pct, z_score, severity, confidence, detected_at
                FROM analytics.anomalies
                ORDER BY detected_at DESC
                """
            )
            rows = cur.fetchall()
    return {"anomalies": rows}


@app.get("/analytics/forecasts")
def analytics_forecasts():
    """Fase 3 - previsões do Prediction Engine, incluindo actual_result
    quando o período previsto já tiver dados reais (compare previsto vs real)."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT metric, forecast_period, predicted_value, confidence,
                       model, actual_result, created_at
                FROM analytics.forecasts
                ORDER BY forecast_period DESC, metric
                """
            )
            rows = cur.fetchall()
    return {"forecasts": rows}


@app.get("/intelligence/insights")
def intelligence_insights():
    """Fase 5 - insights gerados pelo LLM a partir das métricas já calculadas."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT period, insight_text, model, created_at
                FROM intelligence.insights
                ORDER BY period DESC
                """
            )
            rows = cur.fetchall()
    return {"insights": rows}


@app.get("/tasks")
def list_tasks():
    """Fase 6 - tarefas geradas a partir dos insights, com o estado de automação."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, description, priority, category, source,
                       status, automation_type, expected_impact, period, created_at
                FROM tasks.business_tasks
                ORDER BY created_at DESC
                """
            )
            rows = cur.fetchall()
    return {"tasks": rows}


@app.get("/webstudio/overview")
def webstudio_overview():
    """Funil da Webstudio. Tabelas vazias por agora (sem backend/connector
    ligado ainda) - devolve zeros de propósito, não é erro."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM core.leads")
            leads_total = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.leads WHERE qualification IS NOT NULL")
            leads_qualified = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.proposals")
            proposals_total = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.proposals WHERE status = 'accepted'")
            proposals_accepted = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.projects WHERE status = 'active'")
            projects_active = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.projects WHERE status = 'completed'")
            projects_completed = cur.fetchone()["n"]

            cur.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM core.revenue_transactions WHERE revenue_type = 'AGENCY_SERVICE'"
            )
            revenue_total = cur.fetchone()["total"]

            cur.execute(
                "SELECT COALESCE(SUM(value), 0) AS total FROM core.proposals WHERE status = 'sent'"
            )
            pipeline_value = cur.fetchone()["total"]

    return {
        "leads_total": leads_total,
        "leads_qualified": leads_qualified,
        "proposals_total": proposals_total,
        "proposals_accepted": proposals_accepted,
        "projects_active": projects_active,
        "projects_completed": projects_completed,
        "revenue_total": revenue_total,
        "pipeline_value": pipeline_value,
    }
