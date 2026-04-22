type AppShellProps = {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
};

const menuItems = [
  { label: "Painel executivo", href: "/" },
  { label: "Matérias monitoradas", href: "/items" },
  { label: "Banners capturados", href: "/banners" },
  { label: "API / Swagger", href: "http://localhost:8000/docs", external: true },
];

export default function AppShell({ title, subtitle, children }: AppShellProps) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "280px 1fr",
        minHeight: "100vh",
        background: "#f4f6fa",
      }}
    >
      <aside
        style={{
          background: "linear-gradient(180deg,#5c0011 0%,#7a0015 40%,#b00020 100%)",
          color: "#fff",
          padding: 24,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        <div>
          {/* LOGO */}
          <div
            style={{
              background: "#fff",
              borderRadius: 14,
              padding: 16,
              marginBottom: 24,
              textAlign: "center",
            }}
          >
            <img
              src="/logo-tv-fiscal.png"
              alt="TV Fiscal"
              style={{
                width: "100%",
                maxWidth: 180,
                height: "auto",
              }}
            />
          </div>

          {/* DESCRIÇÃO */}
          <div
            style={{
              fontSize: 13,
              lineHeight: 1.6,
              opacity: 0.9,
              marginBottom: 26,
            }}
          >
            Plataforma executiva de monitoramento editorial,
            clipping eletrônico e auditoria de publicidade digital.
          </div>

          {/* MENU */}
          <nav style={{ display: "grid", gap: 10 }}>
            {menuItems.map((item) => (
              <a
                key={item.label}
                href={item.href}
                target={item.external ? "_blank" : undefined}
                style={navLinkStyle}
              >
                {item.label}
              </a>
            ))}
          </nav>
          <a href="/intel" style={navLinkStyle}>
          Inteligência de Anunciantes
          </a>
          {/* STATUS */}
          <div
            style={{
              marginTop: 28,
              background: "rgba(255,255,255,0.1)",
              padding: 12,
              borderRadius: 10,
              fontSize: 12,
            }}
          >
            <strong>Status do sistema</strong>
            <br />
            Backend FastAPI ativo
            <br />
            Monitoramento em execução
          </div>
        </div>

        {/* RODAPÉ */}
        <div
          style={{
            fontSize: 12,
            opacity: 0.85,
            borderTop: "1px solid rgba(255,255,255,0.2)",
            paddingTop: 16,
          }}
        >
          TV Fiscal WebMonitor
          <br />
          O monitor ideal da sua mídia
        </div>
      </aside>

      {/* CONTEÚDO */}
      <main style={{ padding: 28 }}>
        <header
          style={{
            background: "#fff",
            borderRadius: 16,
            padding: 22,
            boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
            marginBottom: 24,
          }}
        >
          <h1 style={{ margin: 0, color: "#b00020" }}>{title}</h1>

          {subtitle && (
            <p
              style={{
                marginTop: 8,
                color: "#666",
                fontSize: 15,
              }}
            >
              {subtitle}
            </p>
          )}
        </header>

        {children}
      </main>
    </div>
  );
}

const navLinkStyle: React.CSSProperties = {
  color: "#fff",
  textDecoration: "none",
  padding: "12px 14px",
  borderRadius: 10,
  fontWeight: "bold",
  background: "rgba(255,255,255,0.12)",
};