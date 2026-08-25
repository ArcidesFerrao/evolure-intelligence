"""
Corre o InventoryAnalyzer.

Uso:
    python run_inventory_analytics.py
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from analytics.kpis.inventory_analyzer import run as run_inventory_analyzer  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.workers.run_inventory_analytics")


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL não está definido")

    results = run_inventory_analyzer(dsn)
    for metric in results:
        logger.info("%s: %.2f", metric["metric"], metric["value"])


if __name__ == "__main__":
    main()
