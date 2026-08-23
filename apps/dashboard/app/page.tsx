async function getApiHealth() {
  const apiUrl = process.env.API_INTERNAL_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${apiUrl}/health`, { cache: "no-store" });
    return await res.json();
  } catch (err) {
    return { status: "unreachable", database: "unknown" };
  }
}

export default async function Home() {
  const health = await getApiHealth();

  return (
    <main>
      <h1>Evolure Intelligence</h1>
      <p>Fase 1 - Foundation</p>
      <ul>
        <li>API: {health.status}</li>
        <li>Base de dados: {health.database}</li>
      </ul>
      <p style={{ color: "#666", fontSize: "0.9rem" }}>
        Se ambos os itens acima disserem &quot;ok&quot; / &quot;connected&quot;,
        a Fase 1 está pronta: dashboard, API e PostgreSQL estão a comunicar.
      </p>
    </main>
  );
}
