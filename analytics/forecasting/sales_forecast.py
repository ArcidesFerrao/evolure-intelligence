"""
Prediction Engine (forecasting inicial) - prevê o próximo período para
métricas transacionais (monthly_revenue, order_count), a partir do
histórico em analytics.metrics.

Honesto quanto à qualidade do modelo conforme o histórico disponível:
  - < 2 pontos de histórico: não prevê (sem base nenhuma)
  - 2 pontos: "naive_last_value" - assume que o próximo período repete o
    último valor conhecido. Confiança baixa (0.3), fixa.
  - >= 3 pontos: regressão linear simples sobre o histórico. Confiança
    derivada do R² do ajuste (quanto melhor a reta explica o histórico,
    mais confiança), com piso de 0.3 e teto de 0.95 (nunca 100% confiante -
    é uma projeção, não um facto).

Ciclo "Prediction -> Actual Result -> Compare": sempre que corre, primeiro
tenta preencher `actual_result` de previsões antigas cujo período já tem
dados reais em analytics.metrics - é isso que permite, no futuro, avaliar
se o modelo está a acertar (Model Performance do documento original).
"""
from __future__ import annotations

import logging
from typing import Any

import psycopg
from psycopg.rows import dict_row

from analytics.kpis.period_utils import next_period

logger = logging.getLogger("evolure.analytics.forecasting")

FORECAST_METRICS = ["monthly_revenue", "order_count"]
MIN_POINTS_FOR_REGRESSION = 3


def _linear_regression(xs: list[int], ys: list[float]) -> tuple[float, float, float]:
    """Mínimos quadrados simples, sem dependências externas.
    Devolve (slope, intercept, r_squared)."""
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0:
        return 0.0, mean_y, 0.0

    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = num / den
    intercept = mean_y - slope * mean_x

    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    if ss_tot == 0:
        r_squared = 1.0
    else:
        preds = [slope * x + intercept for x in xs]
        ss_res = sum((y - p) ** 2 for y, p in zip(ys, preds))
        r_squared = max(0.0, 1 - ss_res / ss_tot)

    return slope, intercept, r_squared


def _backfill_actuals(conn: psycopg.Connection) -> int:
    """Preenche actual_result de previsões cujo forecast_period já tem
    dados reais em analytics.metrics. Devolve quantas foram atualizadas."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE analytics.forecasts f
            SET actual_result = m.value
            FROM analytics.metrics m
            WHERE f.metric = m.metric
              AND f.forecast_period = m.period
              AND f.actual_result IS NULL
            """
        )
        return cur.rowcount


def _save_forecast(
    conn: psycopg.Connection, metric: str, forecast_period: str, predicted_value: float, confidence: float, model: str
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO analytics.forecasts (metric, forecast_period, predicted_value, confidence, model)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (metric, forecast_period) DO UPDATE
                SET predicted_value = EXCLUDED.predicted_value, confidence = EXCLUDED.confidence,
                    model = EXCLUDED.model, created_at = now()
            """,
            (metric, forecast_period, predicted_value, confidence, model),
        )


def _forecast_metric(conn: psycopg.Connection, metric: str) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT period, value FROM analytics.metrics WHERE metric = %s ORDER BY period ASC",
            (metric,),
        )
        rows = cur.fetchall()

    if len(rows) < 2:
        return None  # sem histórico suficiente para arriscar qualquer previsão

    values = [float(r["value"]) for r in rows]
    latest_period = rows[-1]["period"]
    target_period = next_period(latest_period)

    if len(rows) >= MIN_POINTS_FOR_REGRESSION:
        xs = list(range(len(values)))
        slope, intercept, r_squared = _linear_regression(xs, values)
        predicted = max(0.0, slope * len(values) + intercept)
        confidence = round(max(0.3, min(0.95, r_squared)), 2)
        model = "linear_regression"
    else:
        predicted = values[-1]
        confidence = 0.3
        model = "naive_last_value"

    predicted = round(predicted, 2)
    _save_forecast(conn, metric, target_period, predicted, confidence, model)
    return {
        "metric": metric,
        "forecast_period": target_period,
        "predicted_value": predicted,
        "confidence": confidence,
        "model": model,
    }


def run(dsn: str) -> list[dict[str, Any]]:
    """Atualiza actual_result de previsões antigas e calcula novas previsões
    para as métricas em FORECAST_METRICS. Devolve as previsões calculadas
    nesta corrida (não inclui as que não tinham histórico suficiente)."""
    results: list[dict[str, Any]] = []
    with psycopg.connect(dsn) as conn:
        updated = _backfill_actuals(conn)
        if updated:
            logger.info("Backfill: %d previsão(ões) antiga(s) comparada(s) com o resultado real.", updated)

        for metric in FORECAST_METRICS:
            forecast = _forecast_metric(conn, metric)
            if forecast:
                results.append(forecast)

        conn.commit()

    logger.info("Forecasting: %d previsões calculadas.", len(results))
    return results
