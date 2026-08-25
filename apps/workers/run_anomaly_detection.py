"""
Corre o Anomaly Engine sobre as métricas do mês atual. Corre depois de
todos os Analyzers (precisa de analytics.metrics já populado).

Uso:
    python run_anomaly_detection.py
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from analytics.anomalies.anomaly_engine import run as run_anomaly_engine  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.workers.run_anomaly_detection")


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL não está definido")

    anomalies = run_anomaly_engine(dsn)
    if not anomalies:
        logger.info("Nenhuma anomalia detetada (ou histórico ainda insuficiente).")
    for a in anomalies:
        logger.warning(
            "ANOMALIA [%s] %s: esperado=%.2f actual=%.2f (z=%.2f, confiança=%.2f)",
            a["severity"], a["metric"], a["expected"], a["actual"], a["z_score"], a["confidence"],
        )


if __name__ == "__main__":
    main()
