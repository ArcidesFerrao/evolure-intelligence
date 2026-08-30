type Overview = {
  leads_total: number;
  leads_won: number;
  proposals_total: number;
  proposals_accepted: number;
  projects_active: number;
  projects_completed: number;
  revenue_total: number;
  expenses_total: number;
  profit_total: number;
  pipeline_value: number;
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

function fmt(value: number | undefined): string {
  if (value === undefined || value === null) return "—";
  return value.toLocaleString("pt-PT", { maximumFractionDigits: 0 });
}

export default async function WebstudioDashboard() {
  const overview = await getApiJson<Overview>("/webstudio/overview");
  const hasData = !!overview && overview.leads_total > 0;

  const stages = [
    { label: "Leads", value: overview?.leads_total },
    { label: "Ganhos (WON)", value: overview?.leads_won },
    { label: "Propostas", value: overview?.proposals_total },
    { label: "Aceites", value: overview?.proposals_accepted },
    { label: "Projetos ativos", value: overview?.projects_active },
    { label: "Concluídos", value: overview?.projects_completed },
  ];

  return (
    <main
      className="page"
      style={{ fontFamily: "var(--font-display), system-ui" }}
    >
      <p className="eyebrow">Livro de bordo · Webstudio</p>
      <h1 className="title">Funil de Vendas</h1>
      <p className="scopeNote">
        Receita e lucro aqui são PRÓPRIOS da Evolure Labs (agência a fechar
        projetos) - diferente da atividade agregada de terceiros que vês no
        Executive Dashboard do Contela.
      </p>

      {!hasData && (
        <p className="emptyState">
          Sem dados ainda — a estrutura já está ligada ao backend real da
          Webstudio, só à espera da primeira ingestão trazer
          leads/propostas/projetos.
        </p>
      )}

      {/* Funil: Lead -> Won -> Proposal -> Accepted -> Project -> Completed */}
      <div className="grid">
        {stages.map((stage) => (
          <div key={stage.label} className="metricCard">
            <div className="metricLabel">{stage.label}</div>
            <div className="metricFigure">{fmt(stage.value)}</div>
          </div>
        ))}
      </div>

      <p className="sectionLabel">Receita, despesas e lucro</p>
      <div className="grid">
        <div className="metricCard">
          <div className="metricLabel">Receita reconhecida</div>
          <div className="metricFigure">{fmt(overview?.revenue_total)} MZN</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Despesas</div>
          <div className="metricFigure">
            {fmt(overview?.expenses_total)} MZN
          </div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Lucro real</div>
          <div className="metricFigure">{fmt(overview?.profit_total)} MZN</div>
        </div>
        <div className="metricCard">
          <div className="metricLabel">Pipeline (propostas enviadas)</div>
          <div className="metricFigure">
            {fmt(overview?.pipeline_value)} MZN
          </div>
        </div>
      </div>
    </main>
  );
}
