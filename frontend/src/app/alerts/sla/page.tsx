"use client";

import React, { useEffect, useState } from "react";
import AppShell from "../../../components/AppShell";

const API = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";
const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";
const DEFAULT_TOKEN = "tvfiscal-admin-2026";

type SlaItem = {
  id: string;
  title?: string;
  message?: string;
  severity?: string;
  channel?: string;
  status?: string;
  alert_status?: string;
  assigned_to?: string;
  created_at_display?: string;
  sla_due_at_display?: string;
  sla_status?: string;
  sla_remaining_minutes?: number;
  escalation_count?: number;
  escalation_level?: number;
  escalated_at_display?: string;
  target_url?: string;
};

type Payload = {
  project_id: string;
  summary: Record<string, number>;
  by_owner: { owner: string; count: number }[];
  by_severity: { severity: string; count: number }[];
  items: SlaItem[];
};

function slaLabel(value?: string) {
  const map: Record<string, string> = {
    vencido: "Vencido",
    vence_em_breve: "Vence em breve",
    no_prazo: "No prazo",
    resolvido: "Resolvido",
    adiado: "Adiado",
    sem_sla: "Sem SLA",
  };
  return map[value || ""] || value || "—";
}

function severityColor(sev?: string) {
  const s = (sev || "informativo").toLowerCase();
  if (s === "critico") return { background: "#7f1d1d", color: "#fff" };
  if (s === "alto") return { background: "#fee2e2", color: "#991b1b" };
  if (s === "medio") return { background: "#fff7ed", color: "#9a3412" };
  return { background: "#eef2ff", color: "#3730a3" };
}

function slaColor(status?: string) {
  if (status === "vencido") return { background: "#7f1d1d", color: "#fff" };
  if (status === "vence_em_breve") return { background: "#fef3c7", color: "#92400e" };
  if (status === "no_prazo") return { background: "#dcfce7", color: "#166534" };
  if (status === "adiado") return { background: "#e0e7ff", color: "#3730a3" };
  return { background: "#f2f4f7", color: "#344054" };
}

export default function SlaPage() {
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);
  const [token, setToken] = useState(DEFAULT_TOKEN);
  const [payload, setPayload] = useState<Payload | null>(null);
  const [message, setMessage] = useState("");
  const [actor, setActor] = useState("TV Fiscal");
  const [assignee, setAssignee] = useState("TV Fiscal");
  const [loading, setLoading] = useState(false);

  async function api(path: string, options: RequestInit = {}) {
    const headers: Record<string, string> = { "Content-Type": "application/json", "X-Admin-Token": token };
    const res = await fetch(`${API}${path}`, { ...options, headers: { ...headers, ...(options.headers || {}) }, cache: "no-store" });
    if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);
    return res.json();
  }

  async function load(customProjectId = projectId) {
    setLoading(true);
    setMessage("");
    try {
      const data = await api(`/notifications/sla/${customProjectId}?limit=250`);
      setPayload(data);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao carregar SLA.");
    } finally {
      setLoading(false);
    }
  }

  async function evaluate() {
    setMessage("");
    try {
      const result = await api(`/notifications/sla/evaluate/${projectId}`, {
        method: "POST",
        body: JSON.stringify({ send_email: true, dry_run: false, note: "Escalonamento manual pela tela SLA." }),
      });
      setMessage(result.message || "SLA avaliado.");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao avaliar SLA.");
    }
  }

  async function assign(id: string) {
    try {
      const result = await api(`/notifications/logs/${id}/assign`, {
        method: "POST",
        body: JSON.stringify({ assigned_to: assignee, actor, note: "Atribuído pela tela SLA." }),
      });
      setMessage(result.message || "Alerta atribuído.");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao atribuir alerta.");
    }
  }

  async function ack(id: string) {
    await api(`/notifications/logs/${id}/ack`, { method: "POST", body: JSON.stringify({ actor }) });
    await load();
  }

  async function resolve(id: string) {
    await api(`/notifications/logs/${id}/resolve`, { method: "POST", body: JSON.stringify({ actor, note: "Resolvido pela tela SLA." }) });
    await load();
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const p = params.get("project_id") || DEFAULT_PROJECT_ID;
    setProjectId(p);
    load(p);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AppShell
      title="SLA e Escalonamento"
      subtitle="Controle de prazo, responsável, alertas vencidos e escalonamento operacional da Caixa de Alertas."
    >
      <section style={heroStyle}>
        <div>
          <div style={eyebrowStyle}>SLA CENTER · TV FISCAL WEBMONITOR</div>
          <h2 style={{ margin: "8px 0 10px", fontSize: 32 }}>Prazos e escalonamento de alertas</h2>
          <p style={{ margin: 0, maxWidth: 880, lineHeight: 1.65 }}>
            Acompanhe alertas críticos, vencidos, sem responsável e próximos do vencimento. Quando um SLA vencer, o sistema pode escalar por e-mail real para os contatos prioritários do projeto.
          </p>
        </div>
        <div style={{ display: "grid", gap: 10, minWidth: 390 }}>
          <input value={projectId} onChange={(e) => setProjectId(e.target.value)} style={inputStyle} />
          <input value={token} onChange={(e) => setToken(e.target.value)} style={inputStyle} type="password" />
          <button style={primaryButtonStyle} onClick={() => load()}>{loading ? "Atualizando..." : "Atualizar SLA"}</button>
        </div>
      </section>

      {message ? <div style={messageStyle}>{message}</div> : null}

      <section style={kpiGridStyle}>
        <Kpi label="Ativos" value={payload?.summary?.active || 0} hint="não resolvidos" />
        <Kpi label="Vencidos" value={payload?.summary?.overdue || 0} hint="fora do SLA" danger />
        <Kpi label="Vence breve" value={payload?.summary?.due_soon || 0} hint="próx. 30min" />
        <Kpi label="Sem responsável" value={payload?.summary?.unassigned || 0} hint="atribuir" />
        <Kpi label="Escalados" value={payload?.summary?.escalated || 0} hint="com reenvio" />
        <Kpi label="Resolvidos" value={payload?.summary?.resolved || 0} hint="fechados" />
      </section>

      <section style={panelStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <h3 style={{ margin: 0 }}>Ações de SLA</h3>
            <p style={{ margin: "6px 0 0", color: "#667085" }}>Escalonar vencidos envia e-mail real se o SMTP automático do projeto estiver salvo.</p>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <input placeholder="Responsável padrão" value={assignee} onChange={(e) => setAssignee(e.target.value)} style={inputStyle} />
            <input placeholder="Operador" value={actor} onChange={(e) => setActor(e.target.value)} style={inputStyle} />
            <button style={primaryButtonStyle} onClick={evaluate}>Avaliar SLA e escalar vencidos</button>
          </div>
        </div>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginBottom: 18 }}>
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Carga por responsável</h3>
          {(payload?.by_owner || []).slice(0, 8).map((row) => (
            <div key={row.owner} style={rankRowStyle}><span>{row.owner}</span><strong>{row.count}</strong></div>
          ))}
          {!payload?.by_owner?.length ? <p style={{ color: "#667085" }}>Sem alertas ativos.</p> : null}
        </div>
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Carga por severidade</h3>
          {(payload?.by_severity || []).map((row) => (
            <div key={row.severity} style={rankRowStyle}><span>{row.severity}</span><strong>{row.count}</strong></div>
          ))}
          {!payload?.by_severity?.length ? <p style={{ color: "#667085" }}>Sem alertas ativos.</p> : null}
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>Fila crítica de SLA</h3>
        <div style={{ display: "grid", gap: 12 }}>
          {(payload?.items || []).map((item) => (
            <article key={item.id} style={alertCardStyle}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: 420 }}>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                    <span style={{ ...pillStyle, ...severityColor(item.severity) }}>{(item.severity || "informativo").toUpperCase()}</span>
                    <span style={{ ...pillStyle, ...slaColor(item.sla_status) }}>{slaLabel(item.sla_status)}</span>
                    <span style={pillStyle}>{item.channel || "—"} · {item.status || "—"}</span>
                    <span style={pillStyle}>Esc.: {item.escalation_count || 0}</span>
                  </div>
                  <h3 style={{ margin: "0 0 8px", color: "#0b1f3a" }}>{item.title || "Alerta TV Fiscal"}</h3>
                  <p style={{ margin: 0, color: "#344054", lineHeight: 1.55 }}>{item.message || "—"}</p>
                  <p style={{ margin: "10px 0 0", color: "#667085", fontSize: 12 }}>
                    Criado: {item.created_at_display || "—"} · SLA: {item.sla_due_at_display || "—"} · Restante: {item.sla_remaining_minutes ?? "—"} min · Responsável: {item.assigned_to || "Sem responsável"}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignContent: "flex-start", justifyContent: "flex-end" }}>
                  {item.target_url ? <a href={item.target_url} target="_blank" rel="noreferrer" style={linkButtonStyle}>Abrir</a> : null}
                  <button style={smallButtonStyle} onClick={() => assign(item.id)}>Atribuir</button>
                  <button style={smallButtonStyle} onClick={() => ack(item.id)}>Ciente</button>
                  <button style={smallButtonStyle} onClick={() => resolve(item.id)}>Resolver</button>
                </div>
              </div>
            </article>
          ))}
          {!payload?.items?.length ? <div style={emptyStyle}>Nenhum alerta ativo encontrado.</div> : null}
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

const heroStyle: React.CSSProperties = { background: "linear-gradient(135deg,#0b1f3a,#172554)", color: "#fff", borderRadius: 18, padding: 24, marginBottom: 18, display: "flex", justifyContent: "space-between", gap: 20, alignItems: "center", boxShadow: "0 12px 28px rgba(11,31,58,.22)" };
const eyebrowStyle: React.CSSProperties = { color: "#ffccd5", fontWeight: 900, letterSpacing: 1.4, fontSize: 12 };
const inputStyle: React.CSSProperties = { border: "1px solid #d0d5dd", borderRadius: 10, padding: "11px 12px", minWidth: 180, background: "#fff" };
const primaryButtonStyle: React.CSSProperties = { border: "none", borderRadius: 10, padding: "12px 16px", background: "#b00020", color: "#fff", fontWeight: 900, cursor: "pointer" };
const smallButtonStyle: React.CSSProperties = { border: "1px solid #d0d5dd", borderRadius: 9, padding: "8px 10px", background: "#fff", color: "#344054", fontWeight: 800, cursor: "pointer" };
const linkButtonStyle: React.CSSProperties = { ...smallButtonStyle, textDecoration: "none", display: "inline-block" };
const messageStyle: React.CSSProperties = { background: "#fff7ed", border: "1px solid #fed7aa", color: "#9a3412", padding: 12, borderRadius: 12, marginBottom: 16 };
const kpiGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(6,minmax(0,1fr))", gap: 12, marginBottom: 18 };
const kpiStyle: React.CSSProperties = { background: "#fff", borderRadius: 16, padding: 16, boxShadow: "0 4px 14px rgba(15,23,42,.08)", border: "1px solid #eef2f6" };
const panelStyle: React.CSSProperties = { background: "#fff", borderRadius: 18, padding: 18, boxShadow: "0 4px 14px rgba(15,23,42,.08)", border: "1px solid #eef2f6", marginBottom: 18 };
const rankRowStyle: React.CSSProperties = { display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid #f2f4f7", color: "#344054" };
const alertCardStyle: React.CSSProperties = { border: "1px solid #e4e7ec", borderRadius: 16, padding: 16, background: "linear-gradient(180deg,#fff,#fcfcfd)" };
const pillStyle: React.CSSProperties = { borderRadius: 999, padding: "5px 9px", fontSize: 12, fontWeight: 800, background: "#f2f4f7", color: "#344054" };
const emptyStyle: React.CSSProperties = { textAlign: "center", color: "#667085", padding: 28, border: "1px dashed #d0d5dd", borderRadius: 14 };
