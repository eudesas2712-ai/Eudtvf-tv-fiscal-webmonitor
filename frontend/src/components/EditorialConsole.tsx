"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { adminFetch, adminJson, API_BASE, ADMIN_TOKEN_KEY } from "../lib/apiClient";

const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

function getAuthHeaders(extra?: Record<string, string>): Record<string, string> {
  if (typeof window === "undefined") return extra || {};
  const bearer = localStorage.getItem("tvfiscal_auth_token") || "";
  const adminToken = localStorage.getItem(ADMIN_TOKEN_KEY) || "";
  return {
    ...(bearer ? { Authorization: `Bearer ${bearer}` } : {}),
    ...(extra || {}),
  };
}

async function fetchJson<T>(url: string): Promise<T> {
  return adminJson<T>(url, {
    bearer: false,
    admin: true,
    json: true,
  });
}


async function fetchWithAuth(url: string, init: RequestInit = {}) {
  return adminFetch(url, {
    ...init,
    bearer: false,
    admin: true,
    json: false,
  });
}


function getProjectIdFromUrl() {
  if (typeof window === "undefined") return DEFAULT_PROJECT_ID;
  return new URLSearchParams(window.location.search).get("project_id") || DEFAULT_PROJECT_ID;
}

function formatDate(value?: string | null) {
  if (!value) return "Sem data";
  const normalized = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value) && !value.endsWith("Z") && !value.includes("+") ? `${value}Z` : value;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("pt-BR");
}

function sentimentLabel(value?: string | null) {
  const raw = String(value || "neutro").toLowerCase();
  if (raw === "positivo") return "Positivo";
  if (raw === "negativo") return "Negativo";
  return "Neutro";
}

function sentimentStyle(value?: string | null): CSSProperties {
  const raw = String(value || "neutro").toLowerCase();
  if (raw === "positivo") return { background: "#dcfce7", color: "#166534" };
  if (raw === "negativo") return { background: "#fee2e2", color: "#991b1b" };
  return { background: "#e0f2fe", color: "#075985" };
}

function makeQuery(filters: Record<string, string>) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  return params.toString();
}

export default function EditorialConsole() {
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);
  const [items, setItems] = useState<EditorialItem[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [reclassifying, setReclassifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<EditorialItem | null>(null);
  const [token, setToken] = useState("");
  const [filters, setFilters] = useState({ q: "", source_name: "", term: "", sentiment: "", topic: "", date_from: "", date_to: "" });

  useEffect(() => {
    const id = getProjectIdFromUrl();
    setProjectId(id);
    const saved = localStorage.getItem(ADMIN_TOKEN_KEY) || "";
    setToken(saved);
  }, []);

  const sourceOptions = useMemo(() => Array.from(new Set(items.map((item) => item.source_name || "").filter(Boolean))).sort(), [items]);
  const topicOptions = useMemo(() => Array.from(new Set(items.map((item) => item.topic || "").filter(Boolean))).sort(), [items]);
  const termOptions = useMemo(() => {
    const set = new Set<string>();
    for (const item of items) for (const term of item.matched_terms?.terms || []) set.add(term);
    return Array.from(set).sort();
  }, [items]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const query = makeQuery({ ...filters, limit: "80" });
      const [loadedItems, loadedSummary] = await Promise.all([
        fetchJson<EditorialItem[]>(`${API_BASE}/editorial/items/${projectId}${query ? `?${query}` : ""}`),
        fetchJson<Summary>(`${API_BASE}/editorial/summary/${projectId}${reportQuery ? `?${reportQuery}` : ""}`),
      ]);
      setItems(Array.isArray(loadedItems) ? loadedItems : []);
      setSummary(loadedSummary);
    } catch (err) {
      setError(err instanceof TypeError ? "Falha ao conectar ao backend na porta 8000. Verifique se o container backend está rodando." : err instanceof Error ? err.message : "Erro ao carregar dados.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (projectId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function runScan() {
    if (!token.trim()) {
      setError("Informe o token administrativo para executar a coleta editorial.");
      return;
    }
    setRunning(true);
    setError(null);
    try {
      localStorage.setItem(ADMIN_TOKEN_KEY, token.trim());
      const response = await fetchWithAuth(`${API_BASE}/editorial/run/${projectId}?collect_all=true&limit_per_source=25`, {
        method: "POST",
      });
      if (!response.ok) throw new Error(`Falha ao executar coleta editorial: ${response.status}`);
      await load();
    } catch (err) {
      setError(err instanceof TypeError ? "Falha ao conectar ao backend na porta 8000. Verifique se o container backend está rodando." : err instanceof Error ? err.message : "Erro ao executar coleta editorial.");
    } finally {
      setRunning(false);
    }
  }

  async function reclassifyEditorialQuality() {
    if (!token.trim()) {
      setError("Informe o token administrativo para reprocessar a qualidade editorial.");
      return;
    }
    setReclassifying(true);
    setError(null);
    try {
      localStorage.setItem(ADMIN_TOKEN_KEY, token.trim());
      const response = await fetchWithAuth(`${API_BASE}/editorial/reclassify/${projectId}?delete_listing_pages=true`, {
        method: "POST",
      });
      if (!response.ok) throw new Error(`Falha ao reprocessar qualidade editorial: ${response.status}`);
      await load();
    } catch (err) {
      setError(err instanceof TypeError ? "Falha ao conectar ao backend na porta 8000. Verifique se o container backend está rodando." : err instanceof Error ? err.message : "Erro ao reprocessar qualidade editorial.");
    } finally {
      setReclassifying(false);
    }
  }

  const reportQuery = makeQuery(filters);
  const pdfUrl = `${API_BASE}/editorial/report-pdf/${projectId}${reportQuery ? `?${reportQuery}` : ""}`;
  const syntheticPdfUrl = `${API_BASE}/editorial/report-sintetico-pdf/${projectId}${reportQuery ? `?${reportQuery}` : ""}`;
  const analyticalPdfUrl = `${API_BASE}/editorial/report-analitico-pdf/${projectId}${reportQuery ? `?${reportQuery}` : ""}`;
  const syntheticV3PdfUrl = `${API_BASE}/editorial/reports/synthetic-v3/${projectId}${reportQuery ? `?${reportQuery}` : ""}`;
  const analyticalV3PdfUrl = `${API_BASE}/editorial/reports/analytic-expanded-v3/${projectId}${reportQuery ? `?${reportQuery}` : ""}`;
  const syntheticSocialV3PdfUrl = `${API_BASE}/editorial-social/reports/synthetic-v3/${projectId}${reportQuery ? `?${reportQuery}` : ""}`;
  const analyticalSocialV3PdfUrl = `${API_BASE}/editorial-social/reports/analytic-expanded-v3/${projectId}${reportQuery ? `?${reportQuery}` : ""}`;

  async function openReport(url: string, fallbackName: string) {
    setError(null);
    try {
      const response = await fetchWithAuth(url);
      if (!response.ok) throw new Error(`Falha ao gerar relatório editorial: ${response.status}`);
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.target = "_blank";
      a.rel = "noreferrer";
      a.download = fallbackName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    } catch (err) {
      setError(err instanceof TypeError ? "Falha ao conectar ao backend na porta 8000. Verifique se o container backend está rodando." : err instanceof Error ? err.message : "Erro ao gerar relatório editorial.");
    }
  }

  function formatDateInputBR(value: string) {
    if (!value) return "";
    const parts = value.split("-");
    if (parts.length !== 3) return value;
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }

  function currentEditorialFilterSummary() {
    const parts = [];
    if (filters.q.trim()) parts.push(`Busca: ${filters.q.trim()}`);
    if (filters.source_name) parts.push(`Fonte: ${filters.source_name}`);
    if (filters.term) parts.push(`Termo: ${filters.term}`);
    if (filters.sentiment) parts.push(`Sentimento: ${sentimentLabel(filters.sentiment)}`);
    if (filters.topic) parts.push(`Tema: ${filters.topic}`);
    if (filters.date_from || filters.date_to) {
      parts.push(`Período: ${filters.date_from ? formatDateInputBR(filters.date_from) : "início"} a ${filters.date_to ? formatDateInputBR(filters.date_to) : "hoje"}`);
    }
    if (parts.length === 0) {
      return "Recorte atual: geral, todas as fontes, sem termo, sentimento, tema ou período restrito.";
    }
    return `Recorte atual: ${parts.join(" · ")}`;
  }

  return (
    <div style={{ display: "grid", gap: 22 }}>
      <section style={heroStyle}>
        <div>
          <div style={{ color: "#b00020", fontWeight: 800, fontSize: 13, letterSpacing: 1, textTransform: "uppercase" }}>Editorial Intelligence</div>
          <h2 style={{ margin: "8px 0", fontSize: 30 }}>Monitoramento de notícias e menções</h2>
          <p style={{ color: "#64748b", maxWidth: 860, lineHeight: 1.55 }}>
            Coleta matérias dos portais vinculados ao projeto, identifica termos, clientes/anunciantes cadastrados, tema editorial e sentimento básico para clipping eletrônico.
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <input value={token} onChange={(e) => setToken(e.target.value)} placeholder="Token admin" style={inputStyle} />
          <button onClick={runScan} disabled={running} style={primaryButtonStyle}>{running ? "Coletando..." : "Coletar notícias agora"}</button>
          <button onClick={reclassifyEditorialQuality} disabled={reclassifying} style={secondaryButtonStyle}>{reclassifying ? "Reprocessando..." : "Reprocessar qualidade"}</button>
          <button onClick={() => openReport(pdfUrl, "relatorio_editorial.pdf")} style={secondaryButtonStyle}>PDF editorial simples</button>
          <button onClick={() => openReport(syntheticPdfUrl, "editorial_sintetico.pdf")} style={secondaryButtonStyle}>Sintético executivo</button>
          <button onClick={() => openReport(analyticalPdfUrl, "editorial_analitico.pdf")} style={secondaryButtonStyle}>Analítico expandido</button>
        </div>
      </section>

      {error ? <div style={errorStyle}>{error}</div> : null}

      <div style={{ background: "#fff7ed", border: "1px solid #fed7aa", color: "#9a3412", borderRadius: 14, padding: "12px 14px", fontSize: 13, lineHeight: 1.45 }}>
        Qualidade editorial ativa: termos e marcas são detectados por palavra/frase completa, reduzindo falsos positivos como “Amil” dentro de outras palavras. Páginas de categoria/listagem são filtradas. Os novos relatórios seguem o padrão SmartReport: sintético executivo com dashboard e analítico expandido com clipping, transcrição possível e amostras de evidência.
      </div>

      <section style={{ background: "#ffffff", border: "1px solid #e2e8f0", borderRadius: 18, padding: 18, boxShadow: "0 12px 30px rgba(15, 23, 42, 0.06)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 14, flexWrap: "wrap", alignItems: "center" }}>
          <div>
            <div style={{ color: "#b00020", fontWeight: 900, fontSize: 12, letterSpacing: 1, textTransform: "uppercase" }}>
              Relatórios Editorial Premium V3
            </div>
            <h3 style={{ margin: "6px 0 4px", fontSize: 22, color: "#0f172a" }}>
              Padrão executivo TV Fiscal
            </h3>
            <p style={{ margin: 0, color: "#64748b", fontSize: 13, lineHeight: 1.45 }}>
              Geração dos modelos Sintético Executivo Premium V3 e Analítico Executivo Expandido Premium V3, usando os filtros do recorte atual.
            </p>
          </div>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              onClick={() => openReport(syntheticV3PdfUrl, `EDITORIAL_SINTETICO_EXECUTIVO_PREMIUM_V3_${projectId}.pdf`)}
              style={{ ...primaryButtonStyle, background: "#b00020" }}
            >
              Sintético Executivo Premium V3
            </button>

            <button
              onClick={() => openReport(analyticalV3PdfUrl, `EDITORIAL_ANALITICO_EXECUTIVO_EXPANDIDO_PREMIUM_V3_${projectId}.pdf`)}
              style={{ ...secondaryButtonStyle, borderColor: "#b00020", color: "#b00020" }}
            >
              Analítico Executivo Expandido V3
            </button>

              <button
                onClick={() => openReport(syntheticSocialV3PdfUrl, `EDITORIAL_SOCIAL_SINTETICO_PREMIUM_V3_${projectId}.pdf`)}
                style={{ ...secondaryButtonStyle, borderColor: "#7c3aed", color: "#7c3aed" }}
              >
                Sintético Editorial + Social V3
              </button>

              <button
                onClick={() => openReport(analyticalSocialV3PdfUrl, `EDITORIAL_SOCIAL_ANALITICO_PREMIUM_V3_${projectId}.pdf`)}
                style={{ ...secondaryButtonStyle, borderColor: "#7c3aed", color: "#7c3aed" }}
              >
                Analítico Editorial + Social V3
              </button>

                          <button
            onClick={() => {
              openReport(syntheticV3PdfUrl, `EDITORIAL_SINTETICO_EXECUTIVO_PREMIUM_V3_${projectId}.pdf`);
              setTimeout(() => openReport(analyticalV3PdfUrl, `EDITORIAL_ANALITICO_EXECUTIVO_EXPANDIDO_PREMIUM_V3_${projectId}.pdf`), 900);
              setTimeout(() => openReport(syntheticSocialV3PdfUrl, `EDITORIAL_SOCIAL_SINTETICO_PREMIUM_V3_${projectId}.pdf`), 1800);
              setTimeout(() => openReport(analyticalSocialV3PdfUrl, `EDITORIAL_SOCIAL_ANALITICO_PREMIUM_V3_${projectId}.pdf`), 2700);
            }}
            style={secondaryButtonStyle}
          >
            Gerar pacote V3
          </button>
          </div>
        </div>
      </section>

      <section style={metricsGridStyle}>
        <Metric title="Matérias" value={summary?.total_items || 0} hint="Itens editoriais no recorte atual" />
        <Metric title="Termos detectados" value={summary?.total_terms || 0} hint="Menções a termos/marcas no recorte atual" />
        <Metric title="Fontes" value={summary?.sources_count || 0} hint="Fontes presentes no recorte atual" />
        <Metric title="Temas" value={summary?.topics_count || 0} hint="Categorias editoriais no recorte atual" />
      </section>

      <section style={filterPanelStyle}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12 }}>
          <input placeholder="Buscar título, texto, termo..." value={filters.q} onChange={(e) => setFilters({ ...filters, q: e.target.value })} style={inputStyle} />
          <select value={filters.source_name} onChange={(e) => setFilters({ ...filters, source_name: e.target.value })} style={inputStyle}>
            <option value="">Todas as fontes</option>
            {sourceOptions.map((source) => <option key={source} value={source}>{source}</option>)}
          </select>
          <select value={filters.term} onChange={(e) => setFilters({ ...filters, term: e.target.value })} style={inputStyle}>
            <option value="">Todos os termos</option>
            {termOptions.map((term) => <option key={term} value={term}>{term}</option>)}
          </select>
          <select value={filters.sentiment} onChange={(e) => setFilters({ ...filters, sentiment: e.target.value })} style={inputStyle}>
            <option value="">Todos os sentimentos</option>
            <option value="positivo">Positivo</option>
            <option value="neutro">Neutro</option>
            <option value="negativo">Negativo</option>
          </select>
          <select value={filters.topic} onChange={(e) => setFilters({ ...filters, topic: e.target.value })} style={inputStyle}>
            <option value="">Todos os temas</option>
            {topicOptions.map((topic) => <option key={topic} value={topic}>{topic}</option>)}
          </select>
          <input type="date" value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} style={inputStyle} />
          <input type="date" value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} style={inputStyle} />
        </div>
        <div style={{ marginTop: 12, display: "flex", gap: 10 }}>
          <button onClick={load} disabled={loading} style={primaryButtonStyle}>{loading ? "Filtrando..." : "Aplicar filtros"}</button>
          <button onClick={() => setFilters({ q: "", source_name: "", term: "", sentiment: "", topic: "", date_from: "", date_to: "" })} style={ghostButtonStyle}>Limpar</button>
        </div>
          <p style={{ margin: "12px 0 0", color: "#0f172a", fontSize: 13, fontWeight: 800 }}>{currentEditorialFilterSummary()}</p>
      </section>

      <section style={{ display: "grid", gap: 14 }}>
        {items.length === 0 ? <div style={emptyStyle}>Nenhuma matéria encontrada para o recorte atual.</div> : null}
        {items.map((item) => (
          <article key={item.id} style={cardStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
              <div style={{ flex: "1 1 520px" }}>
                <h3 style={{ margin: "0 0 8px", fontSize: 19 }}>{item.title}</h3>
                <div style={{ color: "#64748b", fontSize: 13, marginBottom: 10 }}>
                  {item.source_name || "Fonte não identificada"} · {formatDate(item.created_at)} · Tema: {item.topic || "Geral"}
                </div>
                <p style={{ color: "#334155", lineHeight: 1.5, margin: 0 }}>{item.summary || "Sem resumo disponível."}</p>
              </div>
              <div style={{ display: "grid", gap: 8, minWidth: 180, alignContent: "start" }}>
                <span style={{ ...pillStyle, ...sentimentStyle(item.sentiment) }}>{sentimentLabel(item.sentiment)} · {item.sentiment_score || 0}</span>
                <span style={{ ...pillStyle, background: "#f1f5f9", color: "#334155" }}>Score editorial {item.editorial_score || 0}</span>
                <button onClick={() => setSelected(item)} style={smallButtonStyle}>Detalhar</button>
                <a href={item.url} target="_blank" rel="noreferrer" style={smallLinkStyle}>Página original</a>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
              {(item.matched_terms?.terms || []).map((term) => <span key={term} style={termPillStyle}>{term}</span>)}
            </div>
          </article>
        ))}
      </section>

      {selected ? (
        <div style={modalBackdropStyle} onClick={() => setSelected(null)}>
          <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
            <button onClick={() => setSelected(null)} style={closeButtonStyle}>×</button>
            <h2 style={{ marginTop: 0 }}>{selected.title}</h2>
            <p style={{ color: "#64748b" }}>{selected.source_name} · {formatDate(selected.created_at)}</p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, margin: "16px 0" }}>
              <Info label="Tema" value={selected.topic || "Geral"} />
              <Info label="Sentimento" value={`${sentimentLabel(selected.sentiment)} (${selected.sentiment_score || 0})`} />
              <Info label="Score editorial" value={String(selected.editorial_score || 0)} />
              <Info label="Termos" value={(selected.matched_terms?.terms || []).join(", ") || "Nenhum"} />
            </div>
            <h3>Resumo</h3>
            <p style={{ lineHeight: 1.55 }}>{selected.summary || "Sem resumo."}</p>
            <h3>Texto capturado</h3>
            <div style={{ maxHeight: 260, overflow: "auto", background: "#f8fafc", padding: 14, borderRadius: 12, color: "#334155", lineHeight: 1.55 }}>
              {selected.content_text || "Sem texto capturado."}
            </div>
            <div style={{ marginTop: 18, display: "flex", gap: 10, flexWrap: "wrap" }}>
              <a href={selected.url} target="_blank" rel="noreferrer" style={primaryLinkStyle}>Abrir matéria original</a>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Metric({ title, value, hint }: { title: string; value: string | number; hint: string }) {
  return <div style={metricStyle}><div style={{ color: "#64748b", fontWeight: 700, fontSize: 13 }}>{title}</div><div style={{ color: "#b00020", fontSize: 34, fontWeight: 900, marginTop: 8 }}>{value}</div><div style={{ color: "#94a3b8", fontSize: 12, marginTop: 6 }}>{hint}</div></div>;
}

function Info({ label, value }: { label: string; value: string }) {
  return <div style={{ background: "#f8fafc", borderRadius: 12, padding: 12 }}><div style={{ fontSize: 12, color: "#64748b", fontWeight: 700 }}>{label}</div><div style={{ fontWeight: 800, marginTop: 4 }}>{value}</div></div>;
}

const heroStyle: CSSProperties = { background: "#fff", borderRadius: 22, padding: 24, boxShadow: "0 10px 28px rgba(15,23,42,0.08)", display: "flex", justifyContent: "space-between", gap: 18, flexWrap: "wrap", alignItems: "center" };
const metricsGridStyle: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 14 };
const metricStyle: CSSProperties = { background: "#fff", borderRadius: 18, padding: 18, boxShadow: "0 8px 22px rgba(15,23,42,0.07)", borderLeft: "5px solid #b00020" };
const filterPanelStyle: CSSProperties = { background: "#fff", borderRadius: 18, padding: 18, boxShadow: "0 8px 22px rgba(15,23,42,0.07)" };
const inputStyle: CSSProperties = { border: "1px solid #cbd5e1", borderRadius: 10, padding: "11px 12px", color: "#111827", background: "#fff", WebkitTextFillColor: "#111827", colorScheme: "light" };
const primaryButtonStyle: CSSProperties = { border: 0, borderRadius: 10, padding: "11px 15px", background: "#b00020", color: "#fff", fontWeight: 800, cursor: "pointer" };
const secondaryButtonStyle: CSSProperties = { border: 0, borderRadius: 10, padding: "11px 15px", background: "#1f4e79", color: "#fff", fontWeight: 800, textDecoration: "none", cursor: "pointer" };
const ghostButtonStyle: CSSProperties = { border: "1px solid #cbd5e1", borderRadius: 10, padding: "11px 15px", background: "#fff", color: "#334155", fontWeight: 800, cursor: "pointer" };
const cardStyle: CSSProperties = { background: "#fff", borderRadius: 18, padding: 18, boxShadow: "0 8px 22px rgba(15,23,42,0.07)", borderLeft: "5px solid #1f4e79" };
const pillStyle: CSSProperties = { display: "inline-flex", alignItems: "center", justifyContent: "center", borderRadius: 999, padding: "7px 10px", fontSize: 12, fontWeight: 800 };
const termPillStyle: CSSProperties = { ...pillStyle, background: "#fef3c7", color: "#92400e" };
const smallButtonStyle: CSSProperties = { border: 0, borderRadius: 9, padding: "9px 10px", background: "#111827", color: "#fff", fontWeight: 800, cursor: "pointer" };
const smallLinkStyle: CSSProperties = { borderRadius: 9, padding: "9px 10px", background: "#e0f2fe", color: "#075985", fontWeight: 800, textDecoration: "none", textAlign: "center" };
const primaryLinkStyle: CSSProperties = { borderRadius: 10, padding: "11px 15px", background: "#b00020", color: "#fff", fontWeight: 800, textDecoration: "none" };
const errorStyle: CSSProperties = { background: "#fee2e2", color: "#991b1b", borderRadius: 12, padding: 14, fontWeight: 700 };
const emptyStyle: CSSProperties = { background: "#fff", color: "#64748b", borderRadius: 14, padding: 24, textAlign: "center" };
const modalBackdropStyle: CSSProperties = { position: "fixed", inset: 0, background: "rgba(15,23,42,0.62)", zIndex: 50, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 };
const modalStyle: CSSProperties = { background: "#fff", color: "#111827", borderRadius: 22, padding: 24, width: "min(980px, 96vw)", maxHeight: "90vh", overflow: "auto", position: "relative", boxShadow: "0 24px 70px rgba(0,0,0,0.35)" };
const closeButtonStyle: CSSProperties = { position: "absolute", right: 16, top: 12, border: 0, background: "transparent", fontSize: 28, cursor: "pointer" };
