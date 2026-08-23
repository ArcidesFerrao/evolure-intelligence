"""
Registo central de todos os Labs da Evolure como potenciais fontes de dados.

Decisão de negócio: todos os Labs se tornam fontes de dados do Evolure
Intelligence, cada um com o seu próprio connector (mesmo contrato
connect/extract/transform/load). Mas só faz sentido construir um connector
quando o Lab já tem dados reais a fluir - por isso este registo distingue
"planned" (Lab existe no roadmap, sem connector ainda) de "active"
(connector implementado e ligado).

Para ligar um novo Lab: implementa um DataSource em ingestion/<lab>/,
importa a classe aqui, e muda o status para "active".
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from data.ingestion.base import DataSource


class LabStatus(str, Enum):
    ACTIVE = "active"        # connector implementado e a correr
    READY = "ready"          # Lab tem dados reais, connector por construir
    PLANNED = "planned"      # Lab ainda não gera dados (design/pendente)


@dataclass(frozen=True)
class LabEntry:
    id: str                      # usado em raw.ingestion_log.source
    name: str
    status: LabStatus
    connector: type[DataSource] | None = None
    notes: str = ""


LAB_REGISTRY: dict[str, LabEntry] = {
    "contela": LabEntry(
        id="contela",
        name="Contela",
        status=LabStatus.READY,
        connector=None,  # TODO: ligar ContelaConnector quando implementado
        notes="Funcional com dados reais (stock, orders). Próximo a conectar.",
    ),
    "webstudio": LabEntry(
        id="webstudio",
        name="Webstudio",
        status=LabStatus.PLANNED,
        connector=None,
        notes="Só landing page ainda. Aguarda backend/admin (Campaign/Lead/Project).",
    ),
    "the_ject": LabEntry(
        id="the_ject",
        name="The Ject",
        status=LabStatus.PLANNED,
        connector=None,
        notes="Fase de arquitetura/design. Sem dados ainda.",
    ),
    "digimart": LabEntry(
        id="digimart",
        name="DigiMart",
        status=LabStatus.PLANNED,
        connector=None,
        notes="Inativo - pendente acesso a API de pagamento.",
    ),
    "pay_zamuka": LabEntry(
        id="pay_zamuka",
        name="Pay / Zamuka",
        status=LabStatus.PLANNED,
        connector=None,
        notes="Pendente registo de empresa e contratos.",
    ),
    "farm_hub": LabEntry(
        id="farm_hub",
        name="Farm Hub",
        status=LabStatus.PLANNED,
        connector=None,
        notes="Em estudo.",
    ),
}


def active_sources() -> list[LabEntry]:
    """Labs com connector implementado - o que o scheduler de ingestão corre hoje."""
    return [lab for lab in LAB_REGISTRY.values() if lab.status is LabStatus.ACTIVE]


def get_lab(lab_id: str) -> LabEntry:
    try:
        return LAB_REGISTRY[lab_id]
    except KeyError as exc:
        raise ValueError(f"Lab desconhecido: {lab_id}") from exc
