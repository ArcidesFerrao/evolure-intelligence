-- Substitui o schema especulativo da Webstudio (013) pelo real, agora que
-- o backend existe e partilhou o schema.prisma verdadeiro. Nada tinha dados
-- ainda (stub vazio), por isso é seguro remover e recriar.
--
-- Pipeline: Lead -> Proposal -> Contract -> Project -> Invoice -> Payment,
-- mais Expense (permite calcular lucro real, não só receita bruta).

DROP TABLE IF EXISTS core.projects CASCADE;
DROP TABLE IF EXISTS core.proposals CASCADE;
DROP TABLE IF EXISTS core.leads CASCADE;
DROP TABLE IF EXISTS core.wstudio_campaigns CASCADE;

CREATE TABLE IF NOT EXISTS core.clients (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    name VARCHAR(200),
    email VARCHAR(200),
    phone VARCHAR(50),
    company VARCHAR(200),
    tax_id VARCHAR(100),
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.leads (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    client_id BIGINT REFERENCES core.clients(id),
    name VARCHAR(200),
    email VARCHAR(200),
    phone VARCHAR(50),
    company VARCHAR(200),
    lead_source VARCHAR(100),        -- site, referral, campanha (texto livre no Webstudio)
    status VARCHAR(30) NOT NULL,     -- NEW | CONTACTED | QUALIFIED | PROPOSAL_SENT | WON | LOST
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.proposals (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    client_id BIGINT REFERENCES core.clients(id),
    lead_id BIGINT REFERENCES core.leads(id),
    title VARCHAR(200),
    total_amount NUMERIC(14, 2),
    status VARCHAR(30) NOT NULL,     -- DRAFT | SENT | ACCEPTED | REJECTED | EXPIRED
    valid_until TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.contracts (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    client_id BIGINT REFERENCES core.clients(id),
    proposal_id BIGINT REFERENCES core.proposals(id),
    title VARCHAR(200),
    value NUMERIC(14, 2),
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    status VARCHAR(30) NOT NULL,     -- DRAFT | SIGNED | ACTIVE | COMPLETED | CANCELLED
    signed_at TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.projects (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    client_id BIGINT REFERENCES core.clients(id),
    contract_id BIGINT REFERENCES core.contracts(id),
    name VARCHAR(200),
    status VARCHAR(30) NOT NULL,     -- PLANNING | IN_PROGRESS | ON_HOLD | COMPLETED | CANCELLED
    budget NUMERIC(14, 2),
    start_date TIMESTAMPTZ,
    due_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.invoices (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    client_id BIGINT REFERENCES core.clients(id),
    project_id BIGINT REFERENCES core.projects(id),
    number VARCHAR(100),
    subtotal NUMERIC(14, 2),
    tax NUMERIC(14, 2),
    total NUMERIC(14, 2),
    status VARCHAR(30) NOT NULL,     -- DRAFT | SENT | PAID | OVERDUE | CANCELLED
    due_date TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.payments (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    invoice_id BIGINT REFERENCES core.invoices(id),
    amount NUMERIC(14, 2),
    method VARCHAR(30),              -- BANK_TRANSFER | MPESA | EMOLA | CARD | CASH | OTHER
    status VARCHAR(30) NOT NULL,     -- PENDING | COMPLETED | FAILED | REFUNDED
    paid_at TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.expenses (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    project_id BIGINT REFERENCES core.projects(id),
    category VARCHAR(30),            -- SOFTWARE | HOSTING | MARKETING | EQUIPMENT | CONTRACTOR | TAXES | OTHER
    description VARCHAR(500),
    amount NUMERIC(14, 2),
    expense_date TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.wstudio_campaigns (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL DEFAULT 'webstudio',
    source_external_id VARCHAR(100) NOT NULL,
    name VARCHAR(200),
    channel VARCHAR(100),
    budget NUMERIC(14, 2),
    status VARCHAR(30) NOT NULL,     -- PLANNED | ACTIVE | PAUSED | COMPLETED
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    impressions INT,
    clicks INT,
    leads_count INT,
    conversions INT,
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

-- staging.* - espelho quase direto do que a query de extração devolve,
-- ainda sem validação nem resolução de referências (isso acontece na
-- promoção). Mesma forma dos core.* correspondentes, mas com *_external_id
-- em vez de FKs numéricas.

CREATE TABLE IF NOT EXISTS staging.webstudio_clients (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    name VARCHAR(200), email VARCHAR(200), phone VARCHAR(50), company VARCHAR(200), tax_id VARCHAR(100),
    created_at_source TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS staging.webstudio_leads (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    client_external_id VARCHAR(100),
    name VARCHAR(200), email VARCHAR(200), phone VARCHAR(50), company VARCHAR(200),
    lead_source VARCHAR(100), status VARCHAR(30),
    created_at_source TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS staging.webstudio_proposals (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    client_external_id VARCHAR(100), lead_external_id VARCHAR(100),
    title VARCHAR(200), total_amount NUMERIC(14, 2), status VARCHAR(30),
    valid_until TIMESTAMPTZ, sent_at TIMESTAMPTZ, responded_at TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS staging.webstudio_contracts (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    client_external_id VARCHAR(100), proposal_external_id VARCHAR(100),
    title VARCHAR(200), value NUMERIC(14, 2), status VARCHAR(30),
    start_date TIMESTAMPTZ, end_date TIMESTAMPTZ, signed_at TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS staging.webstudio_projects (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    client_external_id VARCHAR(100), contract_external_id VARCHAR(100),
    name VARCHAR(200), status VARCHAR(30), budget NUMERIC(14, 2),
    start_date TIMESTAMPTZ, due_date TIMESTAMPTZ, completed_at TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS staging.webstudio_invoices (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    client_external_id VARCHAR(100), project_external_id VARCHAR(100),
    number VARCHAR(100), subtotal NUMERIC(14, 2), tax NUMERIC(14, 2), total NUMERIC(14, 2), status VARCHAR(30),
    due_date TIMESTAMPTZ, paid_at TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS staging.webstudio_payments (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    invoice_external_id VARCHAR(100),
    amount NUMERIC(14, 2), method VARCHAR(30), status VARCHAR(30), paid_at TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS staging.webstudio_expenses (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    project_external_id VARCHAR(100),
    category VARCHAR(30), description VARCHAR(500), amount NUMERIC(14, 2), expense_date TIMESTAMPTZ,
    created_at_source TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS staging.webstudio_campaigns (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    name VARCHAR(200), channel VARCHAR(100), budget NUMERIC(14, 2), status VARCHAR(30),
    start_date TIMESTAMPTZ, end_date TIMESTAMPTZ,
    impressions INT, clicks INT, leads_count INT, conversions INT,
    created_at_source TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);
