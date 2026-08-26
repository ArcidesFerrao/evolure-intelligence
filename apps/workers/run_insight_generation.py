"""
Corre o Insight Generator (Fase 5) para o mês atual. Corre depois de todos
os Analyzers, Anomaly Engine e Forecasting (precisa de analytics.* já
populado).

Uso:
    python run_insight_generation.py
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from intelligence.insights.insight_generator import run as run_insight_generator  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.workers.run_insight_generation")


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL não está definido")

    if not os.environ.get("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY não está definido - a saltar geração de insight.")
        return

    result = run_insight_generator(dsn)
    if result:
        logger.info("Insight (%s): %s", result["period"], result["insight_text"])


if __name__ == "__main__":
    main()
