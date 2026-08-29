-- V2 (complemento): liga Order ao Supplier que recebe o pedido, além do
-- Service que o faz (já ligado desde a 011). Order.supplierId já existe
-- no schema do Contela e é obrigatório - só não estava a ser trazido.
-- Isto permite medir "fornecedores ativos" por período, não só clientes.

ALTER TABLE staging.contela_orders ADD COLUMN IF NOT EXISTS supplier_organization_external_id VARCHAR(100);
ALTER TABLE staging.contela_orders ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(200);

ALTER TABLE core.orders ADD COLUMN IF NOT EXISTS supplier_organization_id BIGINT REFERENCES core.organizations(id);
ALTER TABLE core.orders ADD COLUMN IF NOT EXISTS supplier_name VARCHAR(200);
