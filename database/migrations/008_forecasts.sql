-- Fase 3: Prediction Engine. Campos alinhados com o documento original
-- (prediction, confidence, model, created_at, forecast_period, actual_result).
-- actual_result começa NULL e é preenchido automaticamente quando o
-- período previsto passa a ter dados reais (ver _backfill_actuals).

CREATE TABLE IF NOT EXISTS analytics.forecasts (
    id BIGSERIAL PRIMARY KEY,
    metric VARCHAR(100) NOT NULL,
    forecast_period VARCHAR(20) NOT NULL,
    predicted_value NUMERIC(16, 2) NOT NULL,
    confidence NUMERIC(4, 2),        -- 0-1
    model VARCHAR(50) NOT NULL,      -- "naive_last_value" | "linear_regression"
    actual_result NUMERIC(16, 2),    -- preenchido depois, para medir performance do modelo
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (metric, forecast_period)
);
