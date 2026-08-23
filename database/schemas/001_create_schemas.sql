-- Fase 1: cria as camadas base da plataforma.
-- Este ficheiro corre automaticamente no primeiro arranque do container Postgres
-- (montado em /docker-entrypoint-initdb.d).

CREATE SCHEMA IF NOT EXISTS raw;          -- dados originais, sem transformação
CREATE SCHEMA IF NOT EXISTS staging;      -- dados temporários / em transformação
CREATE SCHEMA IF NOT EXISTS core;         -- dados empresariais normalizados
CREATE SCHEMA IF NOT EXISTS analytics;    -- métricas e modelos analíticos
CREATE SCHEMA IF NOT EXISTS intelligence; -- insights e recomendações do LLM
CREATE SCHEMA IF NOT EXISTS tasks;        -- plano de tarefas gerado

-- Tabela de controlo de ingestão: toda fonte de dados regista aqui cada corrida.
-- Serve para depuração e para os "scheduled jobs" da Fase 2 saberem o que já processaram.
CREATE TABLE IF NOT EXISTS raw.ingestion_log (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,           -- 'contela', 'website', 'crm', 'external'
    entity VARCHAR(100) NOT NULL,          -- ex: 'orders', 'stock'
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending | success | failed
    records_processed INT DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

-- Tabela de tarefas (Task Engine, Fase 5/6) — já criada agora para termos
-- o esqueleto completo do ciclo de dados desde a Fase 1.
CREATE TABLE IF NOT EXISTS tasks.business_tasks (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    priority VARCHAR(10) NOT NULL DEFAULT 'medium', -- low | medium | high
    category VARCHAR(50),
    source VARCHAR(50),                    -- qual engine gerou a tarefa
    assigned_to VARCHAR(100),
    deadline DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING | IN_PROGRESS | COMPLETED | REJECTED | AUTOMATED
    automation_type VARCHAR(50),
    expected_impact VARCHAR(10),           -- low | medium | high
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
