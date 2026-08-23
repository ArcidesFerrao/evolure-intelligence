# Evolure Intelligence

Plataforma de Inteligência da Evolure Labs — monorepo.

## Estado atual: Fase 1 — Foundation

O que já existe neste esqueleto:
- Estrutura de pastas completa do monorepo (`apps/`, `data/`, `analytics/`, `intelligence/`, `tasks/`, `automation/`, `database/`)
- `docker-compose.yml` a subir PostgreSQL + API (FastAPI) + Dashboard (Next.js)
- PostgreSQL já criado com os 6 schemas em camada: `raw`, `staging`, `core`, `analytics`, `intelligence`, `tasks`
- API FastAPI mínima com `/health` (valida ligação à BD) e `/internal/ping` (valida chave interna)
- Dashboard Next.js mínimo que chama `/health` da API para provar que a cadeia dashboard → api → postgres funciona

## Como correr

```bash
cp .env.example .env
# edita o .env e troca as passwords/chaves de exemplo

docker compose up --build
```

Depois:
- Dashboard: http://localhost:3000 — deve mostrar "API: ok" e "Base de dados: connected"
- API: http://localhost:8000/health
- PostgreSQL: localhost:5432 (user/pass/db conforme `.env`)

Se os dois itens no dashboard aparecerem "ok" / "connected", a Fase 1 está concluída:
os três serviços estão a comunicar corretamente.

## Próximos passos (Fase 2 — Data Hub)

1. Criar a interface `DataSource` em `data/ingestion/` (connect/extract/transform/load)
2. Implementar `ContelaConnector` primeiro, porque já existe uma fonte de dados real
3. Popular `raw.ingestion_log` a cada corrida de ingestão
4. Criar as primeiras tabelas em `staging` e `core` para `orders` e `stock` do Contela

## Estrutura de pastas

```
evolure-intelligence/
├── apps/            # api (FastAPI), dashboard (Next.js), workers (jobs Python)
├── data/            # ingestion (por fonte), processing, validation
├── analytics/        # kpis, forecasting, anomalies, segmentation, ml
├── intelligence/      # llm, prompts, insights, recommendations, business_context
├── tasks/            # generator, prioritization, assignment, tracking
├── automation/        # email, notifications, api, rpa
├── database/          # migrations, schemas (init SQL), seeds
├── tests/
├── docs/
└── docker/
```
