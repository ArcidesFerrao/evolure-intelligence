import { Space_Grotesk, IBM_Plex_Mono } from "next/font/google";
import styles from "./executive.module.css";

const display = Space_Grotesk({ subsets: ["latin"], weight: ["500", "600"], variable: "--font-display" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono" });

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

function findMetric(metrics: AnalyticsMetric[], name: string): AnalyticsMetric | undefined {
  return metrics.find((m) => m.metric === name);
}

function formatMoney(value: number): string {
  return value.toLocaleString("pt-PT", { maximumFractionDigits: 0 });
}

function growthClass(status: string): string {
  if (status === "positive") return styles.positive;
  if (status === "negative") return styles.negative;
  return styles.neutral;
}

function stampClass(severity: string): string {
  if (severity === "high") return `${styles.stamp} ${styles.stampHigh}`;
  if (severity === "medium") return `${styles.stamp} ${styles.stampMedium}`;
  return `${styles.stamp} ${styles.stampLow}`;
}

export default async function ExecutiveDashboard() {
  const [metricsData, anomalyData, forecastData] = await Promise.all([
    getApiJson<{ metrics: AnalyticsMetric[] }>("/analytics/metrics"),
    getApiJson<{ anomalies: Anomaly[] }>("/analytics/anomalies"),
    getApiJson<{ forecasts: Forecast[] }>("/analytics/forecasts"),
  ]);

  const metrics = metricsData?.metrics ?? [];
  const anomalies = anomalyData?.anomalies ?? [];
  const forecasts = forecastData?.forecasts ?? [];

  const revenue = findMetric(metrics, "monthly_revenue");
  const margin = findMetric(metrics, "gross_margin");
  const customers = findMetric(metrics, "active_customers");
  const orders = findMetric(metrics, "order_count");
  const avgOrder = findMetric(metrics, "avg_order_value");
  const stockValue = findMetric(metrics, "stock_value");
  const revenueForecast = forecasts.find((f) => f.metric === "monthly_revenue");

  return (
    <main className={`${styles.page} ${display.variable} ${mono.variable}`} style={{ fontFamily: "var(--font-display), system-ui" }}>
      <p className={styles.eyebrow}>Livro de bordo · {revenue?.period ?? "—"}</p>
      <h1 className={styles.title}>Executive Dashboard</h1>

      {/* Hero: receita é a única coisa que precisa de ser vista de longe */}
      <div className={styles.hero}>
        <div>
          <div className={styles.heroLabel}>Receita do mês</div>
          <div className={styles.heroFigure}>
            {revenue ? `${formatMoney(revenue.value)} MZN` : "—"}
          </div>
        </div>
        {revenue?.change != null && (
          <span className={`${styles.growthTag} ${growthClass(revenue.status)}`}>
            {revenue.change >= 0 ? "▲" : "▼"} {(Math.abs(revenue.change) * 100).toFixed(1)}%
          </span>
        )}
        {revenueForecast && (
          <div className={styles.forecastBlock}>
            <div className={styles.heroLabel}>Previsão · {revenueForecast.forecast_period}</div>
            <div className={styles.forecastFigure}>{formatMoney(revenueForecast.predicted_value)} MZN</div>
          </div>
        )}
      </div>

      {/* Métricas de apoio */}
      <div className={styles.grid}>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Margem bruta</div>
          <div className={styles.metricFigure}>{margin ? formatMoney(margin.value) : "—"}</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Clientes ativos</div>
          <div className={styles.metricFigure}>{customers ? formatMoney(customers.value) : "—"}</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Vendas</div>
          <div className={styles.metricFigure}>{orders ? formatMoney(orders.value) : "—"}</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Ticket médio</div>
          <div className={styles.metricFigure}>{avgOrder ? formatMoney(avgOrder.value) : "—"}</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Valor em stock</div>
          <div className={styles.metricFigure}>{stockValue ? formatMoney(stockValue.value) : "—"}</div>
        </div>
      </div>

      {/* Anomalias, como carimbos de alerta no livro de bordo */}
      <p className={styles.sectionLabel}>Anomalias</p>
      {anomalies.length === 0 ? (
        <p className={styles.emptyState}>Nada fora do padrão este período.</p>
      ) : (
        <div className={styles.stampRow}>
          {anomalies.map((a) => (
            <div key={`${a.metric}-${a.period}`} className={stampClass(a.severity)}>
              <span>{a.severity}</span>
              <span className={styles.stampDetail}>
                {a.metric}: esperado {formatMoney(a.expected_value)}, real {formatMoney(a.actual_value)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Oportunidades e tarefas - ainda por construir (Fase 5/6) */}
      <p className={styles.sectionLabel}>Oportunidades e tarefas pendentes</p>
      <p className={styles.emptyState}>
        Chega com o Task Engine (Fase 6) e o Recommendation Engine (Fase 5) — ainda não construídos.
      </p>
    </main>
  );
}
