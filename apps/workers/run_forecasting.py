"""
Corre o forecasting: primeiro atualiza actual_result de previsões antigas,
depois calcula novas previsões para o próximo período. Corre depois dos
Analyzers (precisa de analytics.metrics já populado para o período atual).

Uso:
    python run_forecasting.py
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from analytics.forecasting.sales_forecast import run as run_forecasting  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.workers.run_forecasting")


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL não está definido")

    forecasts = run_forecasting(dsn)
    for f in forecasts:
        logger.info(
            "%s -> %s: %.2f (modelo=%s, confiança=%.2f)",
            f["metric"], f["forecast_period"], f["predicted_value"], f["model"], f["confidence"],
        )


if __name__ == "__main__":
    main()
