"""
ContelaConnector - liga-se diretamente ao PostgreSQL do Contela (leitura)
e escreve os dados normalizados em staging.* na base do Evolure Intelligence
(escrita).

============================================================================
AJUSTA AQUI: nomes de tabelas/colunas reais do teu schema Prisma no Contela.
As queries abaixo assumem nomes plausíveis (Prisma por omissão usa o nome
do model como nome de tabela, ex: model Order -> tabela "Order").
Se o teu schema.prisma tiver @@map(...) ou nomes diferentes, muda só o
dicionário ENTITY_QUERIES - o resto do connector não precisa de mudar.
============================================================================

V2: "organizations" é uma nova entidade que unifica Service e Supplier como
contas com identidade própria (em vez de só texto solto em customer_name/
supplier_name). As restantes entidades passaram a trazer também o id da
organização (organization_external_id), para a promoção conseguir ligar
tudo em core.organizations.
"""
from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

from data.ingestion.base import DataSource

# entity -> query SQL contra a base do Contela
ENTITY_QUERIES: dict[str, str] = {
    # Service e Supplier são as duas contas de negócio no Contela - ambas
    # podem, no futuro, ter uma subscrição própria à plataforma.
    "organizations": """
        SELECT id AS external_id, "businessName" AS name, 'SERVICE' AS org_type, "createdAt" AS created_at_source
        FROM "Service"
        UNION ALL
        SELECT id AS external_id, "businessName" AS name, 'SUPPLIER' AS org_type, "createdAt" AS created_at_source
        FROM "Supplier"
    """,
    # "cliente" no Contela é uma Service (modelo B2B: Supplier vende a Service),
    # ligada a Order via serviceId.
    "orders": """
        SELECT
            o.id                AS external_id,
            o."serviceId"       AS organization_external_id,
            o."supplierId"      AS supplier_organization_external_id,
            s."businessName"    AS customer_name,
            sup."businessName"  AS supplier_name,
            o.total             AS total_amount,
            o.status::text      AS status,
            o.timestamp         AS order_date
        FROM "Order" o
        LEFT JOIN "Service" s ON s.id = o."serviceId"
        LEFT JOIN "Supplier" sup ON sup.id = o."supplierId"
    """,
    # StockItem não tem campo sku no schema atual - omitido.
    # Filtra deletedAt (soft delete) para não trazer itens apagados.
    # organization_external_id aqui é o Supplier - dono do stock.
    "stock": """
        SELECT
            si.id               AS external_id,
            si."supplierId"     AS organization_external_id,
            si.name             AS product_name,
            si.stock            AS quantity,
            si.cost             AS cost,
            si.critical         AS critical,
            sup."businessName"  AS supplier_name,
            si."updatedAt"      AS updated_at_source
        FROM "StockItem" si
        LEFT JOIN "Supplier" sup ON sup.id = si."supplierId"
        WHERE si."deletedAt" IS NULL
    """,
    # Sale = receita real de retalho (diferente de Order, que é pedido de
    # reabastecimento entre Service e Supplier). cogs incluído para margem.
    # organization_external_id aqui é a Service que vendeu.
    "sales": """
        SELECT
            s.id                AS external_id,
            s."serviceId"       AS organization_external_id,
            s.timestamp         AS sale_date,
            s.total             AS total_amount,
            s.cogs              AS cogs,
            s."paymentType"::text AS payment_type,
            sv."businessName"   AS service_name,
            sup."businessName"  AS supplier_name
        FROM "Sale" s
        LEFT JOIN "Service" sv ON sv.id = s."serviceId"
        LEFT JOIN "Supplier" sup ON sup.id = s."supplierId"
    """,
}

# entity -> tabela de destino em staging (Evolure Intelligence)
ENTITY_TARGET_TABLE: dict[str, str] = {
    "organizations": "staging.contela_organizations",
    "orders": "staging.contela_orders",
    "stock": "staging.contela_stock",
    "sales": "staging.contela_sales",
}

# entity -> colunas esperadas na tabela de destino, na ordem em que
# aparecem no INSERT (tem de bater certo com as migrations em database/migrations/)
ENTITY_TARGET_COLUMNS: dict[str, list[str]] = {
    "organizations": ["external_id", "name", "org_type", "created_at_source"],
    "orders": [
        "external_id", "organization_external_id", "supplier_organization_external_id",
        "customer_name", "supplier_name", "total_amount", "status", "order_date",
    ],
    "stock": [
        "external_id", "organization_external_id", "product_name", "quantity",
        "cost", "critical", "supplier_name", "updated_at_source",
    ],
    "sales": [
        "external_id", "organization_external_id", "sale_date", "total_amount",
        "cogs", "payment_type", "service_name", "supplier_name",
    ],
}

# entity -> colunas que formam a chave de conflito (ON CONFLICT). Por
# omissão é só "external_id", mas "organizations" precisa de (external_id,
# org_type) porque Service e Supplier podem, em teoria, ter o mesmo id.
ENTITY_CONFLICT_COLUMNS: dict[str, list[str]] = {
    "organizations": ["external_id", "org_type"],
}


class ContelaConnector(DataSource):
    """Lê diretamente do Postgres do Contela e carrega em staging.* do
    Evolure Intelligence. Requer duas DSNs:
      - source_dsn: base do Contela (definido em CONTELA_DATABASE_URL)
      - dest_dsn:   base do Evolure Intelligence (o DATABASE_URL habitual)
    """

    source_id = "contela"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._source_dsn = self.config.get("source_dsn") or os.environ.get("CONTELA_DATABASE_URL", "")
        self._dest_dsn = self.config.get("dest_dsn") or os.environ.get("DATABASE_URL", "")
        self._source_conn: psycopg.Connection | None = None
        self._dest_conn: psycopg.Connection | None = None

    def connect(self) -> None:
        if not self._source_dsn:
            raise RuntimeError("CONTELA_DATABASE_URL não está definido - não é possível ligar ao Contela")
        if not self._dest_dsn:
            raise RuntimeError("DATABASE_URL não está definido - não é possível ligar ao Evolure Intelligence")
        self._source_conn = psycopg.connect(self._source_dsn, row_factory=dict_row)
        self._dest_conn = psycopg.connect(self._dest_dsn)

    def extract(self, entity: str) -> list[dict[str, Any]]:
        query = ENTITY_QUERIES.get(entity)
        if query is None:
            raise ValueError(f"Entidade desconhecida para o Contela: {entity}")
        assert self._source_conn is not None
        with self._source_conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()

    def transform(self, entity: str, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Por agora é passagem direta - as queries já devolvem os nomes
        # normalizados via alias SQL. Se precisares de limpeza adicional
        # (ex: normalizar status, converter moeda), faz aqui.
        cleaned = []
        for record in raw_records:
            clean = dict(record)
            clean["external_id"] = str(clean["external_id"])  # garante string consistente
            cleaned.append(clean)
        return cleaned

    def load(self, entity: str, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0
        table = ENTITY_TARGET_TABLE.get(entity)
        columns = ENTITY_TARGET_COLUMNS.get(entity)
        if table is None or columns is None:
            raise ValueError(f"Entidade desconhecida para o Contela: {entity}")

        conflict_columns = ENTITY_CONFLICT_COLUMNS.get(entity, ["external_id"])

        assert self._dest_conn is not None
        placeholders = ", ".join(f"%({col})s" for col in columns)
        column_list = ", ".join(columns)
        conflict_list = ", ".join(conflict_columns)
        update_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in columns if col not in conflict_columns)

        sql = f"""
            INSERT INTO {table} ({column_list})
            VALUES ({placeholders})
            ON CONFLICT ({conflict_list}) DO UPDATE SET {update_clause}, ingested_at = now()
        """
        with self._dest_conn.cursor() as cur:
            cur.executemany(sql, records)
        self._dest_conn.commit()
        return len(records)

    def disconnect(self) -> None:
        if self._source_conn is not None:
            self._source_conn.close()
        if self._dest_conn is not None:
            self._dest_conn.close()
        self._source_conn = None
        self._dest_conn = None
