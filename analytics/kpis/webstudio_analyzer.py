"""
WebstudioAnalyzer - calcula métricas de negócio próprio da Webstudio, por
período, com comparação ao mês anterior (mesmo padrão do SalesAnalyzer e
CustomerAnalyzer).

IMPORTANTE: "agency_*" é receita e lucro PRÓPRIOS da Evolure Labs (a
Webstudio a fechar projetos) - diferente de "customer_business_*" do
Contela, que é atividade agregada de terceiros. Ver database/migrations/013.

Métricas por período ("YYYY-MM"):
  - agency_gmv:                    receita reconhecida (pagamentos concluídos)
  - agency_transaction_count:      nº de pagamentos reconhecidos
  - agency_avg_transaction_value:  agency_gmv / agency_transaction_count
  - agency_expenses:               despesas do período (core.expenses)
  - agency_profit:                 agency_gmv - agency_expenses (lucro real)
  - new_leads_count:                leads criados no período
  - proposals_sent_count:           propostas enviadas no período
  - proposals_accepted_count:       propostas respondidas e aceites no período
  - proposal_conversion_rate_pct:   aceites / enviadas * 100 (aproximação -
                                     uma proposta pode ser aceite num período
                                     diferente do envio, ver nota no código)
  - projects_completed_count:       projetos concluídos no período
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

from analytics.kpis.period_utils import period_bounds, previous_period, status_for_change

logger = logging.getLogger("evolure.analytics.webstudio")

SOURCE = "webstudio"
REVENUE_TYPE = "AGENCY_SERVICE"


def _compute_period_metrics(conn: psycopg.Connection, period: str) -> dict[str, float]:
    start, end = period_bounds(period)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS gmv, COUNT(*) AS txn_count
            FROM core.revenue_transactions
            WHERE revenue_type = %s AND source = %s
              AND transaction_date >= %s AND transaction_date < %s
            """,
            (REVENUE_TYPE, SOURCE, start, end),
        )
        revenue_row = cur.fetchone()

        cur.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM core.expenses
            WHERE source = %s AND expense_date >= %s AND expense_date < %s
            """,
            (SOURCE, start, end),
        )
        expenses_row = cur.fetchone()

        cur.execute(
            """
            SELECT COUNT(*) AS n FROM core.leads
            WHERE source = %s AND created_at_source >= %s AND created_at_source < %s
            """,
            (SOURCE, start, end),
        )
        new_leads = cur.fetchone()["n"]

        cur.execute(
            """
            SELECT COUNT(*) AS n FROM core.proposals
            WHERE source = %s AND sent_at >= %s AND sent_at < %s
            """,
            (SOURCE, start, end),
        )
        proposals_sent = cur.fetchone()["n"]

        cur.execute(
            """
            SELECT COUNT(*) AS n FROM core.proposals
            WHERE source = %s AND status = 'ACCEPTED' AND responded_at >= %s AND responded_at < %s
            """,
            (SOURCE, start, end),
        )
        proposals_accepted = cur.fetchone()["n"]

        cur.execute(
            """
            SELECT COUNT(*) AS n FROM core.projects
            WHERE source = %s AND completed_at >= %s AND completed_at < %s
            """,
            (SOURCE, start, end),
        )
        projects_completed = cur.fetchone()["n"]

    gmv = float(revenue_row["gmv"] or 0)
    txn_count = int(revenue_row["txn_count"] or 0)
    expenses = float(expenses_row["total"] or 0)
    avg_txn_value = gmv / txn_count if txn_count else 0.0
    conversion_rate = (proposals_accepted / proposals_sent * 100) if proposals_sent else 0.0

    return {
        "agency_gmv": gmv,
        "agency_transaction_count": float(txn_count),
        "agency_avg_transaction_value": avg_txn_value,
        "agency_expenses": expenses,
        "agency_profit": gmv - expenses,
        "new_leads_count": float(new_leads),
        "proposals_sent_count": float(proposals_sent),
        "proposals_accepted_count": float(proposals_accepted),
        "proposal_conversion_rate_pct": conversion_rate,
        "projects_completed_count": float(projects_completed),
    }


def _save_metric(
    conn: psycopg.Connection, metric: str, value: float, change: float | None, period: str, status: str
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO analytics.metrics (metric, value, change, period, status)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (metric, period) DO UPDATE
                SET value = EXCLUDED.value, change = EXCLUDED.change,
                    status = EXCLUDED.status, computed_at = now()
            """,
            (metric, value, change, period, status),
        )


def run(dsn: str, period: str | None = None) -> list[dict[str, Any]]:
    """Calcula e grava as métricas da Webstudio para `period` ('YYYY-MM',
    default: mês atual). Devolve a lista de métricas calculadas."""
    if period is None:
        period = date.today().strftime("%Y-%m")
    prev_period = previous_period(period)

    results: list[dict[str, Any]] = []
    with psycopg.connect(dsn) as conn:
        current = _compute_period_metrics(conn, period)
        previous = _compute_period_metrics(conn, prev_period)

        for metric_name, current_value in current.items():
            previous_value = previous.get(metric_name, 0)
            change = (current_value - previous_value) / previous_value if previous_value else None
            status = status_for_change(change)
            _save_metric(conn, metric_name, current_value, change, period, status)
            results.append(
                {
                    "metric": metric_name,
                    "value": current_value,
                    "change": change,
                    "period": period,
                    "status": status,
                }
            )
        conn.commit()

    logger.info("WebstudioAnalyzer: %d métricas calculadas para %s", len(results), period)
    return results
