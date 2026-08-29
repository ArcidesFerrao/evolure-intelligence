-- Webstudio: schema vazio, pronto a receber quando o backend/admin da
-- Webstudio existir e for ligado como fonte de dados (source='webstudio').
--
-- Segue o funil do documento V2:
--   Lead -> Qualified Lead -> Proposal -> (Rejected | Accepted -> Client -> Project -> Payment -> Revenue)
--
-- IMPORTANTE: receita da Webstudio é receita PRÓPRIA da Evolure Labs
-- (agência a fechar projetos), diferente da receita agregada de terceiros
-- que vemos no Contela. Por isso usa revenue_type='AGENCY_SERVICE' em
-- core.revenue_transactions (a mesma tabela da 011, dimensão nova) - não
-- 'CUSTOMER_BUSINESS' nem 'PLATFORM_*'.

CREATE TABLE IF NOT EXISTS core.wstudio_campaigns (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    platform VARCHAR(50),          -- meta, google, etc
    cost NUMERIC(14, 2),
    impressions INT,
    clicks INT,
    leads_generated INT,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.leads (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    name VARCHAR(200),
    email VARCHAR(200),
    lead_source VARCHAR(100),       -- de onde veio (campanha, referral, orgânico)
    campaign_id BIGINT REFERENCES core.wstudio_campaigns(id),
    status VARCHAR(30) NOT NULL DEFAULT 'new',  -- new | contacted | qualified | proposal | negotiation | won | lost
    qualification VARCHAR(30),      -- cold | warm | hot
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.proposals (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    lead_id BIGINT REFERENCES core.leads(id),
    value NUMERIC(14, 2),
    service VARCHAR(200),
    status VARCHAR(30) NOT NULL DEFAULT 'sent',  -- sent | accepted | rejected
    response_time_hours NUMERIC(10, 2),
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.projects (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    proposal_id BIGINT REFERENCES core.proposals(id),
    client_name VARCHAR(200),
    service VARCHAR(200),
    estimated_hours NUMERIC(10, 2),
    actual_hours NUMERIC(10, 2),
    cost NUMERIC(14, 2),
    revenue NUMERIC(14, 2),
    profit NUMERIC(14, 2),
    status VARCHAR(30) NOT NULL DEFAULT 'active',  -- active | completed | delayed | cancelled
    delivery_date TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);
