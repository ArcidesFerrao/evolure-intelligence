"""
Fase 1 - Foundation
API mínima só para validar que o Docker Compose está tudo a comunicar:
FastAPI <-> PostgreSQL, e que o dashboard consegue chamar a API.

Nada de lógica de negócio aqui ainda - isso entra na Fase 2 (Data Hub)
e Fase 3 (Analytics Engine).
"""
import os
import sys
import logging
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Header, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel

# WORKDIR do container é /monorepo/apps/api - isso NÃO põe /monorepo no
# sys.path automaticamente (só a própria pasta entra via CWD). Sem isto,
# "from actions import ..." falha com ModuleNotFoundError mesmo com o
# volume montado e o ficheiro presente no disco.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from actions import task_proposal_engine
from intelligence.morning_brief import build_morning_brief  # noqa: E402

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


@app.get("/task-proposals")
def list_task_proposals():
    """Fase 6 (v2) - propostas de tarefa geradas a partir dos insights.
    Uma proposta só vira task real quando a Webstudio confirma (status
    CREATED_IN_WEBSTUDIO); até lá, fica PROPOSED/ACCEPTED/REJECTED."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, description, priority, category, source,
                       status, expected_impact, period, webstudio_task_id, created_at
                FROM actions.task_proposals
                ORDER BY created_at DESC
                """
            )
            rows = cur.fetchall()
    return {"task_proposals": rows}


class RejectProposalBody(BaseModel):
    reason: str | None = None


@app.post("/task-proposals/{proposal_id}/accept")
def accept_task_proposal(proposal_id: int):
    """PROPOSED -> ACCEPTED, com tentativa best-effort de criar a task
    real na Webstudio (ver actions/task_proposal_engine.py). A resposta
    inclui sempre "webstudio_sync" a dizer o que realmente aconteceu."""
    try:
        return task_proposal_engine.accept(DATABASE_URL, proposal_id)
    except task_proposal_engine.ProposalNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except task_proposal_engine.InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/task-proposals/{proposal_id}/reject")
def reject_task_proposal(proposal_id: int, body: RejectProposalBody = RejectProposalBody()):
    """PROPOSED -> REJECTED."""
    try:
        return task_proposal_engine.reject(DATABASE_URL, proposal_id, body.reason)
    except task_proposal_engine.ProposalNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except task_proposal_engine.InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/task-proposals/{proposal_id}/retry-sync")
def retry_sync_task_proposal(proposal_id: int):
    """Repete só o push para a Webstudio de uma proposta já ACCEPTED cujo
    sync anterior falhou (ex: Webstudio em baixo, porta errada, etc) - sem
    repetir a transição de estado."""
    try:
        return task_proposal_engine.retry_sync(DATABASE_URL, proposal_id)
    except task_proposal_engine.ProposalNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except task_proposal_engine.InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/webstudio/overview")
def webstudio_overview():
    """Funil da Webstudio, com receita reconhecida e lucro real (receita -
    despesas), agora que Payment/Expense estão ligados."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM core.leads")
            leads_total = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.leads WHERE status = 'WON'")
            leads_won = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.proposals")
            proposals_total = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.proposals WHERE status = 'ACCEPTED'")
            proposals_accepted = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.projects WHERE status IN ('PLANNING', 'IN_PROGRESS')")
            projects_active = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.projects WHERE status = 'COMPLETED'")
            projects_completed = cur.fetchone()["n"]

            cur.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM core.revenue_transactions WHERE revenue_type = 'AGENCY_SERVICE'"
            )
            revenue_total = cur.fetchone()["total"]

            cur.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM core.expenses")
            expenses_total = cur.fetchone()["total"]

            cur.execute("SELECT COALESCE(SUM(total_amount), 0) AS total FROM core.proposals WHERE status = 'SENT'")
            pipeline_value = cur.fetchone()["total"]

    revenue_total = float(revenue_total)
    expenses_total = float(expenses_total)

    return {
        "leads_total": leads_total,
        "leads_won": leads_won,
        "proposals_total": proposals_total,
        "proposals_accepted": proposals_accepted,
        "projects_active": projects_active,
        "projects_completed": projects_completed,
        "revenue_total": revenue_total,
        "expenses_total": expenses_total,
        "profit_total": revenue_total - expenses_total,
        "pipeline_value": pipeline_value,
    }


@app.get("/webstudio/development-activity")
def webstudio_development_activity():
    """Atividade do Development Lab (L3) - commits, PRs, builds etc. já
    promovidos de core.development_events. Não confundir com o funil
    comercial de webstudio_overview - isto é sobre o próprio trabalho de
    desenvolvimento, não sobre clientes/receita."""
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM core.development_events")
            total_events = cur.fetchone()["n"]

            cur.execute(
                "SELECT COUNT(*) AS n FROM core.development_events WHERE occurred_at >= now() - interval '7 days'"
            )
            events_last_7_days = cur.fetchone()["n"]

            cur.execute(
                """
                SELECT event_type, COUNT(*) AS n
                FROM core.development_events
                GROUP BY event_type
                ORDER BY n DESC
                """
            )
            by_type = cur.fetchall()

            cur.execute(
                """
                SELECT event_type, event_source, external_ref, occurred_at
                FROM core.development_events
                ORDER BY occurred_at DESC
                LIMIT 10
                """
            )
            recent = cur.fetchall()

    return {
        "total_events": total_events,
        "events_last_7_days": events_last_7_days,
        "by_type": by_type,
        "recent": recent,
    }


@app.get("/morning-brief")
def morning_brief():
    """Fase 6 (L7) - Context Builder: junta Webstudio + Contela + Labs
    num resumo diário único. Ver intelligence/morning_brief.py para o
    escopo exato (e as limitações honestas) do que entra aqui."""
    from datetime import datetime, timezone

    brief = build_morning_brief(DATABASE_URL)
    brief["generated_at"] = datetime.now(timezone.utc).isoformat()
    return brief
