type AnalyticsMetric = {
  metric: string;
  value: number;
  change: number | null;
  period: string;
  status: "positive" | "negative" | "neutral";
};

type Anomaly = {
  metric: string;
  severity: "low" | "medium" | "high";
};

type Insight = {
  period: string;
  insight_text: string;
};

type Task = {
  priority: "low" | "medium" | "high";
  status: string;
};

async function getApiJson<T>(path: string): Promise<T | null> {
  const apiUrl = process.env.API_INTERNAL_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

function findMetric(
  metrics: AnalyticsMetric[],
  name: string,
): AnalyticsMetric | undefined {
  return metrics.find((m) => m.metric === name);
}

function fmt(value: number | undefined): string {
  if (value === undefined || value === null) return "—";
  return value.toLocaleString("pt-PT", { maximumFractionDigits: 0 });
}

function growthClass(status: string): string {
  if (status === "positive") return "positive";
  if (status === "negative") return "negative";
  return "neutral";
}

export default async function OverviewDashboard() {
  const [metricsData, anomalyData, insightData, taskData] = await Promise.all([
    getApiJson<{ metrics: AnalyticsMetric[] }>("/analytics/metrics"),
    getApiJson<{ anomalies: Anomaly[] }>("/analytics/anomalies"),
    getApiJson<{ insights: Insight[] }>("/intelligence/insights"),
    getApiJson<{ tasks: Task[] }>("/tasks"),
  ]);

  const metrics = metricsData?.metrics ?? [];
  const anomalies = anomalyData?.anomalies ?? [];
  const latestInsight = insightData?.insights?.[0];
  const tasks = taskData?.tasks ?? [];

  // Receita própria da Evolure Labs = só agency_* por agora (Webstudio).
  // Quando a Contela ligar faturação própria (platform_*), soma-se aqui.
  const ownRevenue = findMetric(metrics, "agency_gmv");
  const ownProfit = findMetric(metrics, "agency_profit");

  const contelaGmv = findMetric(metrics, "customer_business_gmv");
  const contelaCustomers = findMetric(
    metrics,
    "customer_business_active_customers",
  );
  const contelaSuppliers = findMetric(metrics, "active_suppliers");

  const webstudioLeads = findMetric(metrics, "new_leads_count");
  const webstudioConversion = findMetric(
    metrics,
    "proposal_conversion_rate_pct",
  );
  const webstudioProjects = findMetric(metrics, "projects_completed_count");

  const tasksPending = tasks.filter((t) => t.status === "PENDING");
  const tasksByPriority = {
    high: tasksPending.filter((t) => t.priority === "high").length,
    medium: tasksPending.filter((t) => t.priority === "medium").length,
    low: tasksPending.filter((t) => t.priority === "low").length,
  };
  const anomaliesHigh = anomalies.filter((a) => a.severity === "high").length;

  return (
    <main
      className={`page`}
      style={{ fontFamily: "var(--font-display), system-ui" }}
    >
      <p className="eyebrow">
        Evolure Intelligence · {ownRevenue?.period ?? "—"}
      </p>
      <h1 className="title">Visão Geral</h1>
      <p className="scopeNote">
        &quot;Receita própria&quot; conta só o que a Evolure Labs efetivamente
        fatura (hoje, só a Webstudio) - o Contela ainda não cobra os seus
        utilizadores.
      </p>

      {/* Hero: a única receita que é mesmo "nossa" hoje */}
      <div className="hero">
        <div>
          <div className="heroLabel">Receita própria da Evolure Labs (mês)</div>
          <div className="heroFigure">{fmt(ownRevenue?.value)} MZN</div>
        </div>
        {ownRevenue?.change != null && (
          <span className={`growthTag ${growthClass(ownRevenue.status)}`}>
            {ownRevenue.change >= 0 ? "▲" : "▼"}{" "}
            {(Math.abs(ownRevenue.change) * 100).toFixed(1)}%
          </span>
        )}
        <div className="forecastBlock">
          <div className="heroLabel">Lucro próprio (mês)</div>
          <div className="forecastFigure">{fmt(ownProfit?.value)} MZN</div>
        </div>
      </div>

      {latestInsight && (
        <p className="insightText">
          &ldquo;{latestInsight.insight_text}&rdquo;
        </p>
      )}

      {/* Contela Ecosystem */}
      <p className="sectionLabel">
        Contela Ecosystem — atividade de terceiros na plataforma
      </p>
      <div className="grid">
        <div className="metricCard">
          <div className="metricLabel">GMV agregado</div>
          <div className="metricFigure">{fmt(contelaGmv?.value)} MZN</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Clientes ativos</div>
          <div className="metricFigure">{fmt(contelaCustomers?.value)}</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Fornecedores ativos</div>
          <div className="metricFigure">{fmt(contelaSuppliers?.value)}</div>
        </div>
      </div>
      <p style={{ marginTop: "-0.5rem", marginBottom: "1.5rem" }}>
        <a
          href="/executive"
          style={{
            color: "var(--accent)",
            fontSize: "0.85rem",
            textDecoration: "none",
          }}
        >
          Ver Executive Dashboard do Contela →
        </a>
      </p>

      {/* Webstudio */}
      <p className="sectionLabel">Webstudio — negócio próprio</p>
      <div className="grid">
        <div className="metricCard">
          <div className="metricLabel">Novos leads</div>
          <div className="metricFigure">{fmt(webstudioLeads?.value)}</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Taxa de conversão</div>
          <div className="metricFigure">{fmt(webstudioConversion?.value)}%</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Projetos concluídos</div>
          <div className="metricFigure">{fmt(webstudioProjects?.value)}</div>
        </div>
      </div>
      <p style={{ marginTop: "-0.5rem", marginBottom: "1.5rem" }}>
        <a
          href="/webstudio"
          style={{
            color: "var(--accent)",
            fontSize: "0.85rem",
            textDecoration: "none",
          }}
        >
          Ver Funil de Vendas da Webstudio →
        </a>
      </p>

      {/* Intelligence: anomalias + tarefas por prioridade */}
      <p className="sectionLabel">Intelligence</p>
      <div className="grid">
        <div className="metricCard">
          <div className="metricLabel">Anomalias (alta severidade)</div>
          <div className="metricFigure">{anomaliesHigh}</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Tarefas · Alta</div>
          <div className="metricFigure">{tasksByPriority.high}</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Tarefas · Média</div>
          <div className="metricFigure">{tasksByPriority.medium}</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Tarefas · Baixa</div>
          <div className="metricFigure">{tasksByPriority.low}</div>
        </div>
      </div>
    </main>
  );
}
