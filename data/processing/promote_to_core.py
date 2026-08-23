"""
Promove registos de staging.* para core.* depois de validados.

staging = o que foi extraído da fonte, sem garantias de qualidade.
core    = só o que passou nas regras de validação. É isto que os Analyzers
          da Fase 3 vão consumir - por isso não pode ter lixo.

Desenhado para funcionar com qualquer fonte (não só Contela): o parâmetro
`source` identifica de onde vieram os dados, e fica gravado em core.*.source
para quando houver mais do que uma fonte a alimentar a mesma entidade.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

import psycopg
from psycopg.rows import dict_row

from data.validation.rules import validate_order, validate_stock

logger = logging.getLogger("evolure.processing.promote")

ENTITY_VALIDATORS: dict[str, Callable[[dict[str, Any]], tuple[bool, str | None]]] = {
    "orders": validate_order,
    "stock": validate_stock,
}

STAGING_TABLE = {
    "orders": "staging.contela_orders",
    "stock": "staging.contela_stock",
}

CORE_TABLE = {
    "orders": "core.orders",
    "stock": "core.stock",
}

CORE_COLUMNS = {
    "orders": ["source", "source_external_id", "customer_name", "total_amount", "status", "order_date"],
    "stock": ["source", "source_external_id", "product_name", "quantity", "supplier_name", "updated_at_source"],
}

# mapeia campo em staging -> campo em core (staging usa "external_id",
# core usa "source_external_id" porque agora convive com outras fontes)
STAGING_TO_CORE_FIELD = {
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
        "supplier_name": "supplier_name",
        "updated_at_source": "updated_at_source",
    },
}


def promote(entity: str, source: str, dsn: str) -> dict[str, int]:
    """Lê staging.<source>_<entity>, valida cada registo, e faz upsert dos
    válidos em core.<entity>. Rejeitados vão para raw.validation_rejects.
    Devolve {"promoted": N, "rejected": N}."""
    validator = ENTITY_VALIDATORS.get(entity)
    if validator is None:
        raise ValueError(f"Sem regras de validação para a entidade: {entity}")

    staging_table = STAGING_TABLE[entity]
    core_table = CORE_TABLE[entity]
    core_columns = CORE_COLUMNS[entity]
    field_map = STAGING_TO_CORE_FIELD[entity]

    promoted = 0
    rejected = 0

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
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

            placeholders = ", ".join(f"%({col})s" for col in core_columns)
            column_list = ", ".join(core_columns)
            update_clause = ", ".join(
                f"{col} = EXCLUDED.{col}"
                for col in core_columns
                if col not in ("source", "source_external_id")
            )
            sql = f"""
                INSERT INTO {core_table} ({column_list})
                VALUES ({placeholders})
                ON CONFLICT (source, source_external_id) DO UPDATE
                    SET {update_clause}, promoted_at = now()
            """
            with conn.cursor() as cur:
                cur.execute(sql, core_record)
            promoted += 1

        conn.commit()

    logger.info("Promoção %s/%s: %d promovidos, %d rejeitados", source, entity, promoted, rejected)
    return {"promoted": promoted, "rejected": rejected}
