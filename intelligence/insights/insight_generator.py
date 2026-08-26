"""
Insight Generator - orquestra a Fase 5.

Fluxo (igual ao diagrama do documento original):
PostgreSQL -> Python (Analytics já feito nas Fases 3) -> LLM -> Business Insight

O LLM nunca vê dados crus (core.*) - só o que analytics.* já calculou.
Isto não é só estética: significa que qualquer erro de interpretação é do
LLM, nunca de aritmética errada, porque a aritmética já está feita antes
de chegar aqui.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

from intelligence.llm.gemini_client import generate_text
from intelligence.prompts.executive_summary import build_prompt

logger = logging.getLogger("evolure.intelligence.insights")


def _get_metrics(conn: psycopg.Connection, period: str) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT metric, value, change, status FROM analytics.metrics WHERE period = %s",
            (period,),
        )
        return [dict(r) for r in cur.fetchall()]


def _get_anomalies(conn: psycopg.Connection, period: str) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT metric, expected_value, actual_value, severity, confidence
            FROM analytics.anomalies WHERE period = %s
            """,
            (period,),
        )
        return [dict(r) for r in cur.fetchall()]


def _get_forecast(conn: psycopg.Connection, period: str) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT metric, predicted_value, confidence, model
            FROM analytics.forecasts WHERE forecast_period = %s AND metric = 'monthly_revenue'
            """,
            (period,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def _save_insight(conn: psycopg.Connection, period: str, insight_text: str, snapshot: dict[str, Any], model: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO intelligence.insights (period, insight_text, metrics_snapshot, model)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (period) DO UPDATE
                SET insight_text = EXCLUDED.insight_text, metrics_snapshot = EXCLUDED.metrics_snapshot,
                    model = EXCLUDED.model, created_at = now()
            """,
            (period, insight_text, json.dumps(snapshot, default=str), model),
        )


def run(dsn: str, period: str | None = None) -> dict[str, Any] | None:
    """Gera e grava o insight executivo para `period` ('YYYY-MM', default:
    mês atual). Devolve None se não houver métricas suficientes para
    justificar chamar o LLM (evita gastar tokens à toa)."""
    if period is None:
        period = date.today().strftime("%Y-%m")

    with psycopg.connect(dsn) as conn:
        metrics = _get_metrics(conn, period)
        if not metrics:
            logger.info("Sem métricas para %s - a saltar geração de insight.", period)
            return None

        anomalies = _get_anomalies(conn, period)
        forecast = _get_forecast(conn, period)

        prompt = build_prompt(metrics, anomalies, forecast)
        insight_text = generate_text(prompt)

        snapshot = {"metrics": metrics, "anomalies": anomalies, "forecast": forecast}
        _save_insight(conn, period, insight_text, snapshot, model="gemini-3.6-flash")
        conn.commit()

    logger.info("Insight gerado para %s.", period)
    return {"period": period, "insight_text": insight_text}
