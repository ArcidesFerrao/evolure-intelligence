-- Fase 3: InventoryAnalyzer precisa de cost (valor de stock) e critical
-- (limiar de stock baixo, já definido pelo utilizador no Contela por item).

ALTER TABLE staging.contela_stock ADD COLUMN IF NOT EXISTS cost NUMERIC(14, 2);
ALTER TABLE staging.contela_stock ADD COLUMN IF NOT EXISTS critical INT;

ALTER TABLE core.stock ADD COLUMN IF NOT EXISTS cost NUMERIC(14, 2);
ALTER TABLE core.stock ADD COLUMN IF NOT EXISTS critical INT;
