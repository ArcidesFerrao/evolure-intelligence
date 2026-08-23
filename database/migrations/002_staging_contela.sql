-- Fase 2: tabelas staging para os dados extraídos do Contela.
-- staging.* guarda dados já normalizados mas ainda não validados/promovidos
-- a core. O ContelaConnector escreve aqui via load().

CREATE TABLE IF NOT EXISTS staging.contela_orders (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,     -- id original no Contela
    customer_name VARCHAR(200),
    total_amount NUMERIC(14, 2),
    status VARCHAR(50),
    order_date TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS staging.contela_stock (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,     -- id original no Contela
    product_name VARCHAR(200),
    quantity NUMERIC(14, 2),
    supplier_name VARCHAR(200),
    updated_at_source TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);
