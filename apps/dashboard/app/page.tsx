// async function getApiHealth() {
//   const apiUrl = process.env.API_INTERNAL_URL || "http://localhost:8000";
//   try {
//     const res = await fetch(`${apiUrl}/health`, { cache: "no-store" });
//     return await res.json();
//   } catch (err) {
//     return { status: "unreachable", database: "unknown" };
//   }
// }
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
  if (status === "positive" || status === "success" || status === "ok")
    return "#1a7f37";
  if (status === "negative" || status === "failed") return "#cf222e";
  return "#666";
}

export default async function Home() {
  const [health, ingestion, analytics] = await Promise.all([
    getApiJson<{ status: string; database: string }>("/health"),
    getApiJson<{ runs: IngestionRun[] }>("/ingestion/status"),
    getApiJson<{ metrics: AnalyticsMetric[] }>("/analytics/metrics"),
  ]);

  const runs = ingestion?.runs ?? [];
  const metrics = analytics?.metrics ?? [];

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
            <span
              style={{
                color: statusColor(
                  health?.database === "connected" ? "ok" : "",
                ),
              }}
            >
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
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: "0.9rem",
            }}
          >
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
                <tr
                  key={`${run.source}-${run.entity}`}
                  style={{ borderBottom: "1px solid #f0f0f0" }}
                >
                  <td style={{ padding: "0.4rem" }}>{run.source}</td>
                  <td style={{ padding: "0.4rem" }}>{run.entity}</td>
                  <td
                    style={{
                      padding: "0.4rem",
                      color: statusColor(run.status),
                    }}
                  >
                    {run.status}
                  </td>
                  <td style={{ padding: "0.4rem" }}>{run.records_processed}</td>
                  <td style={{ padding: "0.4rem" }}>
                    {run.finished_at
                      ? new Date(run.finished_at).toLocaleString("pt-PT")
                      : "-"}
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
                style={{
                  border: "1px solid #ddd",
                  borderRadius: 8,
                  padding: "1rem",
                  minWidth: 180,
                }}
              >
                <div style={{ fontSize: "0.8rem", color: "#666" }}>
                  {m.metric} · {m.period}
                </div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>
                  {m.value.toLocaleString("pt-PT", {
                    maximumFractionDigits: 2,
                  })}
                </div>
                <div
                  style={{ color: statusColor(m.status), fontSize: "0.85rem" }}
                >
                  {m.change != null
                    ? `${(m.change * 100).toFixed(1)}% vs mês anterior`
                    : "sem comparação"}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <p style={{ color: "#999", fontSize: "0.8rem" }}>
        Cada secção reflete o estado real da base de dados. Novas fases seguem o
        mesmo padrão: endpoint na API + secção aqui.
      </p>
    </main>
  );
}
