"""
Corre a ingestão de todos os Labs marcados como "active" no LAB_REGISTRY.

Uso manual (dentro do container dos workers, ou local com DATABASE_URL e
CONTELA_DATABASE_URL definidos):

    python run_ingestion.py

Fase 2 trata isto como corrida manual/on-demand. O agendamento automático
(scheduled jobs, ex: APScheduler ou cron) fica para quando houver mais do
que um Lab ativo a justificar isso.
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from data.ingestion.log_writer import persist_result  # noqa: E402
from data.ingestion.registry import active_sources  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.workers.run_ingestion")


def main() -> None:
    dest_dsn = os.environ.get("DATABASE_URL", "")
    if not dest_dsn:
        raise RuntimeError("DATABASE_URL não está definido")

    labs = active_sources()
    if not labs:
        logger.info("Nenhum Lab ativo no registo - nada para ingerir.")
        return

    for lab in labs:
        if lab.connector is None:
            logger.warning("Lab '%s' está ACTIVE mas sem connector - a saltar.", lab.id)
            continue

        connector = lab.connector()
        for entity in lab.entities:
            logger.info("A ingerir %s / %s...", lab.id, entity)
            result = connector.run(entity)
            persist_result(dest_dsn, result)
            if result.status == "success":
                logger.info(
                    "OK: %s / %s -> %d registos", lab.id, entity, result.records_processed
                )
            else:
                logger.error("FALHOU: %s / %s -> %s", lab.id, entity, result.error_message)


if __name__ == "__main__":
    main()
