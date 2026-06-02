"use client";

import React, { useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";

const API = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";
const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";
const DEFAULT_TOKEN = "tvfiscal-admin-2026";

type InboxItem = {
  id: string;
  created_at_display?: string;
  channel: string;
  status: string;
  alert_status: string;
  severity?: string;
  category?: string;
  title?: string;
  message?: string;
  target_url?: string;
  provider?: string;
  provider_response?: string;
  acknowledged_by?: string;
  acknowledged_at_display?: string;
  resolved_by?: string;
  resolved_at_display?: string;
  resolution_note?: string;
  snoozed_until_display?: string;
  priority_score?: number;
};

type InboxPayload = {
  project_id: string;
  summary: Record<string, number>;
  items: InboxItem[];
};

function statusLabel(value?: string) {
  const map: Record<string, string> = {
    aberto: "Aberto",
    ciente: "Ciente",
    resolvido: "Resolvido",
    adiado: "Adiado",
  };
  return map[value || ""] || value || "—";
}

function deliveryLabel(value?: string) {
  const map: Record<string, string> = {
    sent: "Enviado",
    registered: "Painel",
    dry_run: "Simulado",
    skipped: "Ignorado",
    error: "Erro",
  };
  return map[value || ""] || value || "—";
}

function channelLabel(value?: string) {
  const map: Record<string, string> = { painel: "Painel", sms: "SMS", email: "E-mail", whatsapp: "WhatsApp", webhook: "Webhook" };
  return map[value || ""] || value || "—";
}

function severityStyle(severity?: string): React.CSSProperties {
  const sev = (severity || "informativo").toLowerCase();
  if (sev === "critico") return { background: "#7f1d1d", color: "#fff" };
  if (sev === "alto") return { background: "#fee2e2", color: "#991b1b" };
  if (sev === "medio") return { background: "#fff7ed", color: "#9a3412" };
  return { background: "#eef2ff", color: "#3730a3" };
}

export default function AlertInboxPage() {
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);
  const [token, setToken] = useState(DEFAULT_TOKEN);
  const [status, setStatus] = useState("aberto");
  const [severity, setSeverity] = useState("todos");
  const [channel, setChannel] = useState("todos");
  const [actor, setActor] = useState("TV Fiscal");
  const [note, setNote] = useState("");
  const [payload, setPayload] = useState<InboxPayload | null>(null);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState("");
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
      const params = new URLSearchParams();
      params.set("status", status);
      if (severity !== "todos") params.set("severity", severity);
      if (channel !== "todos") params.set("channel", channel);
      params.set("limit", "200");
      const data = await api(`/notifications/inbox/${customProjectId}?${params.toString()}`);
      setPayload(data);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao carregar caixa de alertas.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const p = params.get("project_id") || DEFAULT_PROJECT_ID;
    setProjectId(p);
    load(p);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, severity, channel]);

  const selectedIds = useMemo(() => Object.keys(selected).filter((id) => selected[id]), [selected]);

  async function updateOne(id: string, action: string, extra: Record<string, unknown> = {}) {
    const result = await api(`/notifications/logs/${id}/${action}`, {
      method: "POST",
      body: JSON.stringify({ actor, note, ...extra }),
    });
    setMessage(result.message || "Status atualizado.");
    await load();
  }

  async function bulk(action: string) {
    if (!selectedIds.length) {
      setMessage("Selecione pelo menos um alerta.");
      return;
    }
    const result = await api(`/notifications/logs/${projectId}/bulk-status`, {
      method: "POST",
      body: JSON.stringify({ ids: selectedIds, action, actor, note }),
    });
    setSelected({});
    setMessage(result.message || "Alertas atualizados.");
    await load();
  }

  return (
    <AppShell
      title="Caixa de Alertas"
      subtitle="Triagem operacional dos alertas gerados pelo WebMonitor, com ciência, adiamento, resolução e histórico de atendimento."
    >
      <section style={heroStyle}>
        <div>
          <div style={eyebrowStyle}>ALERT INBOX · TV FISCAL WEBMONITOR</div>
          <h2 style={{ margin: "8px 0 10px", fontSize: 32 }}>Alertas acionáveis por projeto</h2>
          <p style={{ margin: 0, maxWidth: 860, lineHeight: 1.65 }}>
            Use esta tela como fila operacional após os disparos automáticos. Cada alerta pode ser marcado como ciente, adiado, resolvido ou reaberto, preservando trilha de atendimento.
          </p>
        </div>
        <div style={{ display: "grid", gap: 10, minWidth: 390 }}>
          <input value={projectId} onChange={(e) => setProjectId(e.target.value)} style={inputStyle} />
          <input value={token} onChange={(e) => setToken(e.target.value)} style={inputStyle} type="password" />
          <button style={primaryButtonStyle} onClick={() => load()}>{loading ? "Atualizando..." : "Atualizar caixa"}</button>
        </div>
      </section>

      {message ? <div style={messageStyle}>{message}</div> : null}

      <section style={kpiGridStyle}>
        <Kpi label="Abertos" value={payload?.summary?.open || 0} hint="pendentes" />
        <Kpi label="Críticos" value={payload?.summary?.critical_open || 0} hint="abertos" />
        <Kpi label="Altos" value={payload?.summary?.high_open || 0} hint="abertos" />
        <Kpi label="Cientes" value={payload?.summary?.acknowledged || 0} hint="em acompanhamento" />
        <Kpi label="Adiados" value={payload?.summary?.snoozed || 0} hint="snooze" />
        <Kpi label="Resolvidos" value={payload?.summary?.resolved || 0} hint="fechados" />
        <Kpi label="Erros" value={payload?.summary?.errors_open || 0} hint="envio/integração" />
      </section>

      <section style={panelStyle}>
        <div style={toolbarStyle}>
          <select value={status} onChange={(e) => setStatus(e.target.value)} style={selectStyle}>
            <option value="aberto">Abertos</option>
            <option value="ciente">Cientes</option>
            <option value="adiado">Adiados</option>
            <option value="resolvido">Resolvidos</option>
            <option value="todos">Todos</option>
          </select>
          <select value={severity} onChange={(e) => setSeverity(e.target.value)} style={selectStyle}>
            <option value="todos">Todas as severidades</option>
            <option value="critico">Crítico</option>
            <option value="alto">Alto</option>
            <option value="medio">Médio</option>
            <option value="informativo">Informativo</option>
          </select>
          <select value={channel} onChange={(e) => setChannel(e.target.value)} style={selectStyle}>
            <option value="todos">Todos os canais</option>
            <option value="email">E-mail</option>
            <option value="painel">Painel</option>
            <option value="sms">SMS</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="webhook">Webhook</option>
          </select>
          <input placeholder="Responsável" value={actor} onChange={(e) => setActor(e.target.value)} style={inputStyle} />
          <input placeholder="Nota de atendimento" value={note} onChange={(e) => setNote(e.target.value)} style={inputStyle} />
          <button style={secondaryButtonStyle} onClick={() => bulk("ack")}>Marcar ciente</button>
          <button style={secondaryButtonStyle} onClick={() => bulk("resolve")}>Resolver selecionados</button>
        </div>
      </section>

      <section style={panelStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", marginBottom: 12 }}>
          <div>
            <h3 style={{ margin: 0 }}>Fila de alertas</h3>
            <p style={{ margin: "5px 0 0", color: "#667085" }}>Itens ordenados por data de geração. Use seleção múltipla para tratar alertas em lote.</p>
          </div>
          <span style={badgeStyle}>{selectedIds.length} selecionado(s)</span>
        </div>
        <div style={{ display: "grid", gap: 12 }}>
          {(payload?.items || []).map((item) => (
            <article key={item.id} style={alertCardStyle}>
              <div style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                <input type="checkbox" checked={!!selected[item.id]} onChange={(e) => setSelected({ ...selected, [item.id]: e.target.checked })} style={{ marginTop: 6 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 14, alignItems: "flex-start", flexWrap: "wrap" }}>
                    <div>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                        <span style={{ ...pillStyle, ...severityStyle(item.severity) }}>{(item.severity || "informativo").toUpperCase()}</span>
                        <span style={pillStyle}>{statusLabel(item.alert_status)}</span>
                        <span style={pillStyle}>{channelLabel(item.channel)} · {deliveryLabel(item.status)}</span>
                        <span style={pillStyle}>{item.category || "geral"}</span>
                      </div>
                      <h3 style={{ margin: "0 0 8px", color: "#0b1f3a" }}>{item.title || "Alerta TV Fiscal"}</h3>
                      <p style={{ margin: 0, color: "#344054", lineHeight: 1.55 }}>{item.message || "—"}</p>
                      <p style={{ margin: "10px 0 0", color: "#98a2b3", fontSize: 12 }}>
                        {item.created_at_display || "—"} · Provider: {item.provider || "—"} · Resposta: {item.provider_response || "—"}
                      </p>
                      {item.acknowledged_by || item.resolved_by || item.snoozed_until_display ? (
                        <p style={{ margin: "6px 0 0", color: "#667085", fontSize: 12 }}>
                          {item.acknowledged_by ? `Ciente por ${item.acknowledged_by} em ${item.acknowledged_at_display || "—"}. ` : ""}
                          {item.resolved_by ? `Resolvido por ${item.resolved_by} em ${item.resolved_at_display || "—"}. ` : ""}
                          {item.snoozed_until_display ? `Adiado até ${item.snoozed_until_display}. ` : ""}
                          {item.resolution_note ? `Nota: ${item.resolution_note}` : ""}
                        </p>
                      ) : null}
                    </div>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
                      {item.target_url ? <a href={item.target_url} target="_blank" rel="noreferrer" style={linkButtonStyle}>Abrir</a> : null}
                      <button style={smallButtonStyle} onClick={() => updateOne(item.id, "ack")}>Ciente</button>
                      <button style={smallButtonStyle} onClick={() => updateOne(item.id, "snooze", { minutes: 120 })}>Adiar 2h</button>
                      <button style={smallButtonStyle} onClick={() => updateOne(item.id, "resolve")}>Resolver</button>
                      <button style={smallButtonStyle} onClick={() => updateOne(item.id, "reopen")}>Reabrir</button>
                    </div>
                  </div>
                </div>
              </div>
            </article>
          ))}
          {!payload?.items?.length ? <div style={emptyStyle}>Nenhum alerta encontrado para o filtro atual.</div> : null}
        </div>
      </section>
    </AppShell>
  );
}

function Kpi({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div style={kpiStyle}>
      <div style={{ color: "#667085", fontSize: 13, fontWeight: 800 }}>{label}</div>
      <div style={{ fontSize: 30, fontWeight: 900, color: "#0b1f3a", marginTop: 6 }}>{value}</div>
      {hint ? <div style={{ color: "#98a2b3", fontSize: 12 }}>{hint}</div> : null}
    </div>
  );
}

const heroStyle: React.CSSProperties = { background: "linear-gradient(135deg,#0b1f3a 0%,#152f53 60%,#b00020 100%)", color: "#fff", borderRadius: 20, padding: 26, display: "flex", justifyContent: "space-between", gap: 24, alignItems: "flex-start", boxShadow: "0 18px 40px rgba(11,31,58,0.22)", marginBottom: 18 };
const eyebrowStyle: React.CSSProperties = { fontSize: 12, letterSpacing: 2, textTransform: "uppercase", color: "#ffccd5", fontWeight: 900 };
const kpiGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(7,minmax(120px,1fr))", gap: 14, margin: "18px 0" };
const kpiStyle: React.CSSProperties = { background: "#fff", borderRadius: 16, padding: 18, boxShadow: "0 8px 20px rgba(16,24,40,0.08)", border: "1px solid #eef2f6" };
const panelStyle: React.CSSProperties = { background: "#fff", borderRadius: 18, padding: 20, marginBottom: 18, boxShadow: "0 8px 22px rgba(16,24,40,0.08)", border: "1px solid #eef2f6" };
const toolbarStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(3,minmax(150px,1fr)) repeat(2,minmax(180px,1fr)) auto auto", gap: 10, alignItems: "center" };
const inputStyle: React.CSSProperties = { border: "1px solid #d0d5dd", borderRadius: 12, padding: "12px 14px", fontSize: 14, background: "#fff", color: "#101828", colorScheme: "light" };
const selectStyle: React.CSSProperties = { ...inputStyle, appearance: "auto" };
const primaryButtonStyle: React.CSSProperties = { background: "#b00020", color: "#fff", border: 0, borderRadius: 12, padding: "12px 16px", fontWeight: 900, cursor: "pointer" };
const secondaryButtonStyle: React.CSSProperties = { background: "#0b1f3a", color: "#fff", border: 0, borderRadius: 12, padding: "11px 14px", fontWeight: 800, cursor: "pointer" };
const smallButtonStyle: React.CSSProperties = { ...secondaryButtonStyle, padding: "8px 10px", fontSize: 12 };
const linkButtonStyle: React.CSSProperties = { ...smallButtonStyle, textDecoration: "none", background: "#b00020" };
const messageStyle: React.CSSProperties = { background: "#ecfdf3", color: "#027a48", border: "1px solid #abefc6", padding: 12, borderRadius: 12, marginBottom: 14, fontWeight: 800 };
const badgeStyle: React.CSSProperties = { display: "inline-flex", alignItems: "center", borderRadius: 999, padding: "7px 11px", background: "#eef2ff", color: "#3730a3", fontWeight: 900, fontSize: 12 };
const pillStyle: React.CSSProperties = { display: "inline-flex", alignItems: "center", borderRadius: 999, padding: "5px 9px", background: "#f2f4f7", color: "#344054", fontWeight: 800, fontSize: 11 };
const alertCardStyle: React.CSSProperties = { border: "1px solid #e4e7ec", borderRadius: 16, padding: 16, background: "linear-gradient(180deg,#ffffff,#fbfcff)" };
const emptyStyle: React.CSSProperties = { border: "1px dashed #d0d5dd", borderRadius: 16, padding: 22, color: "#667085", textAlign: "center" };
