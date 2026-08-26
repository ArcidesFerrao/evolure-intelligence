"""
Corre o Task Generator (Fase 6) para o mês atual. Corre depois do Insight
Generator (Fase 5), que é de onde vem a base para a tarefa.

Uso:
    python run_task_generation.py
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tasks.generator.task_generator import run as run_task_generator  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.workers.run_task_generation")


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL não está definido")

    if not os.environ.get("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY não está definido - a saltar geração de tarefa.")
        return

    result = run_task_generator(dsn)
    if result:
        logger.info("Tarefa (%s): %s [%s/%s]", result["period"], result.get("title"), result.get("priority"), result.get("category"))


if __name__ == "__main__":
    main()
