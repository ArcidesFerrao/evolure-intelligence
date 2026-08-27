"""
SalesAnalyzer - calcula métricas a partir de core.revenue_transactions,
filtradas a revenue_type='CUSTOMER_BUSINESS' (atividade agregada dos
negócios - Services - que usam a Contela).

IMPORTANTE: isto NÃO é receita própria da Evolure Labs. É o volume
transacionado por todos os negócios que usam a plataforma Contela. Quando
a Contela passar a faturar os seus próprios utilizadores, essa receita
entra como revenue_type='PLATFORM_SUBSCRIPTION' (ou similar) na mesma
tabela, e merece o seu próprio Analyzer (ver database/migrations/011).

Princípio do plano original: Python calcula os números, o LLM (Fase 5) só
interpreta depois.

Métricas calculadas por período ("YYYY-MM"):
  - customer_business_gmv:                 soma de amount (Gross Merchandise Value)
  - customer_business_transaction_count:    nº de transações (vendas)
  - customer_business_avg_transaction_value: gmv / transaction_count
  - customer_business_gross_margin:         soma de (amount - cogs), cogs vindo de metadata
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

from analytics.kpis.period_utils import period_bounds, previous_period, status_for_change

logger = logging.getLogger("evolure.analytics.sales")

REVENUE_TYPE = "CUSTOMER_BUSINESS"
SOURCE = "contela"


def _compute_period_metrics(conn: psycopg.Connection, period: str) -> dict[str, float]:
    start, end = period_bounds(period)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                COALESCE(SUM(amount), 0) AS gmv,
                COALESCE(SUM(amount - COALESCE((metadata->>'cogs')::numeric, 0)), 0) AS gross_margin,
                COUNT(*) AS txn_count
            FROM core.revenue_transactions
            WHERE revenue_type = %s AND source = %s
              AND transaction_date >= %s AND transaction_date < %s
            """,
            (REVENUE_TYPE, SOURCE, start, end),
        )
        row = cur.fetchone()

    gmv = float(row["gmv"] or 0)
    gross_margin = float(row["gross_margin"] or 0)
    txn_count = int(row["txn_count"] or 0)
    avg_txn_value = gmv / txn_count if txn_count else 0.0
    return {
        "customer_business_gmv": gmv,
        "customer_business_transaction_count": float(txn_count),
        "customer_business_avg_transaction_value": avg_txn_value,
        "customer_business_gross_margin": gross_margin,
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
    """Calcula e grava as métricas para `period` ('YYYY-MM', default: mês
    atual). Devolve a lista de métricas calculadas."""
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

    logger.info("SalesAnalyzer: %d métricas calculadas para %s", len(results), period)
    return results
