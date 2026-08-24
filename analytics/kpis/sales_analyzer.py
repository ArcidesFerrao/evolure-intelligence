"""
SalesAnalyzer - calcula métricas de vendas a partir de core.orders.

Princípio do plano original: Python calcula os números, o LLM (Fase 5) só
interpreta depois. Os resultados aqui são o que a Intelligence Engine vai
ler - nunca deve receber os dados crus.

Métricas calculadas por período ("YYYY-MM"):
  - monthly_revenue:  soma de total_amount
  - order_count:      número de pedidos
  - avg_order_value:  monthly_revenue / order_count

Cada métrica é comparada com o período anterior para calcular `change`
(variação %), replicando o formato do exemplo no documento original:
{"metric": "monthly_revenue", "value": 520000, "change": -0.08, ...}
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger("evolure.analytics.sales")


def _period_bounds(period: str) -> tuple[date, date]:
    """'YYYY-MM' -> (primeiro dia do mês, primeiro dia do mês seguinte)."""
    year, month = map(int, period.split("-"))
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def _previous_period(period: str) -> str:
    year, month = map(int, period.split("-"))
    if month == 1:
        return f"{year - 1}-12"
    return f"{year}-{month - 1:02d}"


def _compute_period_metrics(conn: psycopg.Connection, period: str) -> dict[str, float]:
    start, end = _period_bounds(period)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                COALESCE(SUM(total_amount), 0) AS revenue,
                COUNT(*) AS order_count
            FROM core.orders
            WHERE order_date >= %s AND order_date < %s
            """,
            (start, end),
        )
        row = cur.fetchone()

    revenue = float(row["revenue"] or 0)
    order_count = int(row["order_count"] or 0)
    avg_order_value = revenue / order_count if order_count else 0.0
    return {
        "monthly_revenue": revenue,
        "order_count": float(order_count),
        "avg_order_value": avg_order_value,
    }


def _status_for_change(change: float | None) -> str:
    if change is None:
        return "neutral"  # sem período anterior para comparar (ex: primeiro mês de dados)
    if change > 0:
        return "positive"
    if change < 0:
        return "negative"
    return "neutral"


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
    """Calcula e grava as métricas de vendas para `period` ('YYYY-MM',
    default: mês atual). Devolve a lista de métricas calculadas."""
    if period is None:
        period = date.today().strftime("%Y-%m")
    previous_period = _previous_period(period)

    results: list[dict[str, Any]] = []
    with psycopg.connect(dsn) as conn:
        current = _compute_period_metrics(conn, period)
        previous = _compute_period_metrics(conn, previous_period)

        for metric_name, current_value in current.items():
            previous_value = previous.get(metric_name, 0)
            change = (current_value - previous_value) / previous_value if previous_value else None
            status = _status_for_change(change)
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
