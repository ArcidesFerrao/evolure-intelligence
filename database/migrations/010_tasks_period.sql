-- Fase 6: liga tarefas geradas automaticamente ao período que as originou,
-- evitando gerar a mesma tarefa em todos os ciclos do scheduler.
-- NULLs não colidem em UNIQUE no Postgres, por isso tarefas manuais
-- (sem period) continuam a funcionar sem restrição.

ALTER TABLE tasks.business_tasks ADD COLUMN IF NOT EXISTS period VARCHAR(20);
ALTER TABLE tasks.business_tasks ADD CONSTRAINT uq_tasks_source_period UNIQUE (source, period);
