"""
Morning Brief Engine (Fase 6, L7) - o Context Builder que junta as três
fontes (Webstudio, Contela, Labs) num resumo diário único.

Escopo honesto desta v1: o que a Webstudio expõe hoje via core.* são
entidades comerciais (leads, proposals, contracts, projects, invoices,
payments, expenses, campaigns) e development_events - NÃO inclui ainda
Task/Blocker/DailyPlan/WeeklyPlan (essas entidades nunca foram registadas
no WebstudioConnector). Por isso o brief usa "propostas de tarefa
pendentes" (actions.task_proposals) como substituto para "prioridades do
dia" em vez do DailyPlan real da Webstudio - é o melhor proxy disponível
agora. Quando Task/DailyPlan forem ingeridos como fonte, isto pode ser
enriquecido sem mudar o contrato do brief (só adicionar campos).
"""
from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row


def build_morning_brief(dsn: str) -> dict[str, Any]:
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # --- Labs: último insight gerado ---
            cur.execute(
                "SELECT period, insight_text, created_at FROM intelligence.insights "
                "ORDER BY period DESC LIMIT 1"
            )
            latest_insight = cur.fetchone()

            # --- Labs: propostas à espera de decisão ou de sync ---
            cur.execute(
                """
                SELECT id, title, priority, status, category, created_at
                FROM actions.task_proposals
                WHERE status IN ('PROPOSED', 'ACCEPTED')
                ORDER BY
                    CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                    created_at DESC
                LIMIT 10
                """
            )
            pending_proposals = cur.fetchall()

            # --- Labs: anomalias detetadas nos últimos 7 dias ---
            cur.execute(
                """
                SELECT metric, period, deviation_pct, severity, detected_at
                FROM analytics.anomalies
                WHERE detected_at >= now() - interval '7 days'
                ORDER BY detected_at DESC
                LIMIT 5
                """
            )
            recent_anomalies = cur.fetchall()

            # --- Webstudio (Development Lab): atividade das últimas 24h ---
            cur.execute(
                "SELECT COUNT(*) AS n FROM core.development_events "
                "WHERE occurred_at >= now() - interval '1 day'"
            )
            dev_events_last_day = cur.fetchone()["n"]

            cur.execute(
                """
                SELECT event_type, external_ref, occurred_at
                FROM core.development_events
                ORDER BY occurred_at DESC
                LIMIT 5
                """
            )
            recent_dev_events = cur.fetchall()

            # --- Webstudio: funil comercial (mesma lógica do webstudio_overview) ---
            cur.execute("SELECT COUNT(*) AS n FROM core.leads WHERE status NOT IN ('WON', 'LOST')")
            leads_open = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.proposals WHERE status = 'SENT'")
            proposals_awaiting_response = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.projects WHERE status IN ('PLANNING', 'IN_PROGRESS')")
            projects_active = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM core.invoices WHERE status = 'OVERDUE'")
            invoices_overdue = cur.fetchone()["n"]

            # --- Contela: operação ---
            cur.execute("SELECT COUNT(*) AS n FROM core.stock WHERE quantity <= 0")
            out_of_stock_count = cur.fetchone()["n"]

    focus_recommendation = _build_focus_recommendation(
        pending_proposals, recent_anomalies, invoices_overdue, dev_events_last_day
    )

    return {
        "generated_at": None,  # preenchido pela rota (now() do request, não da query)
        "focus_recommendation": focus_recommendation,
        "latest_insight": latest_insight,
        "pending_task_proposals": pending_proposals,
        "recent_anomalies": recent_anomalies,
        "webstudio": {
            "leads_open": leads_open,
            "proposals_awaiting_response": proposals_awaiting_response,
            "projects_active": projects_active,
            "invoices_overdue": invoices_overdue,
            "development_events_last_24h": dev_events_last_day,
            "recent_development_events": recent_dev_events,
        },
        "contela": {
            "out_of_stock_count": out_of_stock_count,
        },
    }


def _build_focus_recommendation(
    pending_proposals: list[dict[str, Any]],
    recent_anomalies: list[dict[str, Any]],
    invoices_overdue: int,
    dev_events_last_day: int,
) -> str:
    """Heurística simples v1 (sem LLM) - a coisa mais urgente primeiro.
    Prioridade: anomalias severas > faturas vencidas > proposta de alta
    prioridade > continuar o que já estava em curso."""
    high_severity_anomalies = [a for a in recent_anomalies if a.get("severity") == "high"]
    if high_severity_anomalies:
        a = high_severity_anomalies[0]
        return f"Anomalia crítica em {a['metric']} ({a['period']}) - vale investigar antes de mais nada."

    if invoices_overdue > 0:
        return f"{invoices_overdue} fatura(s) vencida(s) na Webstudio - considera cobrar antes de tudo o resto."

    high_priority_proposals = [p for p in pending_proposals if p.get("priority") == "high"]
    if high_priority_proposals:
        p = high_priority_proposals[0]
        return f"Proposta de alta prioridade à espera de decisão: \"{p['title']}\"."

    if dev_events_last_day == 0:
        return "Sem atividade de desenvolvimento registada nas últimas 24h."

    return "Sem urgências detetadas - dia livre para avançar o que já estava planeado."
