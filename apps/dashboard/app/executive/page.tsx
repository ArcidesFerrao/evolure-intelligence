// import { Space_Grotesk, IBM_Plex_Mono } from "next/font/google";
// import styles from "../global.css";

// const display = Space_Grotesk({
//   subsets: ["latin"],
//   weight: ["500", "600"],
//   variable: "--font-display",
// });
// const mono = IBM_Plex_Mono({
//   subsets: ["latin"],
//   weight: ["400", "500"],
//   variable: "--font-mono",
// });

type AnalyticsMetric = {
  metric: string;
  value: number;
  change: number | null;
  period: string;
  status: "positive" | "negative" | "neutral";
};

type Anomaly = {
  metric: string;
  period: string;
  expected_value: number;
  actual_value: number;
  severity: "low" | "medium" | "high";
  confidence: number;
};

type Forecast = {
  metric: string;
  forecast_period: string;
  predicted_value: number;
  confidence: number;
  model: string;
};

type Insight = {
  period: string;
  insight_text: string;
  model: string;
  created_at: string;
};

type Task = {
  id: number;
  title: string;
  description: string;
  priority: "low" | "medium" | "high";
  category: string;
  status: string;
  automation_type: string | null;
  expected_impact: "low" | "medium" | "high";
  period: string | null;
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

function formatMoney(value: number): string {
  return value.toLocaleString("pt-PT", { maximumFractionDigits: 0 });
}

function growthClass(status: string): string {
  if (status === "positive") return "positive";
  if (status === "negative") return "negative";
  return "neutral";
}

function stampClass(severity: string): string {
  if (severity === "high") return "stamp stampHigh";
  if (severity === "medium") return "stamp stampMedium";
  return "stamp stampLow";
}

export default async function ExecutiveDashboard() {
  const [metricsData, anomalyData, forecastData, insightData, taskData] =
    await Promise.all([
      getApiJson<{ metrics: AnalyticsMetric[] }>("/analytics/metrics"),
      getApiJson<{ anomalies: Anomaly[] }>("/analytics/anomalies"),
      getApiJson<{ forecasts: Forecast[] }>("/analytics/forecasts"),
      getApiJson<{ insights: Insight[] }>("/intelligence/insights"),
      getApiJson<{ tasks: Task[] }>("/tasks"),
    ]);

  const metrics = metricsData?.metrics ?? [];
  const anomalies = anomalyData?.anomalies ?? [];
  const forecasts = forecastData?.forecasts ?? [];
  const latestInsight = insightData?.insights?.[0];
  const tasks = taskData?.tasks ?? [];

  const revenue = findMetric(metrics, "customer_business_gmv");
  const margin = findMetric(metrics, "customer_business_gross_margin");
  const customers = findMetric(metrics, "customer_business_active_customers");
  const suppliers = findMetric(metrics, "active_suppliers");
  const orders = findMetric(metrics, "customer_business_transaction_count");
  const avgOrder = findMetric(
    metrics,
    "customer_business_avg_transaction_value",
  );
  const stockValue = findMetric(metrics, "stock_value");
  const revenueForecast = forecasts.find(
    (f) => f.metric === "customer_business_gmv",
  );

  return (
    <main
      className={`page`}
      style={{ fontFamily: "var(--font-display), system-ui" }}
    >
      <p className="eyebrow">Livro de bordo · {revenue?.period ?? "—"}</p>
      <h1 className="title">Executive Dashboard</h1>
      <p className="scopeNote">
        Os números abaixo (Contela) representam a atividade agregada dos
        negócios que usam a plataforma — não é receita própria da Evolure Labs.
      </p>

      {/* Hero: receita é a única coisa que precisa de ser vista de longe */}
      <div className="hero">
        <div>
          <div className="heroLabel">Receita do mês</div>
          <div className="heroFigure">
            {revenue ? `${formatMoney(revenue.value)} MZN` : "—"}
          </div>
        </div>
        {revenue?.change != null && (
          <span className={`growthTag ${growthClass(revenue.status)}`}>
            {revenue.change >= 0 ? "▲" : "▼"}{" "}
            {(Math.abs(revenue.change) * 100).toFixed(1)}%
          </span>
        )}
        {revenueForecast && (
          <div className="forecastBlock">
            <div className="heroLabel">
              Previsão · {revenueForecast.forecast_period}
            </div>
            <div className="forecastFigure">
              {formatMoney(revenueForecast.predicted_value)} MZN
            </div>
          </div>
        )}
      </div>

      {/* Insight do LLM - interpretação em texto, nunca números que ele próprio calculou */}
      {latestInsight && (
        <p className="insightText">
          &ldquo;{latestInsight.insight_text}&rdquo;
        </p>
      )}

      {/* Métricas de apoio */}
      <div className="grid">
        <div className="metricCard">
          <div className="metricLabel">Margem bruta</div>
          <div className="metricFigure">
            {margin ? formatMoney(margin.value) : "—"}
          </div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Clientes ativos</div>
          <div className="metricFigure">
            {customers ? formatMoney(customers.value) : "—"}
          </div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Fornecedores ativos</div>
          <div className="metricFigure">
            {suppliers ? formatMoney(suppliers.value) : "—"}
          </div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Vendas</div>
          <div className="metricFigure">
            {orders ? formatMoney(orders.value) : "—"}
          </div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Ticket médio</div>
          <div className="metricFigure">
            {avgOrder ? formatMoney(avgOrder.value) : "—"}
          </div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Valor em stock</div>
          <div className="metricFigure">
            {stockValue ? formatMoney(stockValue.value) : "—"}
          </div>
        </div>
      </div>

      {/* Anomalias, como carimbos de alerta no livro de bordo */}
      <p className="sectionLabel">Anomalias</p>
      {anomalies.length === 0 ? (
        <p className="emptyState">Nada fora do padrão este período.</p>
      ) : (
        <div className="stampRow">
          {anomalies.map((a) => (
            <div
              key={`${a.metric}-${a.period}`}
              className={stampClass(a.severity)}
            >
              <span>{a.severity}</span>
              <span className="stampDetail">
                {a.metric}: esperado {formatMoney(a.expected_value)}, real{" "}
                {formatMoney(a.actual_value)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Oportunidades e tarefas - geradas pela Intelligence Engine (Fase 5/6) */}
      <p className="sectionLabel">Tarefas pendentes</p>
      {tasks.length === 0 ? (
        <p className="emptyState">Nenhuma tarefa gerada ainda.</p>
      ) : (
        <div className="stampRow">
          {tasks.map((t) => (
            <div
              key={t.id}
              className={stampClass(
                t.priority === "high"
                  ? "high"
                  : t.priority === "medium"
                    ? "medium"
                    : "low",
              )}
            >
              <span>
                {t.category} · {t.status}
              </span>
              <span className="stampDetail">{t.title}</span>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
