const metricConfig: Record<string, {
  label: string;
  description?: string;
  category: string;
  unit?: string;
  decimals?: number;
}> = {
  customer_business_gmv: {
    label: "GMV",
    description: "Volume total de vendas",
    category: "Performance",
    unit: "MT",
  },

  customer_business_gross_margin: {
    label: "Margem bruta",
    description: "Margem gerada pelas vendas",
    category: "Performance",
    unit: "MT",
  },

  customer_business_avg_transaction_value: {
    label: "Valor médio por transação",
    category: "Performance",
    unit: "MT",
    decimals: 2,
  },

  customer_business_active_customers: {
    label: "Clientes ativos",
    category: "Clientes",
  },

  customer_business_avg_gmv_per_customer: {
    label: "GMV por cliente",
    category: "Clientes",
    unit: "MT",
  },

  customer_business_transaction_count: {
    label: "Transações",
    category: "Clientes",
  },

  customer_business_top_gmv_share_pct: {
    label: "Concentração de GMV",
    description: "Percentagem do GMV proveniente dos principais clientes",
    category: "Clientes",
    unit: "%",
  },

  active_suppliers: {
    label: "Fornecedores ativos",
    category: "Operação",
  },

  stock_value: {
    label: "Valor do stock",
    category: "Inventário",
    unit: "MT",
  },

  total_skus: {
    label: "Produtos em stock",
    category: "Inventário",
  },

  low_stock_count: {
    label: "Stock baixo",
    category: "Inventário",
  },

  out_of_stock_count: {
    label: "Sem stock",
    category: "Inventário",
  },
};

export default metricConfig;