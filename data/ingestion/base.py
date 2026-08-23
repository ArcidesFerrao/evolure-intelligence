"""
Interface genérica que todo Lab connector implementa.

Cada Lab da Evolure (Contela, Webstudio, The Ject, DigiMart, Pay/Zamuka,
Farm Hub, ...) tem a sua própria base de dados e é tratado como uma fonte
externa. O contrato aqui é sempre o mesmo: connect -> extract -> transform
-> load. Isto é o que torna possível ligar um novo Lab sem reconstruir a
arquitetura, como previsto no plano original.

Um connector concreto (ex: ContelaConnector) só precisa de herdar de
DataSource e implementar os 4 métodos abaixo. run() trata da orquestração
e do registo em raw.ingestion_log automaticamente.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("evolure.ingestion")


@dataclass
class IngestionResult:
    """Resultado padronizado de uma corrida de ingestão, igual para
    qualquer Lab. É isto que fica registado em raw.ingestion_log."""

    source: str
    entity: str
    status: str = "pending"          # pending | success | failed
    records_processed: int = 0
    error_message: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None


class DataSource(ABC):
    """Interface base para qualquer fonte de dados (Lab) da Evolure.

    source_id: identificador curto e estável usado em raw.ingestion_log
               e no LAB_REGISTRY (ex: "contela", "webstudio").
    """

    source_id: str

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._connection: Any = None

    @abstractmethod
    def connect(self) -> None:
        """Estabelece ligação à fonte (API, base de dados, ficheiro, etc)."""
        raise NotImplementedError

    @abstractmethod
    def extract(self, entity: str) -> list[dict[str, Any]]:
        """Extrai os registos crus de uma entidade (ex: 'orders', 'leads')."""
        raise NotImplementedError

    @abstractmethod
    def transform(self, entity: str, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normaliza os registos crus para o formato esperado em staging."""
        raise NotImplementedError

    @abstractmethod
    def load(self, entity: str, records: list[dict[str, Any]]) -> int:
        """Grava os registos transformados (tipicamente em staging.*).
        Devolve o número de registos gravados."""
        raise NotImplementedError

    def disconnect(self) -> None:
        """Fecha a ligação. Override opcional - por omissão não faz nada."""
        self._connection = None

    def run(self, entity: str) -> IngestionResult:
        """Orquestra connect -> extract -> transform -> load para uma
        entidade, com tratamento de erro uniforme. Todos os connectors
        ganham isto automaticamente, sem reimplementar nada."""
        result = IngestionResult(source=self.source_id, entity=entity)
        try:
            self.connect()
            raw_records = self.extract(entity)
            clean_records = self.transform(entity, raw_records)
            result.records_processed = self.load(entity, clean_records)
            result.status = "success"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ingestão falhou: source=%s entity=%s", self.source_id, entity)
            result.status = "failed"
            result.error_message = str(exc)
        finally:
            result.finished_at = datetime.now(timezone.utc)
            self.disconnect()
        return result
