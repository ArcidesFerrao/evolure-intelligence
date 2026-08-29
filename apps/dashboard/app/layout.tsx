import { IBM_Plex_Mono, Space_Grotesk } from "next/font/google";
import "./global.css";
import Navigator from "../components/Navigator";

export const metadata = {
  title: "Evolure Intelligence",
  description: "Plataforma de Inteligência da Evolure Labs",
};

const display = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "600"],
  variable: "--font-display",
});
const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
});
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt" className={`${display.variable} ${mono.variable}`}>
      <body className="m-0">
        <Navigator />
        {children}
      </body>
    </html>
  );
}
