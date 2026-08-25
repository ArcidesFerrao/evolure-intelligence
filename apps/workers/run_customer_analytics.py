"""
Corre o CustomerAnalyzer para o mês atual.

Uso:
    python run_customer_analytics.py
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from analytics.kpis.customer_analyzer import run as run_customer_analyzer  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.workers.run_customer_analytics")


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL não está definido")

    results = run_customer_analyzer(dsn)
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
