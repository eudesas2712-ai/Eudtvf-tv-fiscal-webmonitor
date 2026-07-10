"use client";

import { useEffect, useState } from "react";
import AppShell from "../../components/AppShell";
import { adminFetch, API_BASE } from "../../lib/apiClient";

const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

type ReportItem = {
  id: string;
  report_family: string;
  report_type: string;
  filename: string;
  file_size?: number;
  public_url?: string;
  filters?: Record<string, string>;
  created_at?: string;
};

function initialSearchParam(name: string) {
  if (typeof window === "undefined") return "";
  return new URLSearchParams(window.location.search).get(name) || "";
}

function labelFamily(value: string) {
  if (value === "editorial") return "Editorial";
  if (value === "editorial_social") return "Editorial + Social";
  if (value === "social") return "Social Monitor";
  return value;
}

function labelType(value: string) {
  if (value === "synthetic_v3") return "Sintético V3";
  if (value === "analytic_expanded_v3") return "Analítico Expandido V3";
  if (value === "executive_consolidated_v3") return "Executivo Consolidado V3";
  return value;
}

function formatDate(value?: string) {
  if (!value) return "-";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString("pt-BR");
}

function formatSize(value?: number) {
  if (!value) return "-";
  if (value < 1024) return `${value} B`;
  return `${(value / 1024).toFixed(1)} KB`;
}

function isRecentReport(value?: string) {
  if (!value) return false;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return false;
  const diffMs = Date.now() - d.getTime();
  return diffMs >= 0 && diffMs <= 48 * 60 * 60 * 1000;
}

function formatFilters(filters?: Record<string, string>) {
  if (!filters) return "Sem filtros";
  const parts = Object.entries(filters)
    .filter(([, v]) => v)
    .map(([k, v]) => `${k}: ${v}`);
  return parts.length ? parts.join(" · ") : "Sem filtros";
}

export default function ReportsHistoryPage() {
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);
  const [family, setFamily] = useState(() => initialSearchParam("report_family"));
  const [type, setType] = useState(() => initialSearchParam("report_type"));
  const [dateFrom, setDateFrom] = useState(() => initialSearchParam("date_from"));
  const [dateTo, setDateTo] = useState(() => initialSearchParam("date_to"));
  const [items, setItems] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function loadHistory() {
    setLoading(true);
    setMessage("");

    try {
      const params = new URLSearchParams();
      params.set("limit", "50");
      if (family) params.set("report_family", family);
      if (type) params.set("report_type", type);
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);

      const res = await adminFetch(`${API_BASE}/reports/history/${projectId}?${params.toString()}`, {
        cache: "no-store",
      });

      if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);

      const data = await res.json();
      setItems(data.items || []);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao carregar histórico.");
    } finally {
      setLoading(false);
    }
  }

  async function openReport(item: ReportItem) {
    setMessage("");
    if (!item.public_url) {
      setMessage("Link público do relatório não disponível.");
      return;
    }
    window.open(item.public_url, "_blank", "noopener,noreferrer");
  }

  async function downloadReport(item: ReportItem) {
    setMessage("");

    try {
      const res = await adminFetch(`${API_BASE}/reports/history/download/${item.id}`, {
        cache: "no-store",
      });

      if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = item.filename || "relatorio.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao baixar relatório.");
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  const socialReports = items.filter((item) => item.report_family === "social").length;
  const latestReport = items[0];
  const totalSize = items.reduce((acc, item) => acc + Number(item.file_size || 0), 0);

  const historyKpis = [
    { label: "Relatórios no recorte", value: items.length },
    { label: "Relatórios Social Monitor", value: socialReports },
    { label: "Último tipo gerado", value: latestReport ? labelType(latestReport.report_type) : "-" },
    { label: "Volume armazenado", value: formatSize(totalSize) },
  ];

  return (
    <AppShell
      title="Histórico de Relatórios V3"
      subtitle="Consulta e download dos relatórios Premium V3 gerados automaticamente."
    >
      <div style={{ display: "grid", gap: 18 }}>
        <section style={{ background: "#fff", borderRadius: 18, padding: 20, border: "1px solid #e5e7eb" }}>
          <h3 style={{ margin: "0 0 14px", color: "#111827" }}>Resumo executivo do histórico</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12 }}>
            {historyKpis.map((kpi) => (
              <div key={kpi.label} style={{ border: "1px solid #eef2f7", borderRadius: 14, padding: 14, background: "#f8fafc" }}>
                <div style={{ fontSize: 22, fontWeight: 900, color: "#C52625" }}>{kpi.value}</div>
                <div style={{ fontSize: 12, color: "#667085", fontWeight: 700 }}>{kpi.label}</div>
              </div>
            ))}
          </div>
        </section>

          {latestReport ? (
            <section style={{ background: "#fff", borderRadius: 18, padding: 20, border: "1px solid #e5e7eb" }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
                <div>
                  <h3 style={{ margin: "0 0 8px", color: "#111827" }}>Último relatório gerado</h3>
                  <div style={{ fontSize: 13, color: "#667085", fontWeight: 700 }}>{labelFamily(latestReport.report_family)} · {labelType(latestReport.report_type)}</div>
                  <div style={{ marginTop: 6, fontSize: 13, color: "#344054", fontWeight: 800 }}>{latestReport.filename}</div>
                  <div style={{ marginTop: 4, fontSize: 12, color: "#667085" }}>{formatDate(latestReport.created_at)}</div>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button onClick={() => downloadReport(latestReport)} style={downloadButtonStyle}>Baixar PDF</button>
                  <button onClick={() => openReport(latestReport)} style={openButtonStyle}>Abrir</button>
                </div>
              </div>
            </section>
          ) : null}

        <section style={{ background: "#fff", borderRadius: 18, padding: 20, border: "1px solid #e5e7eb" }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
            <span style={{ fontSize: 13, fontWeight: 800, color: "#344054", alignSelf: "center" }}>Filtros rápidos:</span>
            <button onClick={() => { setFamily(""); setType(""); }} style={quickButtonStyle}>Todos</button>
            <button onClick={() => { setFamily("editorial"); setType(""); }} style={quickButtonStyle}>Editorial</button>
            <button onClick={() => { setFamily("editorial_social"); setType(""); }} style={quickButtonStyle}>Editorial + Social</button>
            <button onClick={() => { setFamily("social"); setType("executive_consolidated_v3"); }} style={quickButtonStyle}>Social Monitor</button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr auto", gap: 12, alignItems: "end" }}>
            <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 700 }}>
              Projeto
              <input value={projectId} onChange={(e) => setProjectId(e.target.value)} style={{ padding: 10, borderRadius: 10, border: "1px solid #d0d5dd" }} />
            </label>

            <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 700 }}>
              Família
              <select value={family} onChange={(e) => setFamily(e.target.value)} style={{ padding: 10, borderRadius: 10, border: "1px solid #d0d5dd" }}>
                <option value="">Todas</option>
                <option value="editorial">Editorial</option>
                <option value="editorial_social">Editorial + Social</option>
                  <option value="social">Social Monitor</option>
              </select>
            </label>

            <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 700 }}>
              Tipo
              <select value={type} onChange={(e) => setType(e.target.value)} style={{ padding: 10, borderRadius: 10, border: "1px solid #d0d5dd" }}>
                <option value="">Todos</option>
                <option value="synthetic_v3">Sintético V3</option>
                <option value="analytic_expanded_v3">Analítico Expandido V3</option>
                  <option value="executive_consolidated_v3">Executivo Consolidado V3</option>
              </select>
            </label>

              <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 700 }}>
                Data inicial
                <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} style={{ padding: 10, borderRadius: 10, border: "1px solid #d0d5dd" }} />
              </label>

              <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 700 }}>
                Data final
                <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} style={{ padding: 10, borderRadius: 10, border: "1px solid #d0d5dd" }} />
              </label>

            <button onClick={loadHistory} disabled={loading} style={{ padding: "11px 16px", borderRadius: 10, border: "none", background: "#C52625", color: "#fff", fontWeight: 800 }}>
              {loading ? "Carregando..." : "Filtrar"}
            </button>
          </div>

          {message ? <p style={{ color: "#b42318", fontWeight: 700 }}>{message}</p> : null}

          <p style={{ color: "#667085" }}>
            {items.length} relatório(s) encontrado(s).
          </p>
        </section>

        <section style={{ background: "#fff", borderRadius: 18, padding: 20, border: "1px solid #e5e7eb", overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr>
                <th style={th}>Gerado em</th>
                <th style={th}>Família</th>
                <th style={th}>Tipo</th>
                <th style={th}>Arquivo</th>
                <th style={th}>Tamanho</th>
                <th style={th}>Filtros</th>
                <th style={th}>Download</th>
              </tr>
            </thead>

            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                    <td style={td}>
                      <div>{formatDate(item.created_at)}</div>
                      {isRecentReport(item.created_at) ? <span style={recentBadgeStyle}>Recente</span> : null}
                    </td>
                  <td style={td}>{labelFamily(item.report_family)}</td>
                  <td style={td}>{labelType(item.report_type)}</td>
                  <td style={{ ...td, fontWeight: 700 }}>{item.filename}</td>
                  <td style={td}>{formatSize(item.file_size)}</td>
                  <td style={td}>{formatFilters(item.filters)}</td>
                    <td style={td}>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        <button onClick={() => downloadReport(item)} style={downloadButtonStyle}>
                          Baixar PDF
                        </button>
                        <button onClick={() => openReport(item)} style={openButtonStyle}>
                          Abrir
                        </button>
                      </div>
                    </td>
                </tr>
              ))}

              {!items.length ? (
                <tr>
                  <td colSpan={7} style={{ ...td, textAlign: "center", color: "#667085" }}>
                    Nenhum relatório encontrado.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </section>
      </div>
    </AppShell>
  );
}

const th = {
  textAlign: "left" as const,
  padding: 10,
  borderBottom: "1px solid #e5e7eb",
  background: "#f8fafc",
  color: "#475467",
};

const td = {
  padding: 10,
  borderBottom: "1px solid #eef2f7",
  verticalAlign: "top" as const,
  color: "#344054",
};

const quickButtonStyle = {
  border: "1px solid #d0d5dd",
  background: "#fff",
  color: "#344054",
  borderRadius: 999,
  padding: "8px 12px",
  fontWeight: 800,
  cursor: "pointer",
};


const recentBadgeStyle = {
  display: "inline-block",
  marginTop: 6,
  background: "#ecfdf3",
  color: "#027a48",
  border: "1px solid #abefc6",
  borderRadius: 999,
  padding: "3px 8px",
  fontSize: 11,
  fontWeight: 900,
};

const downloadButtonStyle = {
  border: "1px solid #C52625",
  color: "#C52625",
  background: "#fff",
  borderRadius: 10,
  padding: "8px 10px",
  fontWeight: 800,
  cursor: "pointer",
};

const openButtonStyle = {
  border: "1px solid #475467",
  color: "#fff",
  background: "#475467",
  borderRadius: 10,
  padding: "8px 10px",
  fontWeight: 800,
  cursor: "pointer",
};
