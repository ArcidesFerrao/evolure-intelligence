-- Fase 2 (correção): StockItem no schema real do Contela não tem campo sku.
-- Idempotente e seguro correr mesmo que a coluna já não exista ou a tabela
-- ainda não tenha sido criada (nesse caso 002 já a cria sem sku, ver connector.py).

ALTER TABLE IF EXISTS staging.contela_stock DROP COLUMN IF EXISTS sku;
