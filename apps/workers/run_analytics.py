"""
Corre o SalesAnalyzer para o mês atual.

Uso:
    python run_analytics.py
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from analytics.kpis.sales_analyzer import run as run_sales_analyzer  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.workers.run_analytics")


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL não está definido")

    results = run_sales_analyzer(dsn)
    for metric in results:
        logger.info(
            "%s: %.2f (change=%s, status=%s)",
            metric["metric"],
            metric["value"],
            metric["change"],
            metric["status"],
        )


if __name__ == "__main__":
    main()
