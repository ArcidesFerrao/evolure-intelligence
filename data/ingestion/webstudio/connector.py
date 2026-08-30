"""
WebstudioConnector - liga-se diretamente ao PostgreSQL da Webstudio
(schema "operational") e escreve os dados normalizados em staging.* na
base do Evolure Intelligence.

Mesma forma do ContelaConnector. Os campos aqui batem certo com o
schema.prisma real da Webstudio (multiSchema: operational + integration -
por agora lemos "operational" diretamente; se um dia "integration" ganhar
views próprias para isto, troca-se só as queries abaixo).
"""
from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.rows import dict_row

from data.ingestion.base import DataSource

ENTITY_QUERIES: dict[str, str] = {
    "clients": """
        SELECT id AS external_id, name, email, phone, company,
               "taxId" AS tax_id, "createdAt" AS created_at_source
        FROM operational.clients
    """,
    "leads": """
        SELECT id AS external_id, "clientId" AS client_external_id,
               name, email, phone, company, source AS lead_source,
               status::text AS status, "createdAt" AS created_at_source
        FROM operational.leads
    """,
    "proposals": """
        SELECT id AS external_id, "clientId" AS client_external_id, "leadId" AS lead_external_id,
               title, "totalAmount" AS total_amount, status::text AS status,
               "validUntil" AS valid_until, "sentAt" AS sent_at, "respondedAt" AS responded_at,
               "createdAt" AS created_at_source
        FROM operational.proposals
    """,
    "contracts": """
        SELECT id AS external_id, "clientId" AS client_external_id, "proposalId" AS proposal_external_id,
               title, value, "startDate" AS start_date, "endDate" AS end_date,
               status::text AS status, "signedAt" AS signed_at, "createdAt" AS created_at_source
        FROM operational.contracts
    """,
    "projects": """
        SELECT id AS external_id, "clientId" AS client_external_id, "contractId" AS contract_external_id,
               name, status::text AS status, budget,
               "startDate" AS start_date, "dueDate" AS due_date, "completedAt" AS completed_at,
               "createdAt" AS created_at_source
        FROM operational.projects
    """,
    "invoices": """
        SELECT id AS external_id, "clientId" AS client_external_id, "projectId" AS project_external_id,
               number, subtotal, tax, total, status::text AS status,
               "dueDate" AS due_date, "paidAt" AS paid_at, "createdAt" AS created_at_source
        FROM operational.invoices
    """,
    "payments": """
        SELECT id AS external_id, "invoiceId" AS invoice_external_id,
               amount, method::text AS method, status::text AS status,
               "paidAt" AS paid_at, "createdAt" AS created_at_source
        FROM operational.payments
    """,
    "expenses": """
        SELECT id AS external_id, "projectId" AS project_external_id,
               category::text AS category, description, amount,
               date AS expense_date, "createdAt" AS created_at_source
        FROM operational.expenses
    """,
    "campaigns": """
        SELECT id AS external_id, name, channel, budget, status::text AS status,
               "startDate" AS start_date, "endDate" AS end_date,
               (metrics->>'impressions')::int AS impressions,
               (metrics->>'clicks')::int AS clicks,
               (metrics->>'leads')::int AS leads_count,
               (metrics->>'conversions')::int AS conversions,
               "createdAt" AS created_at_source
        FROM operational.campaigns
    """,
}

ENTITY_TARGET_TABLE: dict[str, str] = {
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

ENTITY_TARGET_COLUMNS: dict[str, list[str]] = {
    "clients": ["external_id", "name", "email", "phone", "company", "tax_id", "created_at_source"],
    "leads": [
        "external_id", "client_external_id", "name", "email", "phone", "company",
        "lead_source", "status", "created_at_source",
    ],
    "proposals": [
        "external_id", "client_external_id", "lead_external_id", "title", "total_amount", "status",
        "valid_until", "sent_at", "responded_at", "created_at_source",
    ],
    "contracts": [
        "external_id", "client_external_id", "proposal_external_id", "title", "value", "status",
        "start_date", "end_date", "signed_at", "created_at_source",
    ],
    "projects": [
        "external_id", "client_external_id", "contract_external_id", "name", "status", "budget",
        "start_date", "due_date", "completed_at", "created_at_source",
    ],
    "invoices": [
        "external_id", "client_external_id", "project_external_id", "number", "subtotal", "tax", "total",
        "status", "due_date", "paid_at", "created_at_source",
    ],
    "payments": [
        "external_id", "invoice_external_id", "amount", "method", "status", "paid_at", "created_at_source",
    ],
    "expenses": [
        "external_id", "project_external_id", "category", "description", "amount", "expense_date",
        "created_at_source",
    ],
    "campaigns": [
        "external_id", "name", "channel", "budget", "status", "start_date", "end_date",
        "impressions", "clicks", "leads_count", "conversions", "created_at_source",
    ],
}


class WebstudioConnector(DataSource):
    """Lê diretamente do Postgres da Webstudio (schema operational) e
    carrega em staging.* do Evolure Intelligence. Requer duas DSNs:
      - source_dsn: base da Webstudio (WEBSTUDIO_DATABASE_URL)
      - dest_dsn:   base do Evolure Intelligence (DATABASE_URL habitual)
    """

    source_id = "webstudio"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._source_dsn = self.config.get("source_dsn") or os.environ.get("WEBSTUDIO_DATABASE_URL", "")
        self._dest_dsn = self.config.get("dest_dsn") or os.environ.get("DATABASE_URL", "")
        self._source_conn: psycopg.Connection | None = None
        self._dest_conn: psycopg.Connection | None = None

    def connect(self) -> None:
        if not self._source_dsn:
            raise RuntimeError("WEBSTUDIO_DATABASE_URL não está definido - não é possível ligar à Webstudio")
        if not self._dest_dsn:
            raise RuntimeError("DATABASE_URL não está definido - não é possível ligar ao Evolure Intelligence")
        self._source_conn = psycopg.connect(self._source_dsn, row_factory=dict_row)
        self._dest_conn = psycopg.connect(self._dest_dsn)

    def extract(self, entity: str) -> list[dict[str, Any]]:
        query = ENTITY_QUERIES.get(entity)
        if query is None:
            raise ValueError(f"Entidade desconhecida para a Webstudio: {entity}")
        assert self._source_conn is not None
        with self._source_conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()

    def transform(self, entity: str, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cleaned = []
        for record in raw_records:
            clean = dict(record)
            clean["external_id"] = str(clean["external_id"])
            cleaned.append(clean)
        return cleaned

    def load(self, entity: str, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0
        table = ENTITY_TARGET_TABLE.get(entity)
        columns = ENTITY_TARGET_COLUMNS.get(entity)
        if table is None or columns is None:
            raise ValueError(f"Entidade desconhecida para a Webstudio: {entity}")

        assert self._dest_conn is not None
        placeholders = ", ".join(f"%({col})s" for col in columns)
        column_list = ", ".join(columns)
        update_clause = ", ".join(f"{col} = EXCLUDED.{col}" for col in columns if col != "external_id")

        sql = f"""
            INSERT INTO {table} ({column_list})
            VALUES ({placeholders})
            ON CONFLICT (external_id) DO UPDATE SET {update_clause}, ingested_at = now()
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
