"""
InventoryAnalyzer - três famílias de métricas com naturezas diferentes:

1) Métricas de SNAPSHOT (stock_value, low_stock_count, out_of_stock_count,
   total_skus) - vêm de core.stock, que é sempre uma fotografia do estado
   ATUAL (upsert por item, sem histórico). Sem comparação com "mês
   anterior" (change fica None) - é o estado agora, não uma variação.

2) active_suppliers - vem de core.orders (que TEM data por evento), filtrado
   por período, com comparação ao mês anterior.

3) stock_value_trend - reconstrói o valor de stock EM DATAS PASSADAS a
   partir de core.stock_snapshots (histórico real, ligado via
   StockSnapshot do Contela). Compara o valor no início deste período com
   o valor no início do anterior - a primeira métrica de inventário com
   tendência real, não só "o estado agora". Usa o custo ATUAL de cada item
   (core.stock.cost) como aproximação - se o custo mudou entretanto, o
   valor histórico reconstruído reflete o custo de hoje, não o da altura.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

from analytics.kpis.period_utils import period_bounds, previous_period, status_for_change

logger = logging.getLogger("evolure.analytics.inventory")


def _save_snapshot_metric(conn: psycopg.Connection, metric: str, value: float, period: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO analytics.metrics (metric, value, change, period, status)
            VALUES (%s, %s, NULL, %s, 'neutral')
            ON CONFLICT (metric, period) DO UPDATE
                SET value = EXCLUDED.value, status = 'neutral', computed_at = now()
            """,
            (metric, value, period),
        )


def _save_period_metric(
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


def _compute_snapshot_metrics(conn: psycopg.Connection) -> dict[str, float]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                COALESCE(SUM(quantity * cost), 0)                                   AS stock_value,
                COUNT(*) FILTER (WHERE critical IS NOT NULL AND quantity <= critical) AS low_stock_count,
                COUNT(*) FILTER (WHERE quantity = 0)                                 AS out_of_stock_count,
                COUNT(*)                                                             AS total_skus
            FROM core.stock
            """
        )
        row = cur.fetchone()

    return {
        "stock_value": float(row["stock_value"] or 0),
        "low_stock_count": float(row["low_stock_count"] or 0),
        "out_of_stock_count": float(row["out_of_stock_count"] or 0),
        "total_skus": float(row["total_skus"] or 0),
    }


def _compute_active_suppliers(conn: psycopg.Connection, period: str) -> float:
    start, end = period_bounds(period)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT COUNT(DISTINCT supplier_organization_id) AS active_suppliers
            FROM core.orders
            WHERE order_date >= %s AND order_date < %s
              AND supplier_organization_id IS NOT NULL
            """,
            (start, end),
        )
        row = cur.fetchone()
    return float(row["active_suppliers"] or 0)


def _compute_stock_value_at(conn: psycopg.Connection, as_of) -> float:
    """Reconstrói o valor de stock numa data passada: para cada item, pega
    no snapshot mais recente até essa data, multiplica pelo custo ATUAL
    (core.stock.cost - aproximação, ver docstring do módulo)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(latest.quantity * s.cost), 0) AS value
            FROM (
                SELECT DISTINCT ON (stock_id) stock_id, quantity
                FROM core.stock_snapshots
                WHERE recorded_at <= %s AND stock_id IS NOT NULL
                ORDER BY stock_id, recorded_at DESC
            ) latest
            JOIN core.stock s ON s.id = latest.stock_id
            """,
            (as_of,),
        )
        row = cur.fetchone()
    return float(row["value"] or 0)


def run(dsn: str, period: str | None = None) -> list[dict[str, Any]]:
    """Calcula e grava as métricas de inventário/fornecedores para `period`
    ('YYYY-MM', default: mês atual)."""
    if period is None:
        period = date.today().strftime("%Y-%m")
    prev_period = previous_period(period)

    results: list[dict[str, Any]] = []
    with psycopg.connect(dsn) as conn:
        # Snapshot - sem comparação, é o estado agora.
        for metric_name, value in _compute_snapshot_metrics(conn).items():
            _save_snapshot_metric(conn, metric_name, value, period)
            results.append(
                {"metric": metric_name, "value": value, "change": None, "period": period, "status": "neutral"}
            )

        # Por período - comparável ao mês anterior, como no SalesAnalyzer.
        current_suppliers = _compute_active_suppliers(conn, period)
        previous_suppliers = _compute_active_suppliers(conn, prev_period)
        change = (
            (current_suppliers - previous_suppliers) / previous_suppliers
            if previous_suppliers
            else None
        )
        status = status_for_change(change)
        _save_period_metric(conn, "active_suppliers", current_suppliers, change, period, status)
        results.append(
            {"metric": "active_suppliers", "value": current_suppliers, "change": change, "period": period, "status": status}
        )

        # Tendência real de stock, reconstruída a partir de StockSnapshot -
        # compara o valor no início deste mês com o início do anterior.
        current_start, _ = period_bounds(period)
        prev_start, _ = period_bounds(prev_period)
        value_at_current_start = _compute_stock_value_at(conn, current_start)
        value_at_prev_start = _compute_stock_value_at(conn, prev_start)
        trend_change = (
            (value_at_current_start - value_at_prev_start) / value_at_prev_start
            if value_at_prev_start
            else None
        )
        trend_status = status_for_change(trend_change)
        _save_period_metric(
            conn, "stock_value_trend", value_at_current_start, trend_change, period, trend_status
        )
        results.append(
            {
                "metric": "stock_value_trend", "value": value_at_current_start,
                "change": trend_change, "period": period, "status": trend_status,
            }
        )

        conn.commit()

    logger.info("InventoryAnalyzer: %d métricas calculadas para %s", len(results), period)
    return results
