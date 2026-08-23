export const metadata = {
  title: "Evolure Intelligence",
  description: "Plataforma de Inteligência da Evolure Labs",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, padding: "2rem" }}>
        {children}
      </body>
    </html>
  );
}
