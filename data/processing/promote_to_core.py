"""
Promove registos de staging.* para core.* depois de validados.

Generalizado para qualquer fonte (Contela, Webstudio, ...): cada entidade
declara as suas colunas, a validação, e opcionalmente uma lista de
referências a resolver contra outras tabelas core.* (ex: uma Proposal
resolve client_id contra core.clients e lead_id contra core.leads).

"sales" do Contela continua com caminho próprio porque o destino
(core.revenue_transactions) tem forma completamente diferente da origem.

A ORDEM em que as entidades são promovidas importa quando há referências
entre elas - ver apps/workers/run_promotion.py.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

import psycopg
from psycopg.rows import dict_row

from data.validation.rules import (
    validate_campaign,
    validate_client,
    validate_contract,
    validate_expense,
    validate_invoice,
    validate_lead,
    validate_order,
    validate_organization,
    validate_payment,
    validate_project,
    validate_proposal,
    validate_sale,
    validate_stock,
)

logger = logging.getLogger("evolure.processing.promote")

ENTITY_VALIDATORS: dict[str, Callable[[dict[str, Any]], tuple[bool, str | None]]] = {
    "organizations": validate_organization,
    "orders": validate_order,
    "stock": validate_stock,
    "clients": validate_client,
    "leads": validate_lead,
    "proposals": validate_proposal,
    "contracts": validate_contract,
    "projects": validate_project,
    "invoices": validate_invoice,
    "payments": validate_payment,
    "expenses": validate_expense,
    "campaigns": validate_campaign,
}

STAGING_TABLE = {
    "organizations": "staging.contela_organizations",
    "orders": "staging.contela_orders",
    "stock": "staging.contela_stock",
    "sales": "staging.contela_sales",
    "clients": "staging.webstudio_clients",
    "leads": "staging.webstudio_leads",
    "proposals": "staging.webstudio_proposals",
    "contracts": "staging.webstudio_contracts",
    "projects": "staging.webstudio_projects",
    "invoices": "staging.webstudio_invoices",
    "payments": "staging.webstudio_payments",
    "expenses": "staging.webstudio_expenses",
    "campaigns": "staging.webstudio_campaigns",
}

CORE_TABLE = {
    "organizations": "core.organizations",
    "orders": "core.orders",
    "stock": "core.stock",
    "clients": "core.clients",
    "leads": "core.leads",
    "proposals": "core.proposals",
    "contracts": "core.contracts",
    "projects": "core.projects",
    "invoices": "core.invoices",
    "payments": "core.payments",
    "expenses": "core.expenses",
    "campaigns": "core.wstudio_campaigns",
}

CORE_CONFLICT_COLUMNS = {
    "organizations": ["source", "source_external_id", "org_type"],
}
DEFAULT_CONFLICT_COLUMNS = ["source", "source_external_id"]

CORE_COLUMNS = {
    "organizations": ["source", "source_external_id", "name", "org_type", "created_at_source"],
    "orders": [
        "source", "source_external_id", "organization_id", "supplier_organization_id",
        "customer_name", "supplier_name", "total_amount", "status", "order_date",
    ],
    "stock": [
        "source", "source_external_id", "organization_id", "product_name", "quantity",
        "cost", "critical", "supplier_name", "updated_at_source",
    ],
    "clients": ["source", "source_external_id", "name", "email", "phone", "company", "tax_id", "created_at_source"],
    "leads": [
        "source", "source_external_id", "client_id", "name", "email", "phone", "company",
        "lead_source", "status", "created_at_source",
    ],
    "proposals": [
        "source", "source_external_id", "client_id", "lead_id", "title", "total_amount", "status",
        "valid_until", "sent_at", "responded_at", "created_at_source",
    ],
    "contracts": [
        "source", "source_external_id", "client_id", "proposal_id", "title", "value", "status",
        "start_date", "end_date", "signed_at", "created_at_source",
    ],
    "projects": [
        "source", "source_external_id", "client_id", "contract_id", "name", "status", "budget",
        "start_date", "due_date", "completed_at", "created_at_source",
    ],
    "invoices": [
        "source", "source_external_id", "client_id", "project_id", "number", "subtotal", "tax", "total",
        "status", "due_date", "paid_at", "created_at_source",
    ],
    "payments": [
        "source", "source_external_id", "invoice_id", "amount", "method", "status", "paid_at", "created_at_source",
    ],
    "expenses": [
        "source", "source_external_id", "project_id", "category", "description", "amount", "expense_date",
        "created_at_source",
    ],
    "campaigns": [
        "source", "source_external_id", "name", "channel", "budget", "status", "start_date", "end_date",
        "impressions", "clicks", "leads_count", "conversions", "created_at_source",
    ],
}

# entidade -> campos copiados diretamente de staging para core (mesmo nome
# lógico, sem precisar de resolução). Campos de referência (client_id,
# organization_id, etc) NÃO aparecem aqui - são resolvidos à parte (ver
# REFERENCE_FIELDS), porque staging só tem o external_id, não o id numérico.
STAGING_TO_CORE_FIELD = {
    "organizations": {
        "external_id": "source_external_id", "name": "name", "org_type": "org_type",
        "created_at_source": "created_at_source",
    },
    "orders": {
        "external_id": "source_external_id", "customer_name": "customer_name", "supplier_name": "supplier_name",
        "total_amount": "total_amount", "status": "status", "order_date": "order_date",
    },
    "stock": {
        "external_id": "source_external_id", "product_name": "product_name", "quantity": "quantity",
        "cost": "cost", "critical": "critical", "supplier_name": "supplier_name",
        "updated_at_source": "updated_at_source",
    },
    "clients": {
        "external_id": "source_external_id", "name": "name", "email": "email", "phone": "phone",
        "company": "company", "tax_id": "tax_id", "created_at_source": "created_at_source",
    },
    "leads": {
        "external_id": "source_external_id", "name": "name", "email": "email", "phone": "phone",
        "company": "company", "lead_source": "lead_source", "status": "status",
        "created_at_source": "created_at_source",
    },
    "proposals": {
        "external_id": "source_external_id", "title": "title", "total_amount": "total_amount",
        "status": "status", "valid_until": "valid_until", "sent_at": "sent_at",
        "responded_at": "responded_at", "created_at_source": "created_at_source",
    },
    "contracts": {
        "external_id": "source_external_id", "title": "title", "value": "value", "status": "status",
        "start_date": "start_date", "end_date": "end_date", "signed_at": "signed_at",
        "created_at_source": "created_at_source",
    },
    "projects": {
        "external_id": "source_external_id", "name": "name", "status": "status", "budget": "budget",
        "start_date": "start_date", "due_date": "due_date", "completed_at": "completed_at",
        "created_at_source": "created_at_source",
    },
    "invoices": {
        "external_id": "source_external_id", "number": "number", "subtotal": "subtotal", "tax": "tax",
        "total": "total", "status": "status", "due_date": "due_date", "paid_at": "paid_at",
        "created_at_source": "created_at_source",
    },
    "payments": {
        "external_id": "source_external_id", "amount": "amount", "method": "method", "status": "status",
        "paid_at": "paid_at", "created_at_source": "created_at_source",
    },
    "expenses": {
        "external_id": "source_external_id", "category": "category", "description": "description",
        "amount": "amount", "expense_date": "expense_date", "created_at_source": "created_at_source",
    },
    "campaigns": {
        "external_id": "source_external_id", "name": "name", "channel": "channel", "budget": "budget",
        "status": "status", "start_date": "start_date", "end_date": "end_date",
        "impressions": "impressions", "clicks": "clicks", "leads_count": "leads_count",
        "conversions": "conversions", "created_at_source": "created_at_source",
    },
}

# entidade -> lista de (campo em staging, campo em core, tabela core a
# consultar). Resolvido à parte porque staging só tem o external_id da
# entidade referenciada - precisa de um lookup para virar id numérico.
REFERENCE_FIELDS: dict[str, list[tuple[str, str, str]]] = {
    "orders": [
        ("organization_external_id", "organization_id", "core.organizations"),
        ("supplier_organization_external_id", "supplier_organization_id", "core.organizations"),
    ],
    "stock": [("organization_external_id", "organization_id", "core.organizations")],
    "leads": [("client_external_id", "client_id", "core.clients")],
    "proposals": [
        ("client_external_id", "client_id", "core.clients"),
        ("lead_external_id", "lead_id", "core.leads"),
    ],
    "contracts": [
        ("client_external_id", "client_id", "core.clients"),
        ("proposal_external_id", "proposal_id", "core.proposals"),
    ],
    "projects": [
        ("client_external_id", "client_id", "core.clients"),
        ("contract_external_id", "contract_id", "core.contracts"),
    ],
    "invoices": [
        ("client_external_id", "client_id", "core.clients"),
        ("project_external_id", "project_id", "core.projects"),
    ],
    "payments": [("invoice_external_id", "invoice_id", "core.invoices")],
    "expenses": [("project_external_id", "project_id", "core.projects")],
}


def _resolve_ref(conn: psycopg.Connection, source: str, table: str, external_id: str | None) -> int | None:
    if not external_id:
        return None
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT id FROM {table} WHERE source = %s AND source_external_id = %s LIMIT 1",
            (source, str(external_id)),
        )
        row = cur.fetchone()
        return row[0] if row else None


def _promote_generic(entity: str, source: str, conn: psycopg.Connection) -> dict[str, int]:
    validator = ENTITY_VALIDATORS[entity]
    staging_table = STAGING_TABLE[entity]
    core_table = CORE_TABLE[entity]
    core_columns = CORE_COLUMNS[entity]
    conflict_columns = CORE_CONFLICT_COLUMNS.get(entity, DEFAULT_CONFLICT_COLUMNS)
    field_map = STAGING_TO_CORE_FIELD[entity]
    reference_fields = REFERENCE_FIELDS.get(entity, [])

    promoted = 0
    rejected = 0

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT * FROM {staging_table}")
        rows = cur.fetchall()

    for row in rows:
        is_valid, reason = validator(row)
        if not is_valid:
            rejected += 1
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO raw.validation_rejects (source, entity, external_id, reason)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (source, entity, str(row.get("external_id")), reason),
                )
            continue

        core_record: dict[str, Any] = {"source": source}
        for staging_field, core_field in field_map.items():
            core_record[core_field] = row.get(staging_field)

        for staging_field, core_field, ref_table in reference_fields:
            core_record[core_field] = _resolve_ref(conn, source, ref_table, row.get(staging_field))

        placeholders = ", ".join(f"%({col})s" for col in core_columns)
        column_list = ", ".join(core_columns)
        conflict_list = ", ".join(conflict_columns)
        update_clause = ", ".join(
            f"{col} = EXCLUDED.{col}" for col in core_columns if col not in conflict_columns
        )
        sql = f"""
            INSERT INTO {core_table} ({column_list})
            VALUES ({placeholders})
            ON CONFLICT ({conflict_list}) DO UPDATE
                SET {update_clause}, promoted_at = now()
        """
        with conn.cursor() as cur:
            cur.execute(sql, core_record)
        promoted += 1

    logger.info("Promoção %s/%s: %d promovidos, %d rejeitados", source, entity, promoted, rejected)
    return {"promoted": promoted, "rejected": rejected}


def _promote_sales_to_revenue_transactions(source: str, conn: psycopg.Connection) -> dict[str, int]:
    """Caminho dedicado: staging.contela_sales -> core.revenue_transactions,
    marcado como revenue_type='CUSTOMER_BUSINESS' (atividade agregada dos
    negócios que usam a Contela - não é receita própria da Evolure Labs)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT * FROM {STAGING_TABLE['sales']}")
        rows = cur.fetchall()

    promoted = 0
    rejected = 0

    for row in rows:
        is_valid, reason = validate_sale(row)
        if not is_valid:
            rejected += 1
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO raw.validation_rejects (source, entity, external_id, reason)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (source, "sales", str(row.get("external_id")), reason),
                )
            continue

        organization_id = _resolve_ref(conn, source, "core.organizations", row.get("organization_external_id"))
        metadata = {
            "cogs": float(row["cogs"]) if row.get("cogs") is not None else None,
            "payment_type": row.get("payment_type"),
            "service_name": row.get("service_name"),
            "supplier_name": row.get("supplier_name"),
        }

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO core.revenue_transactions
                    (source, source_external_id, organization_id, customer_id, amount, currency,
                     revenue_type, subscription_id, product_id, transaction_date, metadata)
                VALUES (%s, %s, %s, NULL, %s, 'MZN', 'CUSTOMER_BUSINESS', NULL, NULL, %s, %s)
                ON CONFLICT (source, source_external_id) DO UPDATE
                    SET organization_id = EXCLUDED.organization_id, amount = EXCLUDED.amount,
                        transaction_date = EXCLUDED.transaction_date, metadata = EXCLUDED.metadata,
                        promoted_at = now()
                """,
                (
                    source,
                    row["external_id"],
                    organization_id,
                    row["total_amount"],
                    row["sale_date"],
                    json.dumps(metadata, default=str),
                ),
            )
        promoted += 1

    logger.info("Promoção %s/sales -> revenue_transactions: %d promovidos, %d rejeitados", source, promoted, rejected)
    return {"promoted": promoted, "rejected": rejected}


def _recognize_webstudio_revenue(source: str, conn: psycopg.Connection) -> dict[str, int]:
    """Pagamentos concluídos (Payment.status='COMPLETED') tornam-se receita
    reconhecida em core.revenue_transactions (revenue_type='AGENCY_SERVICE') -
    é receita PRÓPRIA da Evolure Labs, ao contrário da atividade agregada de
    terceiros que vemos no Contela (revenue_type='CUSTOMER_BUSINESS').

    Corre depois de "payments" já estar em core.payments (precisa do join a
    core.invoices para saber o client_id)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT p.source_external_id, p.amount, p.paid_at, i.client_id
            FROM core.payments p
            JOIN core.invoices i ON i.id = p.invoice_id
            WHERE p.source = %s AND p.status = 'COMPLETED'
            """,
            (source,),
        )
        rows = cur.fetchall()

    recognized = 0
    for row in rows:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO core.revenue_transactions
                    (source, source_external_id, organization_id, customer_id, amount, currency,
                     revenue_type, subscription_id, product_id, transaction_date, metadata)
                VALUES (%s, %s, NULL, %s, %s, 'MZN', 'AGENCY_SERVICE', NULL, NULL, %s, NULL)
                ON CONFLICT (source, source_external_id) DO UPDATE
                    SET customer_id = EXCLUDED.customer_id, amount = EXCLUDED.amount,
                        transaction_date = EXCLUDED.transaction_date, promoted_at = now()
                """,
                (source, row["source_external_id"], row["client_id"], row["amount"], row["paid_at"]),
            )
        recognized += 1

    logger.info("Reconhecimento de receita Webstudio: %d pagamentos -> revenue_transactions", recognized)
    return {"promoted": recognized, "rejected": 0}


def promote(entity: str, source: str, dsn: str) -> dict[str, int]:
    """Promove uma entidade de staging para core. Devolve {"promoted": N, "rejected": N}."""
    with psycopg.connect(dsn) as conn:
        if entity == "sales":
            result = _promote_sales_to_revenue_transactions(source, conn)
        elif entity == "revenue_recognition":
            result = _recognize_webstudio_revenue(source, conn)
        elif entity in CORE_TABLE:
            result = _promote_generic(entity, source, conn)
        else:
            raise ValueError(f"Sem lógica de promoção para a entidade: {entity}")
        conn.commit()
    return result
