"""
Automation Engine (Fase 6, v2) - decide se uma task_proposal já confirmada
na Webstudio (status = CREATED_IN_WEBSTUDIO) pode ser executada
automaticamente ou precisa de um humano.

IMPORTANTE: neste momento não há nenhuma integração real ligada (sem envio
de email, sem RPA, sem APIs externas configuradas - as pastas automation/
email, notifications, api, rpa existem desde a Fase 1 mas estão vazias).
Por isso AUTOMATION_HANDLERS está vazio de propósito: toda a proposta cai
em decision="HUMAN" até haver um handler real registado aqui.

Isto não é uma limitação a esconder - é o estado honesto da automação.
Quando ligares, por exemplo, envio de email (automation/email/), regista
um handler aqui: AUTOMATION_HANDLERS["send_weekly_report"] = send_email_fn

REGRA CENTRAL DA ARQUITETURA v3: "Labs Task -> Automation está proibido."
Isto só processa task_proposals com status = CREATED_IN_WEBSTUDIO - ou
seja, propostas que já viraram uma task real confirmada pela Webstudio
(webstudio_task_id preenchido). Uma proposta ainda em PROPOSED/ACCEPTED
nunca passa por aqui. Enquanto o fluxo de aceitação (Webstudio <- Labs,
W8/L4) não estiver ligado, esta função não encontra nada para processar -
o que é o comportamento correto, não um bug.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger("evolure.automation.task_executor")

# category -> função que executa a automação. Vazio por agora - ver docstring acima.
AUTOMATION_HANDLERS: dict[str, Callable[[dict[str, Any]], bool]] = {}


def decide_automation(task_proposal: dict[str, Any]) -> tuple[str, str | None]:
    """Decide se a proposta tem um handler automático registado.
    Devolve (decision, automation_type): decision é "AUTOMATION" ou "HUMAN";
    automation_type só é preenchido quando decision = "AUTOMATION"."""
    category = (task_proposal.get("category") or "").lower().strip()
    if category in AUTOMATION_HANDLERS:
        return "AUTOMATION", category
    return "HUMAN", None


def process_confirmed_proposals(dsn: str) -> dict[str, int]:
    """Percorre task_proposals com status=CREATED_IN_WEBSTUDIO que ainda não
    têm automation_proposals associada, decide HUMAN/AUTOMATION, e executa
    as que tiverem handler registado (hoje, nenhuma). Devolve contagens."""
    processed = {"automated": 0, "human": 0}

    with psycopg.connect(dsn) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT tp.id, tp.title, tp.category, tp.webstudio_task_id
                FROM actions.task_proposals tp
                LEFT JOIN actions.automation_proposals ap ON ap.task_proposal_id = tp.id
                WHERE tp.status = 'CREATED_IN_WEBSTUDIO' AND ap.id IS NULL
                """
            )
            pending = cur.fetchall()

        for proposal in pending:
            decision, automation_type = decide_automation(proposal)

            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO actions.automation_proposals (task_proposal_id, decision, automation_type)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (proposal["id"], decision, automation_type),
                )
                automation_proposal_id = cur.fetchone()["id"]

            if decision == "AUTOMATION":
                handler = AUTOMATION_HANDLERS[automation_type]
                _execute(conn, automation_proposal_id, handler, proposal)
                processed["automated"] += 1
            else:
                processed["human"] += 1

        conn.commit()

    logger.info(
        "Automation Engine: %d automatizadas, %d marcadas para humano.",
        processed["automated"],
        processed["human"],
    )
    return processed


def _execute(
    conn: psycopg.Connection,
    automation_proposal_id: int,
    handler: Callable[[dict[str, Any]], bool],
    proposal: dict[str, Any],
) -> None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "INSERT INTO actions.execution_requests (automation_proposal_id, status) VALUES (%s, 'RUNNING') RETURNING id",
            (automation_proposal_id,),
        )
        execution_request_id = cur.fetchone()["id"]

    try:
        success = handler(proposal)
        error_message = None
    except Exception as exc:  # handler pode lançar - regista como falha, não derruba o worker
        success = False
        error_message = str(exc)
        logger.exception("Handler de automação falhou para proposal %s", proposal["id"])

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE actions.execution_requests SET status = %s WHERE id = %s",
            ("DONE" if success else "FAILED", execution_request_id),
        )
        cur.execute(
            """
            INSERT INTO actions.execution_results (execution_request_id, success, error_message)
            VALUES (%s, %s, %s)
            """,
            (execution_request_id, success, error_message),
        )
