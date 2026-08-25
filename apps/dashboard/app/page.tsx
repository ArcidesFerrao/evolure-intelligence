// Padrão para fases futuras: 1 helper de fetch + 1 endpoint na API + 1 secção aqui.
// Nenhuma secção depende de outra - se uma fase ainda não tem dados, mostra
// um estado vazio em vez de rebentar as restantes.

type IngestionRun = {
  source: string;
  entity: string;
  status: string;
  records_processed: number;
  error_message: string | null;
  started_at: string;
  finished_at: string | null;
};

type AnalyticsMetric = {
  metric: string;
  value: number;
  change: number | null;
  period: string;
  status: "positive" | "negative" | "neutral";
  computed_at: string;
};

type Anomaly = {
  metric: string;
  period: string;
  expected_value: number;
  actual_value: number;
  deviation_pct: number | null;
  z_score: number;
  severity: "low" | "medium" | "high";
  confidence: number;
  detected_at: string;
};

type Forecast = {
  metric: string;
  forecast_period: string;
  predicted_value: number;
  confidence: number;
  model: string;
  actual_result: number | null;
  created_at: string;
};

async function getApiJson<T>(path: string): Promise<T | null> {
  // Este fetch corre no servidor Next.js (dentro do container), por isso
  // usa o nome do serviço na rede do Docker Compose, não "localhost".
  const apiUrl = process.env.API_INTERNAL_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

function statusColor(status: string) {
  if (status === "positive" || status === "success" || status === "ok") return "#1a7f37";
  if (status === "negative" || status === "failed") return "#cf222e";
  return "#666";
}

function severityColor(severity: string) {
  if (severity === "high") return "#cf222e";
  if (severity === "medium") return "#bf8700";
  return "#666";
}

export default async function Home() {
  const [health, ingestion, analytics, anomalyData, forecastData] = await Promise.all([
    getApiJson<{ status: string; database: string }>("/health"),
    getApiJson<{ runs: IngestionRun[] }>("/ingestion/status"),
    getApiJson<{ metrics: AnalyticsMetric[] }>("/analytics/metrics"),
    getApiJson<{ anomalies: Anomaly[] }>("/analytics/anomalies"),
    getApiJson<{ forecasts: Forecast[] }>("/analytics/forecasts"),
  ]);

  const runs = ingestion?.runs ?? [];
  const metrics = analytics?.metrics ?? [];
  const anomalies = anomalyData?.anomalies ?? [];
  const forecasts = forecastData?.forecasts ?? [];

  return (
    <main style={{ maxWidth: 900, margin: "0 auto" }}>
      <h1>Evolure Intelligence</h1>

      {/* Fase 1 - Foundation */}
      <section style={{ marginBottom: "2rem" }}>
        <h2>Fase 1 — Foundation</h2>
        <ul>
          <li>
            API:{" "}
            <span style={{ color: statusColor(health?.status ?? "") }}>
              {health?.status ?? "unreachable"}
            </span>
          </li>
          <li>
            Base de dados:{" "}
            <span style={{ color: statusColor(health?.database === "connected" ? "ok" : "") }}>
              {health?.database ?? "unknown"}
            </span>
          </li>
        </ul>
      </section>

      {/* Fase 2 - Data Hub */}
      <section style={{ marginBottom: "2rem" }}>
        <h2>Fase 2 — Data Hub</h2>
        {runs.length === 0 ? (
          <p style={{ color: "#666" }}>Sem corridas de ingestão ainda.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>
                <th style={{ padding: "0.4rem" }}>Fonte</th>
                <th style={{ padding: "0.4rem" }}>Entidade</th>
                <th style={{ padding: "0.4rem" }}>Estado</th>
                <th style={{ padding: "0.4rem" }}>Registos</th>
                <th style={{ padding: "0.4rem" }}>Última corrida</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={`${run.source}-${run.entity}`} style={{ borderBottom: "1px solid #f0f0f0" }}>
                  <td style={{ padding: "0.4rem" }}>{run.source}</td>
                  <td style={{ padding: "0.4rem" }}>{run.entity}</td>
                  <td style={{ padding: "0.4rem", color: statusColor(run.status) }}>{run.status}</td>
                  <td style={{ padding: "0.4rem" }}>{run.records_processed}</td>
                  <td style={{ padding: "0.4rem" }}>
                    {run.finished_at ? new Date(run.finished_at).toLocaleString("pt-PT") : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Fase 3 - Analytics Engine */}
      <section style={{ marginBottom: "2rem" }}>
        <h2>Fase 3 — Analytics Engine</h2>
        {metrics.length === 0 ? (
          <p style={{ color: "#666" }}>Sem métricas calculadas ainda.</p>
        ) : (
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            {metrics.map((m) => (
              <div
                key={`${m.metric}-${m.period}`}
                style={{ border: "1px solid #ddd", borderRadius: 8, padding: "1rem", minWidth: 180 }}
              >
                <div style={{ fontSize: "0.8rem", color: "#666" }}>
                  {m.metric} · {m.period}
                </div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>
                  {m.value.toLocaleString("pt-PT", { maximumFractionDigits: 2 })}
                </div>
                <div style={{ color: statusColor(m.status), fontSize: "0.85rem" }}>
                  {m.change != null ? `${(m.change * 100).toFixed(1)}% vs mês anterior` : "sem comparação"}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Fase 3 - Anomaly Engine */}
      <section style={{ marginBottom: "2rem" }}>
        <h2>Fase 3 — Anomalias</h2>
        {anomalies.length === 0 ? (
          <p style={{ color: "#666" }}>
            Nenhuma anomalia detetada (ou histórico ainda insuficiente para comparar).
          </p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>
                <th style={{ padding: "0.4rem" }}>Métrica</th>
                <th style={{ padding: "0.4rem" }}>Período</th>
                <th style={{ padding: "0.4rem" }}>Esperado</th>
                <th style={{ padding: "0.4rem" }}>Real</th>
                <th style={{ padding: "0.4rem" }}>Severidade</th>
                <th style={{ padding: "0.4rem" }}>Confiança</th>
              </tr>
            </thead>
            <tbody>
              {anomalies.map((a) => (
                <tr key={`${a.metric}-${a.period}`} style={{ borderBottom: "1px solid #f0f0f0" }}>
                  <td style={{ padding: "0.4rem" }}>{a.metric}</td>
                  <td style={{ padding: "0.4rem" }}>{a.period}</td>
                  <td style={{ padding: "0.4rem" }}>{a.expected_value.toLocaleString("pt-PT")}</td>
                  <td style={{ padding: "0.4rem" }}>{a.actual_value.toLocaleString("pt-PT")}</td>
                  <td style={{ padding: "0.4rem", color: severityColor(a.severity), fontWeight: 600 }}>
                    {a.severity}
                  </td>
                  <td style={{ padding: "0.4rem" }}>{(a.confidence * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Fase 3 - Prediction Engine */}
      <section style={{ marginBottom: "2rem" }}>
        <h2>Fase 3 — Previsão</h2>
        {forecasts.length === 0 ? (
          <p style={{ color: "#666" }}>Sem previsões calculadas ainda (histórico insuficiente).</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.9rem" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #ddd" }}>
                <th style={{ padding: "0.4rem" }}>Métrica</th>
                <th style={{ padding: "0.4rem" }}>Período previsto</th>
                <th style={{ padding: "0.4rem" }}>Previsto</th>
                <th style={{ padding: "0.4rem" }}>Real</th>
                <th style={{ padding: "0.4rem" }}>Modelo</th>
                <th style={{ padding: "0.4rem" }}>Confiança</th>
              </tr>
            </thead>
            <tbody>
              {forecasts.map((f) => (
                <tr key={`${f.metric}-${f.forecast_period}`} style={{ borderBottom: "1px solid #f0f0f0" }}>
                  <td style={{ padding: "0.4rem" }}>{f.metric}</td>
                  <td style={{ padding: "0.4rem" }}>{f.forecast_period}</td>
                  <td style={{ padding: "0.4rem" }}>{f.predicted_value.toLocaleString("pt-PT")}</td>
                  <td style={{ padding: "0.4rem" }}>
                    {f.actual_result != null ? f.actual_result.toLocaleString("pt-PT") : "ainda por vir"}
                  </td>
                  <td style={{ padding: "0.4rem", color: "#666" }}>{f.model}</td>
                  <td style={{ padding: "0.4rem" }}>{(f.confidence * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <p style={{ color: "#999", fontSize: "0.8rem" }}>
        Cada secção reflete o estado real da base de dados. Novas fases seguem o mesmo padrão:
        endpoint na API + secção aqui.
      </p>
    </main>
  );
}
