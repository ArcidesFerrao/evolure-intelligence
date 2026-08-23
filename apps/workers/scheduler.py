"""
Corre o ciclo ingestão -> promoção automaticamente, a cada N minutos.
Substitui a necessidade de correr run_ingestion.py / run_promotion.py
à mão.

Configuração via INGESTION_INTERVAL_MINUTES (default: 30).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

import run_ingestion
import run_promotion

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.scheduler")

INTERVAL_MINUTES = int(os.environ.get("INGESTION_INTERVAL_MINUTES", "30"))


def run_cycle() -> None:
    logger.info("=== Início do ciclo de ingestão + promoção ===")
    try:
        run_ingestion.main()
    except Exception:
        logger.exception("run_ingestion falhou - a promoção corre à mesma sobre o que já estiver em staging")
    try:
        run_promotion.main()
    except Exception:
        logger.exception("run_promotion falhou")
    logger.info("=== Fim do ciclo ===")


def main() -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_cycle,
        "interval",
        minutes=INTERVAL_MINUTES,
        next_run_time=datetime.now(),  # corre uma vez logo ao arrancar, não só depois do 1º intervalo
        id="ingestion_cycle",
    )
    logger.info("Scheduler a arrancar - ciclo a cada %d minutos.", INTERVAL_MINUTES)
    scheduler.start()


if __name__ == "__main__":
    main()
