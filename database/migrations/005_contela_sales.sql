-- Fase 2/3 (correção): Sale é a receita real de retalho (Order é pedido de
-- reabastecimento entre Service e Supplier, coisa diferente - ver conversa).
-- cogs vem incluído para calcular margem bruta, não só receita.

CREATE TABLE IF NOT EXISTS staging.contela_sales (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    sale_date TIMESTAMPTZ,
    total_amount NUMERIC(14, 2),
    cogs NUMERIC(14, 2),
    payment_type VARCHAR(50),
    service_name VARCHAR(200),
    supplier_name VARCHAR(200),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS core.sales (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_external_id VARCHAR(100) NOT NULL,
    sale_date TIMESTAMPTZ,
    total_amount NUMERIC(14, 2),
    cogs NUMERIC(14, 2),
    payment_type VARCHAR(50),
    service_name VARCHAR(200),
    supplier_name VARCHAR(200),
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);
