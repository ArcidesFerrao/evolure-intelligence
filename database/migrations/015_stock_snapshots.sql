-- StockSnapshot do Contela: histórico real de quantidade de stock ao
-- longo do tempo, por ServiceStockItem (a visão de um StockItem dentro de
-- uma Service específica). Isto é o que falta para o InventoryAnalyzer
-- deixar de ser só "o estado agora" e passar a ter tendência comparável
-- mês a mês, como o SalesAnalyzer já tem.

CREATE TABLE IF NOT EXISTS staging.contela_stock_snapshots (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(100) NOT NULL,
    organization_external_id VARCHAR(100),   -- a Service dona do ServiceStockItem
    stock_item_external_id VARCHAR(100),     -- o StockItem (liga a staging.contela_stock)
    quantity NUMERIC(14, 2),
    recorded_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS core.stock_snapshots (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_external_id VARCHAR(100) NOT NULL,
    organization_id BIGINT REFERENCES core.organizations(id),
    stock_id BIGINT REFERENCES core.stock(id),
    quantity NUMERIC(14, 2),
    recorded_at TIMESTAMPTZ NOT NULL,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_external_id)
);

CREATE INDEX IF NOT EXISTS idx_stock_snapshots_stock_recorded
    ON core.stock_snapshots (stock_id, recorded_at DESC);
