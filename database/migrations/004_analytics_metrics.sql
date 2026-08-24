-- Fase 3: tabela genérica para métricas calculadas pelos Analyzers.
-- Um analyzer, várias métricas, todas no mesmo formato estruturado que a
-- Intelligence Engine (Fase 5) vai ler - nunca texto solto para o LLM.

CREATE TABLE IF NOT EXISTS analytics.metrics (
    id BIGSERIAL PRIMARY KEY,
    metric VARCHAR(100) NOT NULL,      -- ex: "monthly_revenue", "order_count"
    value NUMERIC(16, 2) NOT NULL,
    change NUMERIC(8, 4),              -- variação % vs período anterior (NULL se não houver período anterior)
    period VARCHAR(20) NOT NULL,       -- ex: "2026-08"
    status VARCHAR(20) NOT NULL,       -- positive | negative | neutral
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (metric, period)
);
