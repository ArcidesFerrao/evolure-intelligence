"""
InventoryAnalyzer - calcula métricas de stock a partir de core.stock.

Diferente do SalesAnalyzer: core.stock é sempre uma fotografia do estado
ATUAL (upsert por item, sem histórico) - não um registo de eventos por
período como core.sales. Por isso estas métricas não têm comparação com o
"mês anterior" (change fica None) - é o estado agora, não uma variação.

O Contela tem um model StockSnapshot que guardaria histórico de stock ao
longo do tempo; quando isso for ligado, dá para calcular tendência real
(ex: "valor de stock caiu 12% este mês").

Métricas:
  - stock_value:        soma de (quantity * cost) para itens com custo conhecido
  - low_stock_count:     nº de itens com quantity <= critical (limiar do Contela)
  - out_of_stock_count:  nº de itens com quantity = 0
  - total_skus:          nº total de itens de stock ativos
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger("evolure.analytics.inventory")


def _save_metric(conn: psycopg.Connection, metric: str, value: float, period: str) -> None:
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


def run(dsn: str, period: str | None = None) -> list[dict[str, Any]]:
    """Calcula e grava as métricas de inventário para `period` ('YYYY-MM',
    default: mês atual - usado só como etiqueta de quando foi calculado,
    já que a query em si não filtra por data)."""
    if period is None:
        period = date.today().strftime("%Y-%m")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
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

        metrics = {
            "stock_value": float(row["stock_value"] or 0),
            "low_stock_count": float(row["low_stock_count"] or 0),
            "out_of_stock_count": float(row["out_of_stock_count"] or 0),
            "total_skus": float(row["total_skus"] or 0),
        }

        results: list[dict[str, Any]] = []
        for metric_name, value in metrics.items():
            _save_metric(conn, metric_name, value, period)
            results.append(
                {"metric": metric_name, "value": value, "change": None, "period": period, "status": "neutral"}
            )
        conn.commit()

    logger.info("InventoryAnalyzer: %d métricas calculadas para %s", len(results), period)
    return results
