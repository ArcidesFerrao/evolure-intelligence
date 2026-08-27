"""
CustomerAnalyzer - calcula métricas de concentração de clientes a partir de
core.revenue_transactions (revenue_type='CUSTOMER_BUSINESS'), agrupado por
organization_id real (V2) - antes agrupava por texto solto (service_name),
o que não distinguia corretamente organizações com nomes parecidos.

"Cliente" aqui é uma organização (Service do Contela) que gerou vendas no
período. Mede quantas organizações ativas, quanto cada uma vale em média,
e quão concentrada está a receita nas maiores (risco de dependência).

Métricas por período ("YYYY-MM"):
  - customer_business_active_customers:        nº de organizações distintas com vendas no período
  - customer_business_avg_gmv_per_customer:     receita total / active_customers
  - customer_business_top5_gmv_share_pct:       % da receita do período que vem das 5 maiores organizações (0-100)
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

from analytics.kpis.period_utils import period_bounds, previous_period, status_for_change

logger = logging.getLogger("evolure.analytics.customer")

REVENUE_TYPE = "CUSTOMER_BUSINESS"
SOURCE = "contela"


def _compute_period_metrics(conn: psycopg.Connection, period: str) -> dict[str, float]:
    start, end = period_bounds(period)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT organization_id, SUM(amount) AS revenue
            FROM core.revenue_transactions
            WHERE revenue_type = %s AND source = %s
              AND transaction_date >= %s AND transaction_date < %s
              AND organization_id IS NOT NULL
            GROUP BY organization_id
            ORDER BY revenue DESC
            """,
            (REVENUE_TYPE, SOURCE, start, end),
        )
        rows = cur.fetchall()

    active_customers = len(rows)
    total_revenue = float(sum(r["revenue"] for r in rows)) if rows else 0.0
    top5_revenue = float(sum(r["revenue"] for r in rows[:5])) if rows else 0.0
    top5_share_pct = (top5_revenue / total_revenue * 100) if total_revenue else 0.0
    avg_revenue_per_customer = total_revenue / active_customers if active_customers else 0.0

    return {
        "customer_business_active_customers": float(active_customers),
        "customer_business_avg_gmv_per_customer": avg_revenue_per_customer,
        "customer_business_top5_gmv_share_pct": top5_share_pct,
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
    """Calcula e grava as métricas de clientes para `period` ('YYYY-MM',
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

    logger.info("CustomerAnalyzer: %d métricas calculadas para %s", len(results), period)
    return results
