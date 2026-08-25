-- Fase 3: Anomaly Engine - guarda desvios detetados face ao histórico de
-- cada métrica. Formato alinhado com o exemplo do documento original
-- (type/severity/metric/expected/actual/confidence).

CREATE TABLE IF NOT EXISTS analytics.anomalies (
    id BIGSERIAL PRIMARY KEY,
    metric VARCHAR(100) NOT NULL,
    period VARCHAR(20) NOT NULL,
    expected_value NUMERIC(16, 2),
    actual_value NUMERIC(16, 2),
    deviation_pct NUMERIC(8, 4),
    z_score NUMERIC(8, 4),
    severity VARCHAR(10) NOT NULL,   -- low | medium | high
    confidence NUMERIC(4, 2),        -- 0-1, heurística simples baseada no z-score
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (metric, period)
);
