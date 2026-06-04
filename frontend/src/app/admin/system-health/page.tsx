"use client";

import React, { useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";
import { adminJson, adminFetch, API_BASE, ADMIN_TOKEN_KEY, DEFAULT_ADMIN_TOKEN } from "../../../lib/apiClient";

const API = API_BASE;

type Check = {
  service: string;
  label: string;
  status: "ok" | "warning" | "error" | string;
  message: string;
  latency_ms?: number;
  details?: Record<string, any>;
  checked_at_display?: string;
};

type HealthData = {
  app: string;
  generated_at_display?: string;
  summary: {
    overall_status: string;
    overall_label: string;
    ok: number;
    warning: number;
    error: number;
    services: number;
    activity_24h?: Record<string, number>;
  };
  checks: Check[];
  recommendations: string[];
  uptime_robot?: Record<string, any>;
};

type HistoryItem = {
  id: string;
  service: string;
  status: string;
  latency_ms?: number;
  message?: string;
  trigger_source?: string;
  created_at_display?: string;
};

function statusColor(status?: string) {
  if (status === "ok") return "#027A48";
  if (status === "warning") return "#B54708";
  if (status === "error") return "#B42318";
  return "#344054";
}

function statusBg(status?: string) {
  if (status === "ok") return "#ECFDF3";
  if (status === "warning") return "#FFFAEB";
  if (status === "error") return "#FEF3F2";
  return "#F2F4F7";
}

function formatBytes(value?: number) {
  const n = Number(value || 0);
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

export default function SystemHealthPage() {
  const [token, setToken] = useState(DEFAULT_ADMIN_TOKEN);
  const [data, setData] = useState<HealthData | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [serviceFilter, setServiceFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
    return adminJson<T>(path, {
      ...options,
      bearer: false,
      admin: true,
      json: true,
    });
  }

  async function load() {
    setLoading(true);
    setMessage("");
    try {
      const [health, hist] = await Promise.all([
        api("/system/health/advanced"),
        api(`/system/health/history?limit=80${serviceFilter ? `&service=${encodeURIComponent(serviceFilter)}` : ""}${statusFilter ? `&status=${encodeURIComponent(statusFilter)}` : ""}`),
      ]);
      setData(health);
      setHistory(hist.items || []);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao carregar saúde do sistema.");
    } finally {
      setLoading(false);
    }
  }

  async function runCheck() {
    setLoading(true);
    setMessage("Executando verificação completa...");
    try {
      const health = await api("/system/health/check", { method: "POST" });
      setData(health);
      setMessage("Verificação registrada no histórico.");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao executar verificação.");
    } finally {
      setLoading(false);
    }
  }

  function csvUrl() {
    return `${API}/system/health/history/export.csv?admin_token=${encodeURIComponent(token)}&limit=1000`;
  }

  function pdfUrl() {
    return `${API}/system/health/report.pdf?admin_token=${encodeURIComponent(token)}`;
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  const activity = data?.summary?.activity_24h || {};
  const serviceNames = useMemo(() => Array.from(new Set([...(data?.checks || []).map((c) => c.service), ...history.map((h) => h.service)])).sort(), [data, history]);

  return (
    <AppShell
      title="Saúde do Sistema"
      subtitle="Healthcheck avançado, disponibilidade, serviços internos, scheduler, evidências, notificações e histórico para produção."
    >
      <section style={heroStyle}>
        <div>
          <div style={eyebrowStyle}>SYSTEM HEALTH · TV FISCAL WEBMONITOR</div>
          <h2 style={{ margin: "8px 0 10px", fontSize: 32 }}>Operação, uptime e confiabilidade</h2>
          <p style={{ margin: 0, maxWidth: 920, lineHeight: 1.65 }}>
            Acompanhe PostgreSQL, Redis, MinIO, Scheduler, disco, backup e notificações em uma única tela. Gere histórico e relatório técnico para auditoria operacional.
          </p>
        </div>
        <div style={{ display: "grid", gap: 10, minWidth: 390 }}>
          <input value={token} onChange={(e) => setToken(e.target.value)} type="password" style={inputStyle} />
          <button onClick={load} style={primaryButtonStyle}>{loading ? "Atualizando..." : "Atualizar"}</button>
          <button onClick={runCheck} style={secondaryButtonStyle}>Executar healthcheck e gravar histórico</button>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            <a href={csvUrl()} target="_blank" rel="noreferrer" style={secondaryLinkStyle}>Exportar CSV</a>
            <a href={pdfUrl()} target="_blank" rel="noreferrer" style={secondaryLinkStyle}>Relatório PDF</a>
          </div>
        </div>
      </section>

      {message ? <div style={messageStyle}>{message}</div> : null}

      <section style={kpiGridStyle}>
        <Kpi label="Status geral" value={data?.summary?.overall_label || "—"} hint="ambiente" status={data?.summary?.overall_status} />
        <Kpi label="Serviços OK" value={data?.summary?.ok || 0} hint={`${data?.summary?.services || 0} monitorados`} status="ok" />
        <Kpi label="Atenção" value={data?.summary?.warning || 0} hint="warnings" status="warning" />
        <Kpi label="Erros" value={data?.summary?.error || 0} hint="falhas" status="error" />
        <Kpi label="Scheduler 24h" value={activity.scheduler_runs_24h || 0} hint="execuções" />
        <Kpi label="Notificações 24h" value={activity.notifications_24h || 0} hint="logs" />
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginBottom: 18 }}>
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Recomendações operacionais</h3>
          {(data?.recommendations || []).map((line, idx) => (
            <p key={idx} style={{ margin: "8px 0", lineHeight: 1.55, color: "#344054" }}>• {line}</p>
          ))}
          {!data?.recommendations?.length ? <p style={{ color: "#667085" }}>Sem recomendações críticas.</p> : null}
        </div>
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Endpoints para UptimeRobot</h3>
          <p style={smallTextStyle}>Use estes endpoints em monitor externo. O endpoint <strong>/health/ready</strong> valida o banco e retorna 503 se houver falha.</p>
          <CodeLine label="Live" value={`${API}/health/live`} />
          <CodeLine label="Ready" value={`${API}/health/ready`} />
          <CodeLine label="Advanced" value={`${API}/system/health/uptime`} />
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>Serviços monitorados</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 14 }}>
          {(data?.checks || []).map((check) => <ServiceCard key={check.service} check={check} />)}
        </div>
      </section>

      <section style={panelStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <h3 style={{ margin: 0 }}>Histórico de disponibilidade</h3>
            <p style={{ margin: "6px 0 0", color: "#667085" }}>Registros gerados por healthchecks manuais, relatórios e integrações futuras.</p>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <select value={serviceFilter} onChange={(e) => setServiceFilter(e.target.value)} style={inputStyle}>
              <option value="">Todos os serviços</option>
              {serviceNames.map((svc) => <option key={svc} value={svc}>{svc}</option>)}
            </select>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={inputStyle}>
              <option value="">Todos os status</option>
              <option value="ok">OK</option>
              <option value="warning">Atenção</option>
              <option value="error">Erro</option>
            </select>
            <button onClick={load} style={secondaryButtonStyle}>Filtrar</button>
          </div>
        </div>
        <div style={{ overflowX: "auto", marginTop: 14 }}>
          <table style={tableStyle}>
            <thead>
              <tr><th>Data</th><th>Serviço</th><th>Status</th><th>Latência</th><th>Origem</th><th>Mensagem</th></tr>
            </thead>
            <tbody>
              {history.map((row) => (
                <tr key={row.id}>
                  <td>{row.created_at_display || "—"}</td>
                  <td>{row.service}</td>
                  <td><span style={{ ...badgeStyle, background: statusBg(row.status), color: statusColor(row.status) }}>{row.status}</span></td>
                  <td>{row.latency_ms ?? "—"} ms</td>
                  <td>{row.trigger_source || "—"}</td>
                  <td>{row.message || "—"}</td>
                </tr>
              ))}
              {!history.length ? <tr><td colSpan={6}>Nenhum histórico registrado. Clique em “Executar healthcheck e gravar histórico”.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}

function Kpi({ label, value, hint, status }: { label: string; value: number | string; hint: string; status?: string }) {
  return (
    <div style={kpiStyle}>
      <div style={{ color: statusColor(status), fontSize: 26, fontWeight: 900 }}>{value}</div>
      <div style={{ fontWeight: 800, color: "#0b1f3a" }}>{label}</div>
      <div style={{ color: "#667085", fontSize: 12 }}>{hint}</div>
    </div>
  );
}

function CodeLine({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <strong style={{ color: "#0B1F3A" }}>{label}: </strong>
      <code style={{ background: "#F2F4F7", padding: "3px 6px", borderRadius: 6 }}>{value}</code>
    </div>
  );
}

function ServiceCard({ check }: { check: Check }) {
  const details = check.details || {};
  const diskPct = details.used_percent;
  return (
    <div style={{ ...serviceCardStyle, borderColor: statusColor(check.status) }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontWeight: 900, color: "#0B1F3A" }}>{check.label}</div>
          <div style={{ fontSize: 12, color: "#667085" }}>{check.service}</div>
        </div>
        <span style={{ ...badgeStyle, background: statusBg(check.status), color: statusColor(check.status) }}>{check.status}</span>
      </div>
      <p style={{ margin: "10px 0", color: "#344054", lineHeight: 1.45 }}>{check.message}</p>
      <div style={{ color: "#667085", fontSize: 12 }}>Latência: {check.latency_ms ?? "—"} ms</div>
      {typeof diskPct === "number" ? <div style={{ color: "#667085", fontSize: 12 }}>Disco: {diskPct}% usado · {formatBytes(details.free_bytes)} livres</div> : null}
      {details.latest_backup?.filename ? <div style={{ color: "#667085", fontSize: 12 }}>Último backup: {details.latest_backup.filename}</div> : null}
      {details.last_error ? <div style={{ color: "#B42318", fontSize: 12 }}>Último erro: {details.last_error}</div> : null}
    </div>
  );
}

const heroStyle: React.CSSProperties = {
  background: "linear-gradient(135deg,#08172b,#102a4c)",
  color: "#fff",
  padding: 24,
  borderRadius: 18,
  display: "flex",
  justifyContent: "space-between",
  gap: 20,
  alignItems: "center",
  marginBottom: 20,
  boxShadow: "0 14px 30px rgba(0,0,0,.18)",
};
const eyebrowStyle: React.CSSProperties = { color: "#ffccd5", fontWeight: 900, letterSpacing: 1.3, fontSize: 12 };
const inputStyle: React.CSSProperties = { padding: "12px 14px", borderRadius: 10, border: "1px solid #D0D5DD", background: "#fff", color: "#101828" };
const primaryButtonStyle: React.CSSProperties = { padding: "12px 14px", borderRadius: 10, border: 0, background: "#b00020", color: "#fff", fontWeight: 900, cursor: "pointer" };
const secondaryButtonStyle: React.CSSProperties = { padding: "12px 14px", borderRadius: 10, border: "1px solid #D0D5DD", background: "#fff", color: "#0B1F3A", fontWeight: 900, cursor: "pointer" };
const secondaryLinkStyle: React.CSSProperties = { padding: "12px 14px", borderRadius: 10, border: "1px solid #D0D5DD", background: "#fff", color: "#0B1F3A", fontWeight: 900, textDecoration: "none", textAlign: "center" };
const messageStyle: React.CSSProperties = { padding: 14, background: "#fff7ed", border: "1px solid #fed7aa", borderRadius: 12, marginBottom: 18, color: "#7c2d12" };
const kpiGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 14, marginBottom: 18 };
const kpiStyle: React.CSSProperties = { background: "#fff", borderRadius: 16, padding: 16, boxShadow: "0 8px 20px rgba(16,24,40,.08)", border: "1px solid #EAECF0" };
const panelStyle: React.CSSProperties = { background: "#fff", borderRadius: 16, padding: 18, boxShadow: "0 8px 22px rgba(16,24,40,.08)", border: "1px solid #EAECF0", marginBottom: 18 };
const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: 13 };
const badgeStyle: React.CSSProperties = { display: "inline-block", padding: "5px 9px", borderRadius: 999, fontSize: 12, fontWeight: 900 };
const serviceCardStyle: React.CSSProperties = { border: "1px solid", borderLeft: "5px solid", borderRadius: 14, padding: 14, background: "#fff" };
const smallTextStyle: React.CSSProperties = { color: "#667085", lineHeight: 1.55 };
