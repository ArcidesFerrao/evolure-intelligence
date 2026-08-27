"""
Promove registos de staging.* para core.* depois de validados.

V2: duas mudanças importantes face à versão anterior:

1) "organizations" é promovido PRIMEIRO (Service e Supplier do Contela
   ganham identidade própria em core.organizations). "orders" e "stock"
   passam a resolver organization_id a partir do external_id que trazem,
   em vez de ficarem só com o nome em texto.

2) "sales" deixa de ir para core.sales e passa a ir para
   core.revenue_transactions, com revenue_type='CUSTOMER_BUSINESS' - a
   receita agregada dos negócios que usam a Contela, distinta da receita
   da própria Contela enquanto plataforma (que ainda não existe, mas o
   schema já está pronto a recebê-la em revenue_type='PLATFORM_*').

staging = o que foi extraído da fonte, sem garantias de qualidade.
core    = só o que passou nas regras de validação. É isto que os Analyzers
          consomem - por isso não pode ter lixo.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

import psycopg
from psycopg.rows import dict_row

from data.validation.rules import validate_order, validate_organization, validate_sale, validate_stock

logger = logging.getLogger("evolure.processing.promote")

ENTITY_VALIDATORS: dict[str, Callable[[dict[str, Any]], tuple[bool, str | None]]] = {
    "organizations": validate_organization,
    "orders": validate_order,
    "stock": validate_stock,
    "sales": validate_sale,
}

# Entidades tratadas pelo caminho genérico (organizations, orders, stock).
# "sales" tem caminho próprio porque o destino (core.revenue_transactions)
# tem uma forma completamente diferente da origem.
STAGING_TABLE = {
    "organizations": "staging.contela_organizations",
    "orders": "staging.contela_orders",
    "stock": "staging.contela_stock",
    "sales": "staging.contela_sales",
}

CORE_TABLE = {
    "organizations": "core.organizations",
    "orders": "core.orders",
    "stock": "core.stock",
}

CORE_CONFLICT_COLUMNS = {
    "organizations": ["source", "source_external_id", "org_type"],
    "orders": ["source", "source_external_id"],
    "stock": ["source", "source_external_id"],
}

CORE_COLUMNS = {
    "organizations": ["source", "source_external_id", "name", "org_type", "created_at_source"],
    "orders": ["source", "source_external_id", "organization_id", "customer_name", "total_amount", "status", "order_date"],
    "stock": [
        "source", "source_external_id", "organization_id", "product_name", "quantity",
        "cost", "critical", "supplier_name", "updated_at_source",
    ],
}

# mapeia campo em staging -> campo em core (staging usa "external_id",
# core usa "source_external_id" porque agora convive com outras fontes).
# organization_id NÃO aparece aqui porque é resolvido à parte (não é uma
# cópia direta de um campo de staging, precisa de um lookup).
STAGING_TO_CORE_FIELD = {
    "organizations": {
        "external_id": "source_external_id",
        "name": "name",
        "org_type": "org_type",
        "created_at_source": "created_at_source",
    },
    "orders": {
        "external_id": "source_external_id",
        "customer_name": "customer_name",
        "total_amount": "total_amount",
        "status": "status",
        "order_date": "order_date",
    },
    "stock": {
        "external_id": "source_external_id",
        "product_name": "product_name",
        "quantity": "quantity",
        "cost": "cost",
        "critical": "critical",
        "supplier_name": "supplier_name",
        "updated_at_source": "updated_at_source",
    },
}

# entidades cujo staging tem organization_external_id e que precisam de
# resolver organization_id contra core.organizations antes do upsert.
ORG_LOOKUP_ENTITIES = {"orders", "stock", "sales"}


def _resolve_organization_id(conn: psycopg.Connection, source: str, external_id: str | None) -> int | None:
    if not external_id:
        return None
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM core.organizations WHERE source = %s AND source_external_id = %s LIMIT 1",
            (source, str(external_id)),
        )
        row = cur.fetchone()
        return row[0] if row else None


def _promote_generic(entity: str, source: str, conn: psycopg.Connection) -> dict[str, int]:
    validator = ENTITY_VALIDATORS[entity]
    staging_table = STAGING_TABLE[entity]
    core_table = CORE_TABLE[entity]
    core_columns = CORE_COLUMNS[entity]
    conflict_columns = CORE_CONFLICT_COLUMNS[entity]
    field_map = STAGING_TO_CORE_FIELD[entity]

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

        if entity in ORG_LOOKUP_ENTITIES and entity != "organizations":
            core_record["organization_id"] = _resolve_organization_id(
                conn, source, row.get("organization_external_id")
            )

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

        organization_id = _resolve_organization_id(conn, source, row.get("organization_external_id"))
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


def promote(entity: str, source: str, dsn: str) -> dict[str, int]:
    """Promove uma entidade de staging para core. Devolve {"promoted": N, "rejected": N}."""
    with psycopg.connect(dsn) as conn:
        if entity == "sales":
            result = _promote_sales_to_revenue_transactions(source, conn)
        elif entity in CORE_TABLE:
            result = _promote_generic(entity, source, conn)
        else:
            raise ValueError(f"Sem lógica de promoção para a entidade: {entity}")
        conn.commit()
    return result
