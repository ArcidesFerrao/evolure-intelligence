"""
Task Generator (Fase 6) - lê o insight mais recente (Fase 5) e gera uma
tarefa concreta em tasks.business_tasks.

Fluxo: Insight -> Recommendation (implícito no prompt) -> Task.
Idempotente por (source, period): correr o scheduler várias vezes no
mesmo mês não gera tarefas duplicadas (ON CONFLICT actualiza a existente).
"""
from __future__ import annotations

import logging
from typing import Any

import psycopg
from psycopg.rows import dict_row

from intelligence.llm.gemini_client import generate_json
from intelligence.prompts.task_recommendation import build_task_prompt

logger = logging.getLogger("evolure.tasks.generator")

SOURCE = "intelligence_engine"
VALID_PRIORITIES = {"low", "medium", "high"}


def _get_latest_insight(conn: psycopg.Connection, period: str) -> str | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT insight_text FROM intelligence.insights WHERE period = %s",
            (period,),
        )
        row = cur.fetchone()
        return row["insight_text"] if row else None


def _save_task(conn: psycopg.Connection, period: str, task: dict[str, Any]) -> None:
    priority = task.get("priority") if task.get("priority") in VALID_PRIORITIES else "medium"
    impact = task.get("expected_impact") if task.get("expected_impact") in VALID_PRIORITIES else "medium"

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO tasks.business_tasks
                (title, description, priority, category, source, status, expected_impact, period)
            VALUES (%s, %s, %s, %s, %s, 'PENDING', %s, %s)
            ON CONFLICT (source, period) DO UPDATE
                SET title = EXCLUDED.title, description = EXCLUDED.description,
                    priority = EXCLUDED.priority, category = EXCLUDED.category,
                    expected_impact = EXCLUDED.expected_impact, updated_at = now()
            """,
            (
                task.get("title", "Tarefa sem título"),
                task.get("description", ""),
                priority,
                task.get("category", "geral"),
                SOURCE,
                impact,
                period,
            ),
        )


def run(dsn: str, period: str | None = None) -> dict[str, Any] | None:
    """Gera a tarefa para `period` ('YYYY-MM', default: mês atual) a partir
    do insight já gerado. Devolve None se ainda não houver insight (a Fase
    5 corre antes desta, mas protege-se de qualquer forma)."""
    from datetime import date

    if period is None:
        period = date.today().strftime("%Y-%m")

    with psycopg.connect(dsn) as conn:
        insight_text = _get_latest_insight(conn, period)
        if not insight_text:
            logger.info("Sem insight para %s - a saltar geração de tarefa.", period)
            return None

        prompt = build_task_prompt(insight_text)
        task = generate_json(prompt)

        _save_task(conn, period, task)
        conn.commit()

    logger.info("Tarefa gerada para %s: %s", period, task.get("title"))
    return {"period": period, **task}
