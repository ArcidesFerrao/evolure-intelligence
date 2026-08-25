"""
Corre a promoção staging -> core para as entidades do Contela.
Corre depois de run_ingestion.py (staging tem de estar populado primeiro).

Uso:
    python run_promotion.py
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from data.processing.promote_to_core import promote  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("evolure.workers.run_promotion")

# Fase 2: só o Contela está ligado. Quando o Webstudio (ou outro Lab)
# passar a alimentar "orders"/"stock", adiciona aqui mais entradas
# (source, entities) em vez de espalhar isto por vários scripts.
SOURCES_TO_PROMOTE: list[tuple[str, list[str]]] = [
    ("contela", ["orders", "stock", "sales"]),
]


def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise RuntimeError("DATABASE_URL não está definido")

    for source, entities in SOURCES_TO_PROMOTE:
        for entity in entities:
            result = promote(entity, source=source, dsn=dsn)
            logger.info("%s / %s -> %s", source, entity, result)


if __name__ == "__main__":
    main()
