-- Fase 6 (L3): DevelopmentEvent da Webstudio (Development Lab) como fonte
-- de dados, mesmo padrão staging -> core dos outros conectores.
--
-- "source" nas tabelas core.*/staging.* já significa "qual Lab" (webstudio,
-- contela) em todo o resto do schema - por isso o campo próprio do
-- DevelopmentEvent (Git/GitHub/IDE/...) chama-se "event_source" aqui, para
-- não colidir.
--
-- project_id É resolvido contra core.projects (já promovido). user/task
-- ainda NÃO têm tabela core própria (Webstudio User/Task não são
-- entidades comerciais ingeridas) - ficam como *_external_id em texto,
-- sem FK, até isso fazer sentido.

CREATE TABLE IF NOT EXISTS staging.webstudio_development_events (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    event_source VARCHAR(30),
    event_type VARCHAR(30),
    user_external_id VARCHAR(100),
    project_external_id VARCHAR(100),
    task_external_id VARCHAR(100),
    external_ref VARCHAR(200),
    metadata JSONB,
    occurred_at TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS core.development_events (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    event_source VARCHAR(30),
    event_type VARCHAR(30),
    user_external_id VARCHAR(100),
    project_id BIGINT REFERENCES core.projects(id),
    task_external_id VARCHAR(100),
    external_ref VARCHAR(200),
    metadata JSONB,
    occurred_at TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE INDEX IF NOT EXISTS idx_dev_events_event_type ON core.development_events (event_type);
CREATE INDEX IF NOT EXISTS idx_dev_events_project ON core.development_events (project_id);
