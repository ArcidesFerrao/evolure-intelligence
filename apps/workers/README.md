# Workers

Vazio de propósito na Fase 1.

Aqui entram, a partir da Fase 2 (Data Hub) e Fase 3 (Analytics Engine):
- Scheduled jobs de ingestão (Contela, Website, CRM, External APIs)
- Pipelines ETL (raw -> staging -> core)
- Jobs de analytics/forecasting/anomaly detection agendados

Sugestão: usar APScheduler ou uma fila simples (RQ/Celery) ligada ao mesmo
PostgreSQL, para não introduzir infraestrutura extra ainda.
