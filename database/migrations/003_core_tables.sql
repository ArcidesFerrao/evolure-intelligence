-- Fase 2 (complemento): tabelas core - só dados validados chegam aqui.
-- "source" identifica de que Lab veio o registo (hoje só "contela"), o que
-- já prepara o terreno para quando outros Labs (ex: webstudio) alimentarem
-- as mesmas entidades conceptuais.

CREATE TABLE IF NOT EXISTS core.orders (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_external_id VARCHAR(100) NOT NULL,
    customer_name VARCHAR(200),
    total_amount NUMERIC(14, 2),
    status VARCHAR(50),
    order_date TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE TABLE IF NOT EXISTS core.stock (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_external_id VARCHAR(100) NOT NULL,
    product_name VARCHAR(200),
    quantity NUMERIC(14, 2),
    supplier_name VARCHAR(200),
    updated_at_source TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

-- Regista o que falhou validação, em vez de descartar silenciosamente.
-- Útil para perceber se há um problema sistemático numa fonte (ex: muitos
-- pedidos do Contela sem customer_name porque o join com Service falha).
CREATE TABLE IF NOT EXISTS raw.validation_rejects (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    entity VARCHAR(100) NOT NULL,
    external_id VARCHAR(100),
    reason TEXT,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
