"""
Corre o Automation Engine (Fase 6) sobre tarefas PENDING. Marca cada uma
como "manual" (nenhum handler automático existe ainda) ou executa-a, se
um handler estiver registado em automation/task_executor.py.

Uso:
    python run_automation.py
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from automation.task_executor import process_pending_tasks  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.workers.run_automation")


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL não está definido")

    result = process_pending_tasks(dsn)
    logger.info("Resultado: %s", result)


if __name__ == "__main__":
    main()
