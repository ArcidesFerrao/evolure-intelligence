type TaskProposal = {
  id: number;
  title: string;
  priority: "low" | "medium" | "high";
  status: string;
  category: string;
  created_at: string;
};

type Anomaly = {
  metric: string;
  period: string;
  deviation_pct: number;
  severity: string;
  detected_at: string;
};

type RecentDevelopmentEvent = {
  event_type: string;
  external_ref: string | null;
  occurred_at: string;
};

type MorningBrief = {
  generated_at: string;
  focus_recommendation: string;
  latest_insight: { period: string; insight_text: string; created_at: string } | null;
  pending_task_proposals: TaskProposal[];
  recent_anomalies: Anomaly[];
  webstudio: {
    leads_open: number;
    proposals_awaiting_response: number;
    projects_active: number;
    invoices_overdue: number;
    development_events_last_24h: number;
    recent_development_events: RecentDevelopmentEvent[];
  };
  contela: {
    out_of_stock_count: number;
  };
};

const PRIORITY_LABELS: Record<string, string> = {
  high: "Alta",
  medium: "Média",
  low: "Baixa",
};

const STATUS_LABELS: Record<string, string> = {
  PROPOSED: "Por decidir",
  ACCEPTED: "Aceite (a sincronizar)",
};

const EVENT_TYPE_LABELS: Record<string, string> = {
  COMMIT: "Commit",
  PR_CREATED: "Pull Request criado",
  PR_MERGED: "Pull Request integrado",
  BUILD_FAILED: "Build falhou",
  BUILD_SUCCEEDED: "Build concluído",
  TASK_COMPLETED: "Tarefa concluída",
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

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-PT", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default async function MorningBriefPage() {
  const brief = await getApiJson<MorningBrief>("/morning-brief");

  if (!brief) {
    return (
      <main className="page" style={{ fontFamily: "var(--font-display), system-ui" }}>
        <p className="eyebrow">Livro de bordo · Manhã</p>
        <h1 className="title">Morning Brief</h1>
        <p className="emptyState">
          Não foi possível carregar o brief agora — confirma se a API está a
          correr.
        </p>
      </main>
    );
  }

  return (
    <main className="page" style={{ fontFamily: "var(--font-display), system-ui" }}>
      <p className="eyebrow">Livro de bordo · Manhã</p>
      <h1 className="title">Morning Brief</h1>
      <p className="scopeNote">
        Gerado às {formatDateTime(brief.generated_at)}. Junta Webstudio
        (funil comercial + development lab), Contela (operação) e Labs
        (insights, propostas de tarefa, anomalias) num único resumo.
      </p>

      <div className="metricCard" style={{ marginBottom: "1.5rem", padding: "1.25rem" }}>
        <div className="metricLabel">Foco de hoje</div>
        <p style={{ fontSize: "1.1rem", marginTop: "0.5rem" }}>
          {brief.focus_recommendation}
        </p>
      </div>

      {brief.latest_insight && (
        <>
          <p className="sectionLabel">Último insight ({brief.latest_insight.period})</p>
          <p className="insightText">{brief.latest_insight.insight_text}</p>
        </>
      )}

      <p className="sectionLabel">Propostas de tarefa à espera</p>
      {brief.pending_task_proposals.length === 0 ? (
        <p className="emptyState">Nenhuma proposta pendente.</p>
      ) : (
        <div className="insightText">
          {brief.pending_task_proposals.map((p) => (
            <div key={p.id} style={{ marginBottom: "0.5rem" }}>
              <strong>[{PRIORITY_LABELS[p.priority] ?? p.priority}]</strong> {p.title}
              {" — "}
              {STATUS_LABELS[p.status] ?? p.status}
              {" · "}
              {p.category}
            </div>
          ))}
        </div>
      )}

      {brief.recent_anomalies.length > 0 && (
        <>
          <p className="sectionLabel">Anomalias recentes (7 dias)</p>
          <div className="insightText">
            {brief.recent_anomalies.map((a, i) => (
              <div key={i} style={{ marginBottom: "0.5rem" }}>
                <strong>{a.metric}</strong> ({a.period}) — desvio de{" "}
                {a.deviation_pct?.toFixed(1)}% · severidade {a.severity}
              </div>
            ))}
          </div>
        </>
      )}

      <p className="sectionLabel">Webstudio</p>
      <div className="grid">
        <div className="metricCard">
          <div className="metricLabel">Leads em aberto</div>
          <div className="metricFigure">{brief.webstudio.leads_open}</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Propostas enviadas</div>
          <div className="metricFigure">{brief.webstudio.proposals_awaiting_response}</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Projetos ativos</div>
          <div className="metricFigure">{brief.webstudio.projects_active}</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Faturas vencidas</div>
          <div className="metricFigure">{brief.webstudio.invoices_overdue}</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Eventos de dev (24h)</div>
          <div className="metricFigure">{brief.webstudio.development_events_last_24h}</div>
        </div>
      </div>

      {brief.webstudio.recent_development_events.length > 0 && (
        <div className="insightText" style={{ marginTop: "0.75rem" }}>
          {brief.webstudio.recent_development_events.map((ev, i) => (
            <div key={i} style={{ marginBottom: "0.3rem" }}>
              {EVENT_TYPE_LABELS[ev.event_type] ?? ev.event_type}
              {ev.external_ref ? ` — ${ev.external_ref}` : ""}
              {" · "}
              {formatDateTime(ev.occurred_at)}
            </div>
          ))}
        </div>
      )}

      <p className="sectionLabel">Contela</p>
      <div className="grid">
        <div className="metricCard">
          <div className="metricLabel">SKUs sem stock</div>
          <div className="metricFigure">{brief.contela.out_of_stock_count}</div>
        </div>
      </div>
    </main>
  );
}
