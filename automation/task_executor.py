"""
Automation Engine (Fase 6) - decide se uma tarefa pode ser executada
automaticamente ou precisa de um humano.

IMPORTANTE: neste momento não há nenhuma integração real ligada (sem envio
de email, sem RPA, sem APIs externas configuradas - as pastas automation/
email, notifications, api, rpa existem desde a Fase 1 mas estão vazias).
Por isso AUTOMATION_HANDLERS está vazio de propósito: toda a tarefa cai em
"manual" até haver um handler real registado aqui.

Isto não é uma limitação a esconder - é o estado honesto da automação.
Quando ligares, por exemplo, envio de email (automation/email/), regista
um handler aqui: AUTOMATION_HANDLERS["send_weekly_report"] = send_email_fn
"""
from __future__ import annotations

import logging
from typing import Any, Callable

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger("evolure.automation.task_executor")

# category/automation_type -> função que executa a tarefa automaticamente.
# Vazio por agora - ver docstring acima.
AUTOMATION_HANDLERS: dict[str, Callable[[dict[str, Any]], bool]] = {}


def decide_automation_type(task: dict[str, Any]) -> str:
    """Decide se a tarefa tem um handler automático registado. Devolve o
    nome do handler se existir, ou "manual" caso contrário."""
    category = (task.get("category") or "").lower().strip()
    if category in AUTOMATION_HANDLERS:
        return category
    return "manual"


def process_pending_tasks(dsn: str) -> dict[str, int]:
    """Percorre tarefas PENDING, marca automation_type, e executa as que
    tiverem handler registado (hoje, nenhuma). Devolve contagens."""
    processed = {"automated": 0, "manual": 0}

    with psycopg.connect(dsn) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT id, title, category FROM tasks.business_tasks WHERE status = 'PENDING' AND automation_type IS NULL"
            )
            pending = cur.fetchall()

        for task in pending:
            automation_type = decide_automation_type(task)
            handler = AUTOMATION_HANDLERS.get(automation_type)

            with conn.cursor() as cur:
                if handler:
                    success = handler(task)
                    new_status = "AUTOMATED" if success else "PENDING"
                    cur.execute(
                        "UPDATE tasks.business_tasks SET automation_type = %s, status = %s, updated_at = now() WHERE id = %s",
                        (automation_type, new_status, task["id"]),
                    )
                    processed["automated"] += 1 if success else 0
                else:
                    cur.execute(
                        "UPDATE tasks.business_tasks SET automation_type = 'manual', updated_at = now() WHERE id = %s",
                        (task["id"],),
                    )
                    processed["manual"] += 1
        conn.commit()

    logger.info("Automation Engine: %d automatizadas, %d marcadas para humano.", processed["automated"], processed["manual"])
    return processed
