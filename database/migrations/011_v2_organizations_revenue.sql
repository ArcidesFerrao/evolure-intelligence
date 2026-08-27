-- Fase 2/3 (V2 - re-arquitetura): adota o modelo core do documento V2.
--
-- Duas mudanças estruturais:
-- 1) core.organizations: Service e Supplier do Contela deixam de ser texto
--    solto (service_name/supplier_name) e passam a ter identidade própria,
--    permitindo agrupar/filtrar por organização individual no futuro.
-- 2) core.revenue_transactions: substitui core.sales como destino da
--    receita. O campo revenue_type distingue "atividade dos negócios que
--    usam a Contela" (CUSTOMER_BUSINESS) de "o que a Contela cobra pelos
--    seus próprios planos" (PLATFORM_*) - hoje só a primeira tem dados
--    reais; a segunda fica pronta a receber quando a Contela passar a
--    faturar os seus utilizadores.

CREATE TABLE IF NOT EXISTS core.organizations (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_external_id VARCHAR(100) NOT NULL,
    name VARCHAR(200),
    org_type VARCHAR(20) NOT NULL,   -- SERVICE | SUPPLIER (papel no Contela)
    created_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id, org_type)
);

CREATE TABLE IF NOT EXISTS core.revenue_transactions (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_external_id VARCHAR(100) NOT NULL,
    organization_id BIGINT REFERENCES core.organizations(id),
    customer_id BIGINT,               -- NULL por agora: Contela não rastreia clientes finais individuais
    amount NUMERIC(14, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'MZN',
    revenue_type VARCHAR(30) NOT NULL,  -- CUSTOMER_BUSINESS | PLATFORM_SUBSCRIPTION | PLATFORM_ADDON | PLATFORM_API_USAGE | PLATFORM_MARKETPLACE | PLATFORM_OTHER
    subscription_id BIGINT,           -- FK a core.subscriptions, só relevante para revenue_type PLATFORM_*
    product_id VARCHAR(100),
    transaction_date TIMESTAMPTZ NOT NULL,
    metadata JSONB,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE INDEX IF NOT EXISTS idx_revenue_transactions_type_date
    ON core.revenue_transactions (revenue_type, transaction_date);

-- Faturação da própria plataforma (Contela a cobrar os seus utilizadores).
-- Vazias por agora - a Contela ainda não fatura os seus utilizadores, mas
-- isto já fica pronto a receber quando essa funcionalidade existir lá.
CREATE TABLE IF NOT EXISTS core.plans (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_external_id VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,          -- Basic | Premium | Enterprise
    price NUMERIC(14, 2),
    billing_interval VARCHAR(20),        -- monthly | yearly
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.subscriptions (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_external_id VARCHAR(100) NOT NULL,
    organization_id BIGINT REFERENCES core.organizations(id),
    plan_id BIGINT REFERENCES core.plans(id),
    status VARCHAR(20),                  -- active | cancelled | past_due | trialing
    started_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.feature_usage (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    organization_id BIGINT REFERENCES core.organizations(id),
    feature VARCHAR(100) NOT NULL,
    usage_count INT,
    usage_duration_seconds INT,
    last_used_at TIMESTAMPTZ,
    period VARCHAR(20)
);

-- core.orders e core.stock ganham a ligação estrutural à organização
-- (antes só existia como texto em customer_name/supplier_name).
ALTER TABLE core.orders ADD COLUMN IF NOT EXISTS organization_id BIGINT REFERENCES core.organizations(id);
ALTER TABLE core.stock ADD COLUMN IF NOT EXISTS organization_id BIGINT REFERENCES core.organizations(id);

-- staging ganha as colunas de ligação (external id da organização), que a
-- promoção usa para resolver organization_id em core.*
ALTER TABLE staging.contela_orders ADD COLUMN IF NOT EXISTS organization_external_id VARCHAR(100);
ALTER TABLE staging.contela_stock ADD COLUMN IF NOT EXISTS organization_external_id VARCHAR(100);
ALTER TABLE staging.contela_sales ADD COLUMN IF NOT EXISTS organization_external_id VARCHAR(100);

CREATE TABLE IF NOT EXISTS staging.contela_organizations (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    name VARCHAR(200),
    org_type VARCHAR(20) NOT NULL,
    created_at_source TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id, org_type)
);
