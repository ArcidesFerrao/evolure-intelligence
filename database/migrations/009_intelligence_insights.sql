-- Fase 5: Intelligence Engine. Guarda os insights gerados pelo LLM a
-- partir das métricas já calculadas (nunca o contrário - o LLM não vê
-- dados crus, só o que o Python já processou).

CREATE TABLE IF NOT EXISTS intelligence.insights (
    id BIGSERIAL PRIMARY KEY,
    period VARCHAR(20) NOT NULL,
    insight_text TEXT NOT NULL,
    metrics_snapshot JSONB NOT NULL,   -- exatamente o que foi enviado ao LLM, para auditoria
    model VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (period)
);
