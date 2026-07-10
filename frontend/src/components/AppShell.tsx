"use client";

import React, { useEffect, useMemo, useState } from "react";
import { AuthUser, clearAuthSession, getAuthToken, getAuthUser, installAuthFetchInterceptor } from "../lib/auth";

type AppShellProps = {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
};

type MenuItem = { label: string; href: string; module: string; external?: boolean; admin?: boolean };

const menuItems: MenuItem[] = [
  { label: "Dashboard Executivo", href: "/", module: "dashboard" },
  { label: "Projetos monitorados", href: "/projects", module: "projects", admin: true },
  { label: "Matérias monitoradas", href: "/items", module: "editorial" },
  { label: "Monitoramento editorial", href: "/editorial", module: "editorial" },
  { label: "Histórico de Relatórios V3", href: "/reports-history", module: "editorial" },
  { label: "Banners capturados", href: "/banners", module: "banners" },
  { label: "Evidências operacionais", href: "/evidencias", module: "evidences" },
  { label: "Inteligência de Mercado", href: "/intel", module: "intel" },
  { label: "Intel Comparativo", href: "/intel/comparativo", module: "compare" },
  { label: "Área Admin · Scheduler", href: "/admin/scheduler", module: "scheduler", admin: true },
  { label: "Cadastros operacionais", href: "/admin/cadastros", module: "projects", admin: true },
  { label: "Usuários e Perfis", href: "/admin/users", module: "users", admin: true },
  { label: "Manutenção e Backup", href: "/admin/maintenance", module: "health", admin: true },
  { label: "Saúde do Sistema", href: "/admin/system-health", module: "health", admin: true },
  { label: "Central de Alertas", href: "/alerts", module: "alerts" },
  { label: "Caixa de Alertas", href: "/alerts/inbox", module: "inbox" },
  { label: "SLA e Escalonamento", href: "/alerts/sla", module: "sla" },
  { label: "Relatório de Alertas", href: "/alerts/reports", module: "reports" },
  { label: "Motor de Notificações", href: "/admin/notifications", module: "notifications", admin: true },
  { label: "Qualificação de marcas", href: "/admin/identificacao", module: "intel", admin: true },
  { label: "API / Swagger", href: "http://localhost:8000/docs", module: "health", external: true, admin: true },
];

function canAccess(user: AuthUser | null, module: string) {
  if (!user) return false;
  if (user.role === "admin") return true;
  const modules = user.allowed_modules || [];
  return modules.includes("*") || modules.includes(module);
}

export default function AppShell({ title, subtitle, children }: AppShellProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = getAuthToken();
    const current = getAuthUser();
    if (!token || !current) {
      window.location.href = "/login";
      return;
    }
    installAuthFetchInterceptor();
    setUser(current);
    setReady(true);
  }, []);

  const visibleMenu = useMemo(() => menuItems.filter((item) => canAccess(user, item.module)), [user]);

  function logout() {
    clearAuthSession();
    window.location.href = "/login";
  }

  if (!ready) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#f4f6fa", color: "#667085" }}>
        Carregando sessão...
      </div>
    );
  }

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
          background:
            "linear-gradient(180deg,#5c0011 0%,#7a0015 40%,#b00020 100%)",
          color: "#fff",
          padding: 24,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          boxSizing: "border-box",
        }}
      >
        <div>
          <div
            style={{
              width: "100%",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              padding: "10px 0 22px",
              boxSizing: "border-box",
              marginBottom: 8,
              borderBottom: "1px solid rgba(255,255,255,0.16)",
            }}
          >
            <div
              style={{
                background: "#fff",
                borderRadius: 14,
                padding: 12,
                width: 220,
                minHeight: 96,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 12px rgba(0,0,0,0.18)",
              }}
            >
              <img
                src="/logo-tv-fiscal-clean.png"
                alt="TV Fiscal"
                style={{ maxWidth: "100%", maxHeight: 80, height: "auto", objectFit: "contain", display: "block" }}
              />
            </div>
          </div>

          <div style={{ fontSize: 13, lineHeight: 1.6, opacity: 0.9, marginBottom: 18 }}>
            Plataforma executiva de monitoramento editorial, clipping eletrônico
            e auditoria de publicidade digital.
          </div>

          <div style={{ background: "rgba(255,255,255,0.12)", border: "1px solid rgba(255,255,255,0.22)", padding: 12, borderRadius: 12, marginBottom: 18, fontSize: 12, lineHeight: 1.5 }}>
            <strong>{user?.name}</strong><br />
            {user?.role_label || user?.role}<br />
            <span style={{ opacity: 0.85 }}>{user?.email}</span>
            <button onClick={logout} style={{ marginTop: 10, width: "100%", border: "1px solid rgba(255,255,255,0.35)", background: "rgba(0,0,0,0.18)", color: "#fff", borderRadius: 10, padding: "8px 10px", cursor: "pointer", fontWeight: 800 }}>
              Sair
            </button>
          </div>

          <nav style={{ display: "grid", gap: 10 }}>
            {visibleMenu.map((item) => (
              <a
                key={item.label}
                href={item.href}
                target={item.external ? "_blank" : undefined}
                rel={item.external ? "noreferrer" : undefined}
                style={{
                  ...navLinkStyle,
                  background: item.admin ? "rgba(0,0,0,0.28)" : "rgba(255,255,255,0.12)",
                  border: item.admin ? "1px solid rgba(255,255,255,0.35)" : "none",
                }}
              >
                {item.label}
              </a>
            ))}
          </nav>

          <div style={{ marginTop: 28, background: "rgba(255,255,255,0.1)", padding: 12, borderRadius: 10, fontSize: 12 }}>
            <strong>Status do sistema</strong>
            <br />
            Backend FastAPI ativo
            <br />
            Monitoramento em execução
          </div>
        </div>

        <div style={{ fontSize: 12, opacity: 0.85, borderTop: "1px solid rgba(255,255,255,0.2)", paddingTop: 16 }}>
          TV Fiscal WebMonitor
          <br />
          O monitor ideal da sua mídia
        </div>
      </aside>

      <main style={{ padding: 28 }}>
        <header style={{ background: "#fff", borderRadius: 16, padding: 22, boxShadow: "0 4px 14px rgba(0,0,0,0.08)", marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start" }}>
            <div>
              <h1 style={{ margin: 0, color: "#b00020" }}>{title}</h1>
              {subtitle && <p style={{ marginTop: 8, color: "#666", fontSize: 15 }}>{subtitle}</p>}
            </div>
            <div style={{ padding: "7px 10px", borderRadius: 999, background: "#F2F4F7", color: "#344054", fontSize: 12, fontWeight: 800 }}>
              Perfil: {user?.role_label || user?.role}
            </div>
          </div>
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
