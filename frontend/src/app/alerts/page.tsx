"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "../../components/AppShell";

const API =
  (process.env.NEXT_PUBLIC_API_BASE ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000").replace(/\/$/, "");
const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

function getLocalAuthHeaders(): Record<string, string> {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("tvfiscal_auth_token")
      : null;

  return {
    "X-Admin-Token": "tvfiscal-admin-2026",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function authorizedFetch(url: string, init: RequestInit = {}) {
  return fetch(url, {
    ...init,
    cache: "no-store",
    headers: {
      ...getLocalAuthHeaders(),
      ...(init.headers || {}),
    },
  });
}

async function downloadWithAuth(url: string, filenameFallback: string) {
  const res = await authorizedFetch(url);

  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`Erro ao exportar arquivo: ${res.status} ${msg || res.statusText}`);
  }

  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") || "";
  const match = cd.match(/filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)\"?/i);
  const filename = decodeURIComponent(match?.[1] || match?.[2] || filenameFallback);

  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(objectUrl);
}

type AlertItem = {
  id: string;
  title: string;
  message: string;
  category: string;
  severity: "critico" | "alto" | "medio" | "informativo" | string;
  score: number;
  metric?: string | null;
  recommended_action: string;
  route?: string | null;
};

type AlertsPayload = {
  summary: {
    project_id: string;
    total_alerts: number;
    critical_alerts: number;
    high_alerts: number;
    medium_alerts: number;
    info_alerts: number;
    market_items: number;
    auditables: number;
    pending_identification: number;
    pending_identification_rate: number;
    pending_identification_investment: number;
    low_confidence_rate: number;
    editorial_items: number;
    negative_editorial: number;
    news_candidates: number;
    generated_at: string;
  };
  alerts: AlertItem[];
  market: {
    top_advertisers: Array<{ advertiser: string; items: number; investment: number; share: number; auditables: number }>;
    top_portals: Array<{ portal: string; items: number; investment: number; share: number; auditables: number }>;
    confidence: Record<string, number>;
  };
  editorial: {
    top_topics: Array<{ topic: string; count: number }>;
    top_sources: Array<{ source: string; count: number }>;
    latest_negative: Array<{ title: string; source?: string; topic?: string; sentiment_score?: number; url?: string }>;
  };
};

function brl(value?: number) {
  return `R$ ${Number(value || 0).toLocaleString("pt-BR")}`;
}

function severityLabel(sev: string) {
  const labels: Record<string, string> = {
    critico: "Crítico",
    alto: "Alto",
    medio: "Médio",
    informativo: "Informativo",
  };
  return labels[sev] || sev;
}

function severityStyle(sev: string): React.CSSProperties {
  const base: React.CSSProperties = {
    borderRadius: 999,
    padding: "6px 10px",
    fontWeight: 900,
    fontSize: 12,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    minWidth: 92,
  };
  if (sev === "critico") return { ...base, background: "#7f1d1d", color: "#fff" };
  if (sev === "alto") return { ...base, background: "#dc2626", color: "#fff" };
  if (sev === "medio") return { ...base, background: "#f97316", color: "#fff" };
  return { ...base, background: "#e5e7eb", color: "#1f2937" };
}

function categoryLabel(cat: string) {
  const labels: Record<string, string> = {
    identificacao: "Identificação",
    checking: "Checking",
    qualidade: "Qualidade",
    mercado: "Mercado",
    editorial: "Editorial",
  };
  return labels[cat] || cat;
}

export default function AlertsPage() {
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);
  const [data, setData] = useState<AlertsPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [category, setCategory] = useState("todos");
  const [severity, setSeverity] = useState("todos");

  async function load(customProjectId = projectId) {
    setLoading(true);
    setError("");
    try {
      const res = await authorizedFetch(`${API}/alerts/summary/${customProjectId}`);
      if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);
      const payload = (await res.json()) as AlertsPayload;
      setData(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar alertas.");
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

  const alerts = useMemo(() => {
    let rows = data?.alerts || [];
    if (category !== "todos") rows = rows.filter((a) => a.category === category);
    if (severity !== "todos") rows = rows.filter((a) => a.severity === severity);
    return rows;
  }, [data, category, severity]);

  function exportCsv() {
    downloadWithAuth(
      `${API}/alerts/summary/${projectId}/export.csv`,
      `alertas_${projectId}.csv`
    ).catch((err) =>
      setError(err instanceof Error ? err.message : "Erro ao exportar CSV.")
    );
  }

  return (
    <AppShell
      title="Central de Alertas"
      subtitle="Leitura executiva de riscos operacionais, identificação comercial, checking, clipping editorial e qualidade da base."
    >
      <section style={heroStyle}>
        <div>
          <div style={eyebrowStyle}>EXECUTIVE ALERTS · TV FISCAL WEBMONITOR</div>
          <h2 style={{ margin: "8px 0 10px", fontSize: 32 }}>Painel de decisão e prioridade operacional</h2>
          <p style={{ margin: 0, maxWidth: 820, lineHeight: 1.65 }}>
            Consolida os pontos que exigem ação: pendentes de identificação, baixa confiança, evidências auditáveis,
            candidatos editoriais, matérias negativas e concentração de mercado.
          </p>
        </div>
        <div style={{ display: "grid", gap: 10, minWidth: 360 }}>
          <input value={projectId} onChange={(e) => setProjectId(e.target.value)} style={inputStyle} />
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button onClick={() => load()} style={primaryButtonStyle}>{loading ? "Atualizando..." : "Atualizar alertas"}</button>
            <button onClick={exportCsv} style={secondaryButtonStyle}>Exportar CSV</button>
          </div>
        </div>
      </section>

      {error ? <div style={errorStyle}>{error}</div> : null}

      <section style={kpiGridStyle}>
        <Kpi label="Alertas" value={data?.summary.total_alerts || 0} hint="ativos no recorte" />
        <Kpi label="Críticos/Altos" value={(data?.summary.critical_alerts || 0) + (data?.summary.high_alerts || 0)} hint="prioridade executiva" />
        <Kpi label="Pendentes ID" value={data?.summary.pending_identification || 0} hint={`${data?.summary.pending_identification_rate || 0}% do mercado`} />
        <Kpi label="Invest. pendente" value={brl(data?.summary.pending_identification_investment)} hint="qualificação comercial" />
        <Kpi label="Auditáveis" value={data?.summary.auditables || 0} hint="checking comprovável" />
        <Kpi label="Baixa confiança" value={`${data?.summary.low_confidence_rate || 0}%`} hint="exige revisão" />
        <Kpi label="Matérias" value={data?.summary.editorial_items || 0} hint="clipping editorial" />
        <Kpi label="Negativas" value={data?.summary.negative_editorial || 0} hint="risco reputacional" />
      </section>

      <section style={panelStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", marginBottom: 18 }}>
          <div>
            <h3 style={{ margin: 0 }}>Alertas priorizados</h3>
            <p style={{ margin: "5px 0 0", color: "#667085" }}>
              Ordenados por score operacional. Use os atalhos para resolver na tela correta.
            </p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <select value={category} onChange={(e) => setCategory(e.target.value)} style={selectStyle}>
              <option value="todos">Todas as categorias</option>
              <option value="identificacao">Identificação</option>
              <option value="checking">Checking</option>
              <option value="qualidade">Qualidade</option>
              <option value="mercado">Mercado</option>
              <option value="editorial">Editorial</option>
            </select>
            <select value={severity} onChange={(e) => setSeverity(e.target.value)} style={selectStyle}>
              <option value="todos">Todas as severidades</option>
              <option value="critico">Crítico</option>
              <option value="alto">Alto</option>
              <option value="medio">Médio</option>
              <option value="informativo">Informativo</option>
            </select>
          </div>
        </div>
        <div style={{ display: "grid", gap: 14 }}>
          {alerts.length ? alerts.map((alert) => (
            <article key={alert.id} style={alertCardStyle}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 18 }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                    <span style={severityStyle(alert.severity)}>{severityLabel(alert.severity)}</span>
                    <span style={categoryBadgeStyle}>{categoryLabel(alert.category)}</span>
                    <span style={scoreStyle}>Score {alert.score}</span>
                    {alert.metric ? <span style={metricStyle}>{alert.metric}</span> : null}
                  </div>
                  <h4 style={{ margin: "12px 0 6px", fontSize: 18, color: "#101828" }}>{alert.title}</h4>
                  <p style={{ margin: 0, color: "#344054", lineHeight: 1.55 }}>{alert.message}</p>
                  <p style={{ margin: "10px 0 0", color: "#667085", lineHeight: 1.55 }}>
                    <strong>Ação recomendada:</strong> {alert.recommended_action}
                  </p>
                </div>
                {alert.route ? (
                  <a href={`${alert.route}?project_id=${projectId}`} style={openButtonStyle}>Abrir</a>
                ) : null}
              </div>
            </article>
          )) : (
            <div style={emptyStyle}>Nenhum alerta encontrado para o filtro atual.</div>
          )}
        </div>
      </section>

      <section style={twoColumnsStyle}>
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Leitura de mercado</h3>
          <Table
            columns={["Anunciante", "Itens", "Invest.", "Share"]}
            rows={(data?.market.top_advertisers || []).map((r) => [r.advertiser, r.items, brl(r.investment), `${r.share}%`])}
          />
          <h4>Top portais</h4>
          <Table
            columns={["Portal", "Itens", "Invest.", "Share"]}
            rows={(data?.market.top_portals || []).map((r) => [r.portal, r.items, brl(r.investment), `${r.share}%`])}
          />
        </div>
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Leitura editorial</h3>
          <Table
            columns={["Tema", "Qtd."]}
            rows={(data?.editorial.top_topics || []).map((r) => [r.topic, r.count])}
          />
          <h4>Últimas negativas</h4>
          <div style={{ display: "grid", gap: 10 }}>
            {(data?.editorial.latest_negative || []).slice(0, 5).map((item, idx) => (
              <a key={`${item.url}-${idx}`} href={item.url || "#"} target="_blank" rel="noreferrer" style={negativeItemStyle}>
                <strong>{item.title}</strong>
                <span>{item.source || "Fonte"} · {item.topic || "Tema"} · score {item.sentiment_score ?? "—"}</span>
              </a>
            ))}
            {!(data?.editorial.latest_negative || []).length ? <div style={emptyStyle}>Sem negativas no recorte.</div> : null}
          </div>
        </div>
      </section>
    </AppShell>
  );
}

function Kpi({ label, value, hint }: { label: string; value: string | number; hint: string }) {
  return (
    <div style={kpiStyle}>
      <div style={{ fontSize: 12, color: "#667085", fontWeight: 800, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 900, color: "#101828", marginTop: 6 }}>{value}</div>
      <div style={{ fontSize: 12, color: "#98a2b3", marginTop: 4 }}>{hint}</div>
    </div>
  );
}

function Table({ columns, rows }: { columns: string[]; rows: Array<Array<string | number>> }) {
  return (
    <div style={{ overflowX: "auto", marginTop: 12 }}>
      <table style={tableStyle}>
        <thead>
          <tr>{columns.map((c) => <th key={c} style={thStyle}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.length ? rows.map((row, idx) => (
            <tr key={idx}>{row.map((cell, i) => <td key={i} style={tdStyle}>{cell}</td>)}</tr>
          )) : <tr><td colSpan={columns.length} style={tdStyle}>Sem dados.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

const heroStyle: React.CSSProperties = {
  background: "linear-gradient(135deg,#071528 0%,#10243f 58%,#7a0015 100%)",
  color: "#fff",
  borderRadius: 22,
  padding: 28,
  display: "flex",
  justifyContent: "space-between",
  gap: 24,
  alignItems: "center",
  boxShadow: "0 18px 45px rgba(16,24,40,.18)",
  marginBottom: 22,
};
const eyebrowStyle: React.CSSProperties = { color: "#fda4af", fontSize: 12, fontWeight: 900, letterSpacing: 1.5 };
const inputStyle: React.CSSProperties = { padding: "12px 14px", borderRadius: 10, border: "1px solid rgba(255,255,255,.35)", background: "#fff", color: "#101828", fontWeight: 700 };
const selectStyle: React.CSSProperties = { padding: "10px 12px", borderRadius: 10, border: "1px solid #d0d5dd", background: "#fff", color: "#101828", fontWeight: 700 };
const primaryButtonStyle: React.CSSProperties = { background: "#b00020", color: "#fff", border: "none", borderRadius: 10, padding: "12px 16px", fontWeight: 900, cursor: "pointer" };
const secondaryButtonStyle: React.CSSProperties = { background: "rgba(255,255,255,.14)", color: "#fff", border: "1px solid rgba(255,255,255,.45)", borderRadius: 10, padding: "12px 16px", fontWeight: 900, cursor: "pointer" };
const kpiGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(4,minmax(160px,1fr))", gap: 14, marginBottom: 22 };
const kpiStyle: React.CSSProperties = { background: "#fff", borderRadius: 18, padding: 18, border: "1px solid #eaecf0", boxShadow: "0 10px 25px rgba(16,24,40,.06)" };
const panelStyle: React.CSSProperties = { background: "#fff", borderRadius: 20, padding: 22, border: "1px solid #eaecf0", boxShadow: "0 10px 30px rgba(16,24,40,.06)", marginBottom: 22 };
const twoColumnsStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 };
const alertCardStyle: React.CSSProperties = { border: "1px solid #eaecf0", borderRadius: 16, padding: 16, background: "linear-gradient(180deg,#fff,#fbfcfe)" };
const categoryBadgeStyle: React.CSSProperties = { background: "#eef4ff", color: "#3538cd", borderRadius: 999, padding: "6px 10px", fontSize: 12, fontWeight: 900 };
const scoreStyle: React.CSSProperties = { background: "#f2f4f7", color: "#344054", borderRadius: 999, padding: "6px 10px", fontSize: 12, fontWeight: 900 };
const metricStyle: React.CSSProperties = { background: "#fff1f2", color: "#be123c", borderRadius: 999, padding: "6px 10px", fontSize: 12, fontWeight: 900 };
const openButtonStyle: React.CSSProperties = { alignSelf: "center", background: "#101828", color: "#fff", textDecoration: "none", padding: "10px 14px", borderRadius: 10, fontWeight: 900, whiteSpace: "nowrap" };
const errorStyle: React.CSSProperties = { background: "#fee2e2", color: "#991b1b", padding: 14, borderRadius: 12, marginBottom: 16, fontWeight: 800 };
const emptyStyle: React.CSSProperties = { background: "#f9fafb", color: "#667085", padding: 14, borderRadius: 12 };
const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: 13 };
const thStyle: React.CSSProperties = { textAlign: "left", padding: "10px 8px", background: "#101828", color: "#fff", fontSize: 12 };
const tdStyle: React.CSSProperties = { padding: "10px 8px", borderBottom: "1px solid #eaecf0", verticalAlign: "top" };
const negativeItemStyle: React.CSSProperties = { display: "grid", gap: 4, padding: 12, borderRadius: 12, border: "1px solid #fee2e2", background: "#fff7f7", color: "#101828", textDecoration: "none" };
