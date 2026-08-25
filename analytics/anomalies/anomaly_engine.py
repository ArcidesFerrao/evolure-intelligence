"""
Anomaly Engine - deteta quando uma métrica foge do padrão histórico.

Abordagem: para cada métrica com valor no período atual, compara com a
média e desvio-padrão dos últimos períodos anteriores (z-score). Se o
valor atual estiver a mais de Z_SCORE_THRESHOLD desvios-padrão da média
histórica, marca como anomalia.

Limitação honesta: com poucos períodos de histórico (< MIN_HISTORY_POINTS),
não há dados suficientes para estabelecer um padrão - a métrica é ignorada
nesse caso, em vez de arriscar falsos positivos. A qualidade da deteção
melhora à medida que mais meses de analytics.metrics se acumulam. Métricas
do InventoryAnalyzer (que não variam por período, ver inventory_analyzer.py)
não geram histórico útil aqui até ligarmos StockSnapshot.
"""
from __future__ import annotations

import logging
import statistics
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger("evolure.analytics.anomaly")

MIN_HISTORY_POINTS = 3
Z_SCORE_THRESHOLD = 2.0
LOOKBACK_PERIODS = 6


def _severity_for_z(z: float) -> str:
    az = abs(z)
    if az >= 3:
        return "high"
    if az >= 2.5:
        return "medium"
    return "low"


def _confidence_for_z(z: float) -> float:
    # Heurística simples, não estatisticamente rigorosa: quanto mais longe
    # da média, maior a confiança de que é mesmo anómalo (não ruído).
    return round(min(0.99, abs(z) / 4), 2)


def _get_current_metrics(conn: psycopg.Connection, period: str) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT metric, value FROM analytics.metrics WHERE period = %s", (period,))
        return cur.fetchall()


def _get_history(conn: psycopg.Connection, metric: str, before_period: str) -> list[float]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT value FROM analytics.metrics
            WHERE metric = %s AND period < %s
            ORDER BY period DESC
            LIMIT %s
            """,
            (metric, before_period, LOOKBACK_PERIODS),
        )
        return [float(r["value"]) for r in cur.fetchall()]


def _save_anomaly(
    conn: psycopg.Connection,
    metric: str,
    period: str,
    expected: float,
    actual: float,
    z_score: float,
    severity: str,
    confidence: float,
) -> None:
    deviation_pct = (actual - expected) / expected if expected else None
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO analytics.anomalies
                (metric, period, expected_value, actual_value, deviation_pct, z_score, severity, confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (metric, period) DO UPDATE
                SET expected_value = EXCLUDED.expected_value, actual_value = EXCLUDED.actual_value,
                    deviation_pct = EXCLUDED.deviation_pct, z_score = EXCLUDED.z_score,
                    severity = EXCLUDED.severity, confidence = EXCLUDED.confidence, detected_at = now()
            """,
            (metric, period, expected, actual, deviation_pct, z_score, severity, confidence),
        )


def run(dsn: str, period: str | None = None) -> list[dict[str, Any]]:
    """Analisa todas as métricas do período `period` (default: mês atual)
    contra o histórico e grava as anomalias encontradas. Devolve a lista
    de anomalias detetadas (não a lista de todas as métricas analisadas)."""
    if period is None:
        period = date.today().strftime("%Y-%m")

    anomalies: list[dict[str, Any]] = []
    with psycopg.connect(dsn) as conn:
        current_metrics = _get_current_metrics(conn, period)

        for row in current_metrics:
            metric = row["metric"]
            actual = float(row["value"])
            history = _get_history(conn, metric, period)

            if len(history) < MIN_HISTORY_POINTS:
                continue  # histórico insuficiente - não arrisca falso positivo

            mean = statistics.mean(history)
            stdev = statistics.pstdev(history)
            if stdev == 0:
                continue  # sem variação histórica - qualquer desvio seria ambíguo

            z_score = (actual - mean) / stdev
            if abs(z_score) < Z_SCORE_THRESHOLD:
                continue  # dentro do padrão esperado

            severity = _severity_for_z(z_score)
            confidence = _confidence_for_z(z_score)
            _save_anomaly(conn, metric, period, mean, actual, z_score, severity, confidence)
            anomalies.append(
                {
                    "metric": metric,
                    "period": period,
                    "expected": round(mean, 2),
                    "actual": actual,
                    "z_score": round(z_score, 2),
                    "severity": severity,
                    "confidence": confidence,
                }
            )

        conn.commit()

    logger.info("AnomalyEngine: %d anomalias detetadas para %s", len(anomalies), period)
    return anomalies
