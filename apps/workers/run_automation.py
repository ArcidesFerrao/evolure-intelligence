"""
Corre o Automation Engine (Fase 6, v2) sobre task_proposals já confirmadas
na Webstudio (status=CREATED_IN_WEBSTUDIO). Marca cada uma como "HUMAN"
(nenhum handler automático existe ainda) ou executa-a, se um handler
estiver registado em automation/task_executor.py.

Uso:
    python run_automation.py
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from automation.task_executor import process_confirmed_proposals  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.workers.run_automation")


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL não está definido")

    result = process_confirmed_proposals(dsn)
    logger.info("Resultado: %s", result)


if __name__ == "__main__":
    main()
