export const metadata = {
  title: "Evolure Intelligence",
  description: "Plataforma de Inteligência da Evolure Labs",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, padding: "2rem" }}>
        <nav style={{ maxWidth: 900, margin: "0 auto 1.5rem", display: "flex", gap: "1.5rem", fontSize: "0.85rem" }}>
          <a href="/" style={{ color: "#666", textDecoration: "none" }}>
            Estado do sistema
          </a>
          <a href="/executive" style={{ color: "#666", textDecoration: "none" }}>
            Executive Dashboard
          </a>
        </nav>
        {children}
      </body>
    </html>
  );
}
