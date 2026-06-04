"use client";

import React, { useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";
import { adminFetch, API_BASE, ADMIN_TOKEN_KEY, DEFAULT_ADMIN_TOKEN } from "../../../lib/apiClient";

const API = API_BASE;
const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

type Report = {
  project_id: string;
  generated_at?: string;
  period?: { label?: string; start_date?: string; end_date?: string };
  summary: Record<string, number>;
  executive_reading: string[];
  by_owner: { owner: string; count: number }[];
  by_severity: { severity: string; count: number }[];
  by_channel: { channel: string; count: number }[];
  by_alert_status: { alert_status: string; count: number }[];
  by_category: { category: string; count: number }[];
  recurrent_terms: { term: string; count: number }[];
  timeline: { date: string; count: number }[];
  critical_queue: any[];
};

function formatNumber(value: any) {
  if (value === undefined || value === null) return "0";
  return String(value);
}

function reportUrl(projectId: string, path: string, startDate?: string, endDate?: string) {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  const query = params.toString();
  return `${API}/notifications/reports/alerts/${projectId}${path}${query ? `?${query}` : ""}`;
}

export default function AlertsReportsPage() {
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);
  const [token, setToken] = useState(DEFAULT_ADMIN_TOKEN);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function load(customProjectId = projectId) {
    setLoading(true);
    setMessage("");
    try {
      const res = await adminFetch(reportUrl(customProjectId, "", startDate, endDate), {
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);
      const data = await res.json();
      setReport(data);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao carregar relatório gerencial.");
    } finally {
      setLoading(false);
    }
  }

  function openDownload(path: string) {
    window.open(reportUrl(projectId, path, startDate, endDate), "_blank");
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const p = params.get("project_id") || DEFAULT_PROJECT_ID;
    setProjectId(p);
    load(p);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const summary = report?.summary || {};
  const resolutionRate = Number(summary.resolution_rate || 0);
  const overdueRate = Number(summary.overdue_rate || 0);

  return (
    <AppShell
      title="Relatório Gerencial de Alertas e SLA"
      subtitle="Painel executivo de produtividade operacional, alertas vencidos, responsáveis, canais, erros e exportações PDF/PPTX/CSV."
    >
      <section style={heroStyle}>
        <div>
          <div style={eyebrowStyle}>ALERT OPS · TV FISCAL WEBMONITOR</div>
          <h2 style={{ margin: "8px 0 10px", fontSize: 32 }}>Gestão executiva dos alertas</h2>
          <p style={{ margin: 0, maxWidth: 900, lineHeight: 1.65 }}>
            Consolide a operação de alertas por período: volume tratado, pendências, SLA vencido, tempo médio de resposta, produtividade por responsável e canais de notificação.
          </p>
        </div>
        <div style={{ display: "grid", gap: 10, minWidth: 420 }}>
          <input value={projectId} onChange={(e) => setProjectId(e.target.value)} style={inputStyle} />
          <input value={token} onChange={(e) => setToken(e.target.value)} style={inputStyle} type="password" />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={inputStyle} />
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={inputStyle} />
          </div>
          <button style={primaryButtonStyle} onClick={() => load()}>{loading ? "Atualizando..." : "Atualizar relatório"}</button>
        </div>
      </section>

      {message ? <div style={messageStyle}>{message}</div> : null}

      <section style={kpiGridStyle}>
        <Kpi label="Alertas" value={summary.total || 0} hint="período" />
        <Kpi label="Ativos" value={summary.active || 0} hint="fila atual" />
        <Kpi label="Resolvidos" value={summary.resolved || 0} hint={`${resolutionRate}%`} />
        <Kpi label="Vencidos" value={summary.overdue || 0} hint={`${overdueRate}%`} danger />
        <Kpi label="Sem responsável" value={summary.unassigned || 0} hint="atribuir" danger={(summary.unassigned || 0) > 0} />
        <Kpi label="Erros" value={summary.errors || 0} hint="provedores" danger={(summary.errors || 0) > 0} />
      </section>

      <section style={panelStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <h3 style={{ margin: 0 }}>Exportações executivas</h3>
            <p style={{ margin: "6px 0 0", color: "#667085" }}>Gere o relatório gerencial nos formatos PDF, PPTX e CSV.</p>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button style={primaryButtonStyle} onClick={() => openDownload("/pdf")}>Gerar PDF</button>
            <button style={secondaryButtonStyle} onClick={() => openDownload("/pptx")}>Gerar PPTX</button>
            <button style={secondaryButtonStyle} onClick={() => openDownload("/export.csv")}>Exportar CSV</button>
          </div>
        </div>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "1.05fr .95fr", gap: 18, marginBottom: 18 }}>
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Leitura executiva</h3>
          {(report?.executive_reading || []).map((line, idx) => (
            <p key={idx} style={{ margin: "8px 0", color: "#344054", lineHeight: 1.55 }}>• {line}</p>
          ))}
          {!report?.executive_reading?.length ? <p style={{ color: "#667085" }}>Sem leitura executiva disponível.</p> : null}
        </div>
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Indicadores de tempo</h3>
          <div style={timeGridStyle}>
            <KpiMini label="T. médio ciência" value={`${formatNumber(summary.avg_ack_minutes)} min`} />
            <KpiMini label="T. médio resolução" value={`${formatNumber(summary.avg_resolution_minutes)} min`} />
            <KpiMini label="Escalados" value={summary.escalated || 0} />
            <KpiMini label="Vence breve" value={summary.due_soon || 0} />
          </div>
        </div>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 18, marginBottom: 18 }}>
        <Rank title="Por responsável" rows={report?.by_owner || []} labelKey="owner" />
        <Rank title="Por severidade" rows={report?.by_severity || []} labelKey="severity" />
        <Rank title="Por canal" rows={report?.by_channel || []} labelKey="channel" />
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 18, marginBottom: 18 }}>
        <Rank title="Por status" rows={report?.by_alert_status || []} labelKey="alert_status" />
        <Rank title="Por categoria" rows={report?.by_category || []} labelKey="category" />
        <Rank title="Reincidência de termos/temas" rows={report?.recurrent_terms || []} labelKey="term" />
      </section>

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>Fila crítica de SLA</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr><th>Data</th><th>SLA</th><th>Severidade</th><th>Responsável</th><th>Canal</th><th>Título</th></tr>
            </thead>
            <tbody>
              {(report?.critical_queue || []).slice(0, 20).map((row) => (
                <tr key={row.id}>
                  <td>{row.created_at_display || "—"}</td>
                  <td>{row.sla_status || "—"}</td>
                  <td>{row.severity || "—"}</td>
                  <td>{row.assigned_to || "Sem responsável"}</td>
                  <td>{row.channel || "—"}</td>
                  <td>{row.title || "Alerta TV Fiscal"}</td>
                </tr>
              ))}
              {!report?.critical_queue?.length ? <tr><td colSpan={6}>Nenhum alerta crítico no período.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}

function Kpi({ label, value, hint, danger }: { label: string; value: number | string; hint: string; danger?: boolean }) {
  return (
    <div style={kpiStyle}>
      <div style={{ color: danger ? "#b42318" : "#b00020", fontSize: 28, fontWeight: 900 }}>{value}</div>
      <div style={{ fontWeight: 800, color: "#0b1f3a" }}>{label}</div>
      <div style={{ color: "#667085", fontSize: 12 }}>{hint}</div>
    </div>
  );
}

function KpiMini({ label, value }: { label: string; value: number | string }) {
  return <div style={miniKpiStyle}><strong>{value}</strong><span>{label}</span></div>;
}

function Rank({ title, rows, labelKey }: { title: string; rows: any[]; labelKey: string }) {
  const max = useMemo(() => Math.max(1, ...rows.map((r) => Number(r.count || 0))), [rows]);
  return (
    <div style={panelStyle}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      {(rows || []).slice(0, 8).map((row) => {
        const count = Number(row.count || 0);
        return (
          <div key={`${title}-${row[labelKey]}`} style={{ marginBottom: 12 }}>
            <div style={rankRowStyle}><span>{row[labelKey] || "—"}</span><strong>{count}</strong></div>
            <div style={barBgStyle}><div style={{ ...barStyle, width: `${Math.max(4, (count / max) * 100)}%` }} /></div>
          </div>
        );
      })}
      {!rows?.length ? <p style={{ color: "#667085" }}>Sem dados.</p> : null}
    </div>
  );
}

const heroStyle: React.CSSProperties = { background: "linear-gradient(135deg,#0b1f3a,#172554)", color: "#fff", borderRadius: 18, padding: 24, marginBottom: 18, display: "flex", justifyContent: "space-between", gap: 20, alignItems: "center", boxShadow: "0 12px 28px rgba(11,31,58,.22)" };
const eyebrowStyle: React.CSSProperties = { color: "#ffccd5", fontWeight: 900, letterSpacing: 1.4, fontSize: 12 };
const inputStyle: React.CSSProperties = { border: "1px solid #d0d5dd", borderRadius: 10, padding: "11px 12px", minWidth: 180, background: "#fff" };
const primaryButtonStyle: React.CSSProperties = { border: "none", borderRadius: 10, padding: "12px 16px", background: "#b00020", color: "#fff", fontWeight: 900, cursor: "pointer" };
const secondaryButtonStyle: React.CSSProperties = { border: "1px solid #d0d5dd", borderRadius: 10, padding: "12px 16px", background: "#fff", color: "#344054", fontWeight: 900, cursor: "pointer" };
const messageStyle: React.CSSProperties = { background: "#fff7ed", border: "1px solid #fed7aa", color: "#9a3412", padding: 12, borderRadius: 12, marginBottom: 16 };
const kpiGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(6,minmax(0,1fr))", gap: 12, marginBottom: 18 };
const kpiStyle: React.CSSProperties = { background: "#fff", borderRadius: 16, padding: 16, boxShadow: "0 4px 14px rgba(15,23,42,.08)", border: "1px solid #eef2f6" };
const miniKpiStyle: React.CSSProperties = { background: "#f8fafc", border: "1px solid #eef2f6", borderRadius: 14, padding: 14, display: "grid", gap: 4, color: "#344054" };
const timeGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 };
const panelStyle: React.CSSProperties = { background: "#fff", borderRadius: 18, padding: 18, boxShadow: "0 4px 14px rgba(15,23,42,.08)", border: "1px solid #eef2f6", marginBottom: 18 };
const rankRowStyle: React.CSSProperties = { display: "flex", justifyContent: "space-between", gap: 10, color: "#344054", fontSize: 13 };
const barBgStyle: React.CSSProperties = { height: 6, borderRadius: 999, background: "#eef2f6", overflow: "hidden", marginTop: 6 };
const barStyle: React.CSSProperties = { height: "100%", borderRadius: 999, background: "#0b1f3a" };
const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: 13 };
