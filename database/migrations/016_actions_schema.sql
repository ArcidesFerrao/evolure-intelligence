-- Fase 6 (v2): substitui o schema "tasks" (fila de tarefas própria do
-- Labs, que na prática duplicava gestão de projeto) pelo schema "actions"
-- (propostas de ação), seguindo o princípio da arquitetura v3:
--
--   A Webstudio possui as Tasks. O Labs possui Task Proposals.
--
-- O Labs nunca escreve uma task real diretamente - só propõe. Uma
-- task_proposal segue PROPOSED -> ACCEPTED -> CREATED_IN_WEBSTUDIO
-- (quando a Webstudio confirma a criação e devolve o id real), ou
-- PROPOSED -> REJECTED. Automação só pode agir sobre uma proposta já
-- CREATED_IN_WEBSTUDIO - nunca sobre uma proposta ainda não confirmada
-- (ver automation/task_executor.py).

DROP TABLE IF EXISTS tasks.business_tasks;
DROP SCHEMA IF EXISTS tasks;

CREATE SCHEMA IF NOT EXISTS actions;

CREATE TABLE IF NOT EXISTS actions.task_proposals (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    priority VARCHAR(10) NOT NULL DEFAULT 'medium',   -- low | medium | high
    category VARCHAR(50),
    source VARCHAR(50) NOT NULL,                      -- qual engine gerou a proposta
    expected_impact VARCHAR(10),                      -- low | medium | high
    period VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'PROPOSED',    -- PROPOSED | ACCEPTED | REJECTED | CREATED_IN_WEBSTUDIO
    webstudio_task_id VARCHAR(50),                     -- preenchido só quando status = CREATED_IN_WEBSTUDIO
    recommendation_id BIGINT,                          -- referência opcional a intelligence.insights.id
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, period)
);

-- Decisão de automação para uma proposta já confirmada como task real na
-- Webstudio. NUNCA deve existir para uma proposta que ainda esteja em
-- PROPOSED/ACCEPTED/REJECTED - só depois de CREATED_IN_WEBSTUDIO.
CREATE TABLE IF NOT EXISTS actions.automation_proposals (
    id BIGSERIAL PRIMARY KEY,
    task_proposal_id BIGINT NOT NULL REFERENCES actions.task_proposals(id),
    decision VARCHAR(20) NOT NULL,                     -- HUMAN | AUTOMATION
    automation_type VARCHAR(50),                       -- nome do handler, quando decision = AUTOMATION
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (task_proposal_id)
);

CREATE TABLE IF NOT EXISTS actions.execution_requests (
    id BIGSERIAL PRIMARY KEY,
    automation_proposal_id BIGINT NOT NULL REFERENCES actions.automation_proposals(id),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',     -- PENDING | RUNNING | DONE | FAILED
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS actions.execution_results (
    id BIGSERIAL PRIMARY KEY,
    execution_request_id BIGINT NOT NULL REFERENCES actions.execution_requests(id),
    success BOOLEAN NOT NULL,
    output JSONB,
    error_message TEXT,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
