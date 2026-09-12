import React from "react";

export default function Navigator() {
  return (
    <nav className="navigator page my-4 flex gap-4 text-md">
      <a href="/morning-brief" style={{ color: "#666", textDecoration: "none" }}>
        Morning Brief
      </a>
      <a href="/overview" style={{ color: "#666", textDecoration: "none" }}>
        Visão Geral
      </a>
      <a href="/" style={{ color: "#666", textDecoration: "none" }}>
        Estado do sistema
      </a>
      <a href="/executive" style={{ color: "#666", textDecoration: "none" }}>
        Executive Dashboard
      </a>
      <a href="/webstudio" style={{ color: "#666", textDecoration: "none" }}>
        Webstudio
      </a>
    </nav>
  );
}
