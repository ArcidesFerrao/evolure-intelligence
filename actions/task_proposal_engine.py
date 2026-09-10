"""
Task Proposal Engine (Fase 6, L4) - gere as transições de estado de uma
task_proposal: PROPOSED -> ACCEPTED/REJECTED, e ACCEPTED -> CREATED_IN_WEBSTUDIO.

Princípio central da arquitetura v3: "A Webstudio possui as Tasks. O Labs
possui Task Proposals." O Labs nunca cria uma task real sozinho - aceitar
uma proposta aqui só marca ACCEPTED e tenta (best-effort) empurrar para a
Webstudio via WEBSTUDIO_API_URL/WEBSTUDIO_API_KEY. Enquanto o endpoint do
lado da Webstudio que recebe isto (W8) não existir, a proposta fica
honestamente presa em ACCEPTED - nada aqui finge que a task foi criada
sem ter sido de verdade. Assim que W8 existir, chamar accept() de novo
(ou um futuro job de retry) completa a transição sem precisar mudar nada
aqui.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import psycopg
import requests
from psycopg.rows import dict_row

logger = logging.getLogger("evolure.actions.task_proposal_engine")

# Caminho previsto do lado da Webstudio para receber propostas aceites -
# ainda não construído (W8). Módulo já fica pronto para quando existir.
WEBSTUDIO_TASK_PROPOSAL_PATH = "/api/delivery/development/task-proposals"


class ProposalNotFound(Exception):
    pass


class InvalidTransition(Exception):
    pass


def _get_proposal(conn: psycopg.Connection, proposal_id: int) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM actions.task_proposals WHERE id = %s", (proposal_id,))
        row = cur.fetchone()
    if not row:
        raise ProposalNotFound(f"task_proposal {proposal_id} não encontrada")
    return row


def _transition(
    conn: psycopg.Connection,
    proposal_id: int,
    from_status: str,
    to_status: str,
) -> dict[str, Any]:
    proposal = _get_proposal(conn, proposal_id)
    if proposal["status"] != from_status:
        raise InvalidTransition(
            f"Só é possível transitar de {from_status} para {to_status} "
            f"(estado atual: {proposal['status']})"
        )

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "UPDATE actions.task_proposals SET status = %s, updated_at = now() WHERE id = %s RETURNING *",
            (to_status, proposal_id),
        )
        updated = cur.fetchone()
    conn.commit()
    return updated


def accept(dsn: str, proposal_id: int) -> dict[str, Any]:
    """PROPOSED -> ACCEPTED, depois tenta (best-effort) criar a task real
    na Webstudio. O resultado inclui sempre um campo "webstudio_sync" que
    diz honestamente o que aconteceu: "success", "pending_config" (W8
    ainda não configurado) ou "failed" (tentou e não conseguiu)."""
    with psycopg.connect(dsn) as conn:
        proposal = _transition(conn, proposal_id, "PROPOSED", "ACCEPTED")

    return _try_push_to_webstudio(dsn, proposal)


def reject(dsn: str, proposal_id: int, reason: str | None = None) -> dict[str, Any]:
    with psycopg.connect(dsn) as conn:
        updated = _transition(conn, proposal_id, "PROPOSED", "REJECTED")

    logger.info("Proposta %d rejeitada. Motivo: %s", proposal_id, reason or "(sem motivo)")
    return updated


def _try_push_to_webstudio(dsn: str, proposal: dict[str, Any]) -> dict[str, Any]:
    api_url = os.environ.get("WEBSTUDIO_API_URL", "").rstrip("/")
    api_key = os.environ.get("WEBSTUDIO_API_KEY", "")

    if not api_url or not api_key:
        logger.warning(
            "WEBSTUDIO_API_URL/WEBSTUDIO_API_KEY não configurados - proposta %d "
            "fica ACCEPTED, à espera do endpoint da Webstudio (W8, ainda por construir).",
            proposal["id"],
        )
        return {**proposal, "webstudio_sync": "pending_config"}

    try:
        resp = requests.post(
            f"{api_url}{WEBSTUDIO_TASK_PROPOSAL_PATH}",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "title": proposal["title"],
                "description": proposal["description"],
                "priority": proposal["priority"],
                "sourceProposalId": proposal["id"],
            },
            timeout=10,
        )
        resp.raise_for_status()
        webstudio_task_id = resp.json().get("id")
    except Exception as exc:
        logger.exception("Falha ao empurrar proposta %d para a Webstudio", proposal["id"])
        return {**proposal, "webstudio_sync": "failed", "webstudio_sync_error": str(exc)}

    with psycopg.connect(dsn) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE actions.task_proposals
                SET status = 'CREATED_IN_WEBSTUDIO', webstudio_task_id = %s, updated_at = now()
                WHERE id = %s
                RETURNING *
                """,
                (webstudio_task_id, proposal["id"]),
            )
            updated = cur.fetchone()
        conn.commit()

    logger.info(
        "Proposta %d criada na Webstudio com id %s", proposal["id"], webstudio_task_id
    )
    return {**updated, "webstudio_sync": "success"}
