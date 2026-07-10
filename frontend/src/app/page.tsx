"use client";

import React, { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import { adminFetch, API_BASE } from "../lib/apiClient";

const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

type Dashboard = {
  generated_at: string;
  project_filter?: string | null;
  project_name: string;
  period_days: number;
  summary: Record<string, number>;
  quality: Record<string, number>;
  providers: Record<string, number>;
  rankings: {
    advertisers: { name: string; count: number; investment: number }[];
    portals: { name: string; count: number; investment: number }[];
    editorial_sources: { source: string; count: number }[];
    topics: { topic: string; count: number }[];
    sentiments: { sentiment: string; count: number }[];
    alert_severity: { severity: string; count: number }[];
    alert_channel: { channel: string; count: number }[];
    alert_owner: { owner: string; count: number }[];
    projects: { project_id: string; project_name: string; items: number; banners: number; alerts: number; investment: number; score: number }[];
  };
  timeline: { date: string; editorial: number; banners: number; alerts: number }[];
  latest: {
    items: any[];
    banners: any[];
    alerts: any[];
    automation_runs: any[];
  };
  executive_reading: string[];
};

function money(value?: number) {
  return `R$ ${(value || 0).toLocaleString("pt-BR")}`;
}

function pct(value?: number) {
  return `${(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

function MetricCard({ label, value, hint, tone = "red" }: { label: string; value: string | number; hint: string; tone?: "red" | "blue" | "green" | "orange" | "purple" | "dark" }) {
  const color = toneColor[tone] || toneColor.red;
  return (
    <div style={{ ...metricCardStyle, borderTop: `4px solid ${color}` }}>
      <div style={metricLabelStyle}>{label}</div>
      <div style={{ ...metricValueStyle, color }}>{value}</div>
      <div style={metricHintStyle}>{hint}</div>
    </div>
  );
}

function ProgressList({ title, subtitle, items, valueKey = "count", labelKey = "name", moneyKey }: { title: string; subtitle?: string; items: any[]; valueKey?: string; labelKey?: string; moneyKey?: string }) {
  const max = Math.max(1, ...items.map((i) => Number(i[valueKey] || 0)));
  return (
    <section style={panelStyle}>
      <h2 style={panelTitleStyle}>{title}</h2>
      {subtitle ? <p style={panelSubtitleStyle}>{subtitle}</p> : null}
      <div style={{ display: "grid", gap: 13, marginTop: 18 }}>
        {items.length === 0 ? <p style={emptyStyle}>Sem dados para exibir.</p> : items.map((item, index) => {
          const value = Number(item[valueKey] || 0);
          const width = Math.max(4, Math.round((value / max) * 100));
          return (
            <div key={`${title}-${index}`}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, fontSize: 13, marginBottom: 6 }}>
                <strong style={{ color: "#182235", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item[labelKey]}</strong>
                <span style={{ color: "#5b6472", whiteSpace: "nowrap" }}>{value.toLocaleString("pt-BR")}{moneyKey ? ` · ${money(item[moneyKey])}` : ""}</span>
              </div>
              <div style={barTrackStyle}>
                <div style={{ ...barFillStyle, width: `${width}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Timeline({ data }: { data: Dashboard["timeline"] }) {
  const max = Math.max(1, ...data.map((d) => d.editorial + d.banners + d.alerts));
  return (
    <section style={panelStyle}>
      <h2 style={panelTitleStyle}>Linha do tempo operacional</h2>
      <p style={panelSubtitleStyle}>Volume recente de notícias, evidências e alertas.</p>
      <div style={{ display: "flex", gap: 8, alignItems: "end", minHeight: 150, marginTop: 24 }}>
        {data.map((d, idx) => {
          const total = d.editorial + d.banners + d.alerts;
          const height = Math.max(8, Math.round((total / max) * 118));
          return (
            <div key={idx} style={{ flex: 1, minWidth: 0, textAlign: "center" }} title={`${d.date}: ${total}`}>
              <div style={{ height: 126, display: "flex", alignItems: "end", justifyContent: "center" }}>
                <div style={{ width: "70%", height, borderRadius: "9px 9px 4px 4px", background: "linear-gradient(180deg,#d62b44,#801126)", boxShadow: "0 8px 18px rgba(176,0,32,0.18)" }} />
              </div>
              <div style={{ fontSize: 10, color: "#697386", marginTop: 8, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{d.date.slice(0, 5)}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function HealthPill({ label, value, status }: { label: string; value: string | number; status: "ok" | "warn" | "danger" | "neutral" }) {
  const color = status === "ok" ? "#138a44" : status === "warn" ? "#b7791f" : status === "danger" ? "#b00020" : "#4b5563";
  const bg = status === "ok" ? "#eaf7ee" : status === "warn" ? "#fff7e6" : status === "danger" ? "#fff1f2" : "#eef2f7";
  return (
    <div style={{ background: bg, color, border: `1px solid ${color}22`, padding: "12px 14px", borderRadius: 14 }}>
      <strong style={{ display: "block", fontSize: 20, lineHeight: 1 }}>{value}</strong>
      <span style={{ fontSize: 12 }}>{label}</span>
    </div>
  );
}

function ActionButton({ href, label, color = "#b00020" }: { href: string; label: string; color?: string }) {
  return (
    <a href={href} style={{ background: color, color: "#fff", padding: "11px 15px", borderRadius: 11, fontWeight: 800, textDecoration: "none", boxShadow: "0 8px 16px rgba(0,0,0,0.12)", display: "inline-block", fontSize: 13 }}>
      {label}
    </a>
  );
}

function ListPanel({ title, subtitle, items, render }: { title: string; subtitle?: string; items: any[]; render: (item: any, index: number) => React.ReactNode }) {
  return (
    <section style={panelStyle}>
      <h2 style={panelTitleStyle}>{title}</h2>
      {subtitle ? <p style={panelSubtitleStyle}>{subtitle}</p> : null}
      <div style={{ display: "grid", gap: 12, marginTop: 18 }}>
        {items.length === 0 ? <p style={emptyStyle}>Sem dados para exibir.</p> : items.map(render)}
      </div>
    </section>
  );
}

function MiniCard({ children }: { children: React.ReactNode }) {
  return <div style={miniCardStyle}>{children}</div>;
}

export default function ExecutiveDashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      try {
        setLoading(true);
        setLoadError(null);

        const API = API_BASE;

        const token =
          typeof window !== "undefined"
            ? localStorage.getItem("tvfiscal_auth_token")
            : null;

        const headers: Record<string, string> = {
        };

        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }

        const response = await adminFetch(
          `${API}/executive/dashboard?project_id=${encodeURIComponent(DEFAULT_PROJECT_ID)}&days=30`,
          {
            cache: "no-store",
            headers,
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const payload = (await response.json()) as Dashboard;

        if (!cancelled) {
          setData(payload);
        }
      } catch (error) {
        if (!cancelled) {
          const message = error instanceof Error ? error.message : "Erro desconhecido";
          setLoadError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <AppShell title="Dashboard Executivo Geral" subtitle="Visão consolidada da TV Fiscal WebMonitor">
        <div style={loadingBoxStyle}>Carregando dashboard executivo geral...</div>
      </AppShell>
    );
  }

  if (loadError || !data) {
    return (
      <AppShell title="Dashboard Executivo Geral" subtitle="Visão consolidada da TV Fiscal WebMonitor">
        <div style={errorBoxStyle}>
          Erro ao carregar o dashboard executivo geral. O backend respondeu corretamente nos testes diretos. Esta tela usa o cliente centralizado de API.
          {loadError ? <div style={{ marginTop: 8 }}>Detalhe técnico: {loadError}</div> : null}
        </div>
      </AppShell>
    );
  }

  const s = data.summary || {};
  const q = data.quality || {};
  const pendingStatus = s.pending_identification > 0 ? "warn" : "ok";
  const slaStatus = s.alerts_overdue > 0 ? "danger" : s.alerts_due_soon > 0 ? "warn" : "ok";
  const providerStatus = s.alerts_errors > 0 ? "danger" : "ok";

  return (
    <AppShell title="Dashboard Executivo Geral" subtitle="Visão única da operação: projetos, coletas, publicidade, editorial, alertas, SLA e relatórios.">
      <section style={heroStyle}>
        <div>
          <div style={heroKickerStyle}>EXECUTIVE COMMAND CENTER · TV FISCAL WEBMONITOR</div>
          <h2 style={heroTitleStyle}>Central executiva da plataforma</h2>
          <p style={heroTextStyle}>
            Consolide a operação de checking publicitário, inteligência de mercado, clipping editorial, alertas, notificações e SLA em um único painel de gestão.
          </p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 18 }}>
            <ActionButton href="/projects" label="Projetos" />
            <ActionButton href="/intel" label="Intel Mercado" color="#1f4e79" />
            <ActionButton href="/editorial" label="Editorial" color="#0f766e" />
            <ActionButton href="/social" label="Social Monitor" color="#9333ea" />
            <ActionButton href="/alerts/inbox" label="Caixa de Alertas" color="#7c2d12" />
            <ActionButton href="/alerts/sla" label="SLA" color="#6d28d9" />
          </div>
        </div>
        <div style={heroRightStyle}>
          <div style={heroStampStyle}>Atualizado em<br /><strong>{data.generated_at}</strong></div>
          <div style={heroStampStyle}>Período<br /><strong>{data.period_days} dias</strong></div>
        </div>
      </section>

      <section style={healthGridStyle}>
        <HealthPill label="Saúde operacional" value={slaStatus === "danger" ? "Atenção" : "OK"} status={slaStatus} />
        <HealthPill label="Pendentes de identificação" value={s.pending_identification || 0} status={pendingStatus} />
        <HealthPill label="SLA vencido" value={s.alerts_overdue || 0} status={slaStatus} />
        <HealthPill label="Erros de notificação" value={s.alerts_errors || 0} status={providerStatus} />
        <HealthPill label="SMTP/Provedores ativos" value={(data.providers.email || 0) + (data.providers.sms || 0) + (data.providers.whatsapp || 0)} status="neutral" />
      </section>

      <section style={metricsGridStyle}>
        <MetricCard label="Projetos ativos" value={s.projects_active || 0} hint={`${s.projects_total || 0} projeto(s) cadastrados`} tone="red" />
        <MetricCard label="Matérias monitoradas" value={s.editorial_items || 0} hint={`${s.editorial_recent || 0} no recorte recente`} tone="green" />
        <MetricCard label="Itens de mercado" value={s.market_items || 0} hint={`${s.banner_items || 0} itens visuais totais`} tone="blue" />
        <MetricCard label="Investimento estimado" value={money(s.investment_total)} hint="Base de inteligência de mercado" tone="dark" />
        <MetricCard label="Publicidade auditável" value={s.auditables || 0} hint={`${pct(q.auditable_rate)} dos itens visuais`} tone="purple" />
        <MetricCard label="Evidências preservadas" value={s.preserved_evidence || 0} hint={`${pct(q.preserved_rate)} de preservação`} tone="green" />
        <MetricCard label="Alertas ativos" value={s.alerts_active || 0} hint={`${s.alerts_sent || 0} envio(s) real(is)`} tone="orange" />
        <MetricCard label="Taxa de identificação" value={pct(q.identification_rate)} hint={`${s.pending_identification || 0} pendente(s)`} tone="red" />
      </section>

      <section style={panelStyle}>
        <h2 style={panelTitleStyle}>Leitura executiva automática</h2>
        <p style={panelSubtitleStyle}>Síntese operacional para diretoria, coordenação de mídia e equipe de monitoramento.</p>
        <div style={{ display: "grid", gap: 10, marginTop: 16 }}>
          {data.executive_reading.map((line, idx) => (
            <div key={idx} style={insightStyle}>• {line}</div>
          ))}
        </div>
      </section>

      <section style={threeColGridStyle}>
        <ProgressList title="Top anunciantes identificados" subtitle="Ranking limpo, sem pendentes de identificação." items={data.rankings.advertisers || []} valueKey="count" labelKey="name" moneyKey="investment" />
        <ProgressList title="Top portais publicitários" subtitle="Presença e investimento estimado por publisher." items={data.rankings.portals || []} valueKey="count" labelKey="name" moneyKey="investment" />
        <ProgressList title="Temas editoriais" subtitle="Assuntos mais recorrentes no clipping." items={data.rankings.topics || []} valueKey="count" labelKey="topic" />
      </section>

      <section style={twoColGridStyle}>
        <Timeline data={data.timeline || []} />
        <section style={panelStyle}>
          <h2 style={panelTitleStyle}>Qualidade da operação</h2>
          <p style={panelSubtitleStyle}>Indicadores de controle para priorização diária.</p>
          <div style={{ display: "grid", gap: 14, marginTop: 18 }}>
            <QualityLine label="Identificação comercial" value={q.identification_rate || 0} />
            <QualityLine label="Evidência auditável" value={q.auditable_rate || 0} />
            <QualityLine label="Prova preservada" value={q.preserved_rate || 0} />
            <QualityLine label="SLA dentro do prazo" value={100 - (q.sla_overdue_rate || 0)} />
            <QualityLine label="Notificações sem erro" value={100 - (q.notification_error_rate || 0)} />
          </div>
        </section>
      </section>

      <section style={threeColGridStyle}>
        <ProgressList title="Fontes editoriais" items={data.rankings.editorial_sources || []} valueKey="count" labelKey="source" />
        <ProgressList title="Alertas por severidade" items={data.rankings.alert_severity || []} valueKey="count" labelKey="severity" />
        <ProgressList title="Responsáveis por alertas" items={data.rankings.alert_owner || []} valueKey="count" labelKey="owner" />
      </section>

      <section style={twoColGridStyle}>
        <ListPanel title="Projetos com maior atividade" subtitle="Combina notícias, evidências e alertas." items={data.rankings.projects || []} render={(item, index) => (
          <MiniCard key={index}>
            <strong style={{ color: "#182235" }}>{index + 1}. {item.project_name}</strong>
            <div style={miniMetaStyle}>Matérias: {item.items} · Mercado: {item.banners} · Alertas: {item.alerts} · Invest.: {money(item.investment)}</div>
          </MiniCard>
        )} />

        <ListPanel title="Alertas críticos em aberto" subtitle="Prioridade operacional por severidade e SLA." items={data.latest.alerts || []} render={(item, index) => (
          <MiniCard key={index}>
            <strong style={{ color: item.severity === "critico" || item.severity === "crítico" ? "#b00020" : "#182235" }}>{item.title || "Alerta sem título"}</strong>
            <div style={miniMetaStyle}>Severidade: {item.severity || "informativo"} · Canal: {item.channel || "painel"} · Status: {item.alert_status || "aberto"}</div>
            <div style={miniMetaStyle}>Responsável: {item.assigned_to || "Sem responsável"} · SLA: {item.sla_due_at || "—"}</div>
          </MiniCard>
        )} />
      </section>

      <section style={twoColGridStyle}>
        <ListPanel title="Últimas matérias" subtitle="Clipping editorial recente." items={data.latest.items || []} render={(item, index) => (
          <MiniCard key={index}>
            <strong style={{ color: "#0f766e" }}>{item.title}</strong>
            <div style={miniMetaStyle}>{item.source_name || "Sem fonte"} · Tema: {item.topic || "—"} · Tom: {item.sentiment || "—"}</div>
            {item.url ? <a href={item.url} target="_blank" style={linkStyle}>Abrir matéria</a> : null}
          </MiniCard>
        )} />

        <ListPanel title="Últimas evidências visuais" subtitle="Publicidade, mercado e candidatos editoriais." items={data.latest.banners || []} render={(item, index) => (
          <MiniCard key={index}>
            <strong style={{ color: "#1f4e79" }}>{item.advertiser_name}</strong>
            <div style={miniMetaStyle}>{item.source_name || "Sem portal"} · {item.format} · {money(item.estimated_value)}</div>
            <div style={miniMetaStyle}>Checking: {item.checking_status || "—"} · Mercado: {item.market_status || "—"}</div>
          </MiniCard>
        )} />
      </section>
    </AppShell>
  );
}

function QualityLine({ label, value }: { label: string; value: number }) {
  const safe = Math.max(0, Math.min(100, value || 0));
  const color = safe >= 80 ? "#138a44" : safe >= 50 ? "#b7791f" : "#b00020";
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 13 }}>
        <strong>{label}</strong>
        <span>{pct(safe)}</span>
      </div>
      <div style={barTrackStyle}><div style={{ ...barFillStyle, width: `${safe}%`, background: color }} /></div>
    </div>
  );
}

const toneColor = {
  red: "#b00020",
  blue: "#1f4e79",
  green: "#0f766e",
  orange: "#c05621",
  purple: "#6d28d9",
  dark: "#182235",
};

const heroStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1.3fr 0.7fr",
  gap: 22,
  padding: 28,
  borderRadius: 24,
  color: "#fff",
  background: "radial-gradient(circle at top right, rgba(255,255,255,0.18), transparent 32%), linear-gradient(135deg,#081426 0%,#122844 48%,#b00020 100%)",
  boxShadow: "0 18px 40px rgba(8,20,38,0.22)",
  marginBottom: 24,
};

const heroKickerStyle: React.CSSProperties = { fontSize: 12, letterSpacing: 1.4, fontWeight: 900, opacity: 0.86, textTransform: "uppercase" };
const heroTitleStyle: React.CSSProperties = { margin: "8px 0 0", fontSize: 34, lineHeight: 1.1, fontWeight: 900 };
const heroTextStyle: React.CSSProperties = { margin: "12px 0 0", maxWidth: 760, lineHeight: 1.65, opacity: 0.92 };
const heroRightStyle: React.CSSProperties = { display: "grid", gap: 12, alignContent: "center" };
const heroStampStyle: React.CSSProperties = { background: "rgba(255,255,255,0.13)", border: "1px solid rgba(255,255,255,0.2)", borderRadius: 18, padding: 16, lineHeight: 1.5 };

const healthGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 14, marginBottom: 20 };
const metricsGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 18, marginBottom: 22 };
const twoColGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 22, marginTop: 22 };
const threeColGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 22, marginTop: 22 };

const panelStyle: React.CSSProperties = { background: "#fff", borderRadius: 20, padding: 22, boxShadow: "0 8px 22px rgba(8,20,38,0.08)", border: "1px solid #e7ecf3" };
const panelTitleStyle: React.CSSProperties = { margin: 0, color: "#182235", fontSize: 20, fontWeight: 900 };
const panelSubtitleStyle: React.CSSProperties = { margin: "7px 0 0", color: "#687386", fontSize: 13.5, lineHeight: 1.5 };
const metricCardStyle: React.CSSProperties = { background: "#fff", borderRadius: 18, padding: 20, boxShadow: "0 8px 22px rgba(8,20,38,0.08)", border: "1px solid #e7ecf3" };
const metricLabelStyle: React.CSSProperties = { color: "#687386", fontSize: 12, fontWeight: 900, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 10 };
const metricValueStyle: React.CSSProperties = { fontSize: 30, fontWeight: 950, lineHeight: 1 };
const metricHintStyle: React.CSSProperties = { color: "#697386", fontSize: 13, marginTop: 9, lineHeight: 1.35 };
const barTrackStyle: React.CSSProperties = { height: 9, borderRadius: 999, background: "#e9eef5", overflow: "hidden" };
const barFillStyle: React.CSSProperties = { height: "100%", borderRadius: 999, background: "linear-gradient(90deg,#b00020,#e3485e)" };
const insightStyle: React.CSSProperties = { background: "#f8fafc", border: "1px solid #e7ecf3", borderLeft: "4px solid #b00020", padding: "12px 14px", borderRadius: 12, color: "#253044", lineHeight: 1.5 };
const miniCardStyle: React.CSSProperties = { border: "1px solid #e7ecf3", background: "#fbfcfe", borderRadius: 14, padding: 14, display: "grid", gap: 6 };
const miniMetaStyle: React.CSSProperties = { color: "#687386", fontSize: 13, lineHeight: 1.45 };
const emptyStyle: React.CSSProperties = { color: "#687386", margin: 0 };
const linkStyle: React.CSSProperties = { color: "#1f4e79", textDecoration: "none", fontWeight: 800, fontSize: 13 };
const errorBoxStyle: React.CSSProperties = { background: "#fff4f4", border: "1px solid #f1c2c2", color: "#8a1f1f", padding: 18, borderRadius: 12 };
const loadingBoxStyle: React.CSSProperties = { background: "#fff", border: "1px solid #e7ecf3", color: "#344054", padding: 18, borderRadius: 12, boxShadow: "0 8px 22px rgba(8,20,38,0.08)" };
