"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";

const API =
  (process.env.NEXT_PUBLIC_API_BASE ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000").replace(/\/$/, "");
const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

function getLocalAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "X-Admin-Token": "tvfiscal-admin-2026",
  };

  if (typeof window !== "undefined") {
    const token =
      localStorage.getItem("tvfiscal_auth_token") ||
      localStorage.getItem("auth_token") ||
      localStorage.getItem("access_token") ||
      localStorage.getItem("token");

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  return headers;
}

async function authorizedFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const headers = new Headers(init.headers || undefined);

  for (const [key, value] of Object.entries(getLocalAuthHeaders())) {
    headers.set(key, value);
  }

  return fetch(input, {
    ...init,
    headers,
    cache: init.cache || "no-store",
  });
}

async function downloadWithAuth(url: string, filenameFallback: string) {
  const res = await authorizedFetch(url);

  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`Erro ao gerar arquivo: ${res.status} ${msg || res.statusText}`);
  }

  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") || "";
  const match = cd.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
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

function getProjectIdFromUrl() {
  if (typeof window === "undefined") return DEFAULT_PROJECT_ID;
  const value = new URLSearchParams(window.location.search).get("project_id");
  return value || DEFAULT_PROJECT_ID;
}

type Segment = { id: string; name: string };
type Advertiser = { id: string; name: string; segment_id?: string | null; segment_name?: string | null };

type CompareAdvertiser = {
  advertiser_id: string;
  advertiser: string;
  segment_name?: string | null;
  items: number;
  auditables: number;
  review_items: number;
  rejected_items: number;
  news_candidates: number;
  investment: number;
  share_count_percent: number;
  share_investment_percent: number;
  avg_publicity_score: number;
  avg_market_score: number;
  avg_visibility_score: number;
  portals: { portal: string; items: number }[];
  formats: { format: string; items: number }[];
  latest_evidences: any[];
  daily_timeline: { date: string; items: number; investment: number }[];
  strength_score: number;
};

function formatBRL(value: any) {
  return Number(value || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

function formatPct(value: any) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function shortDate(value: any) {
  if (!value) return "";
  const d = new Date(`${value}T00:00:00`);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

function MetricCard({ title, value, hint }: { title: string; value: string | number; hint?: string }) {
  return (
    <div style={metricCardStyle}>
      <div style={{ fontSize: 13, color: "#68707f", fontWeight: 700 }}>{title}</div>
      <div style={{ fontSize: 32, color: "#b00020", fontWeight: 900, marginTop: 8 }}>{value}</div>
      {hint ? <div style={{ fontSize: 12, color: "#7b8290", marginTop: 8 }}>{hint}</div> : null}
    </div>
  );
}

function ProgressBar({ value, max = 100 }: { value: number; max?: number }) {
  const pct = max ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <div style={{ background: "#eef1f6", height: 9, borderRadius: 999, overflow: "hidden" }}>
      <div style={{ width: `${pct}%`, height: "100%", background: "#b00020" }} />
    </div>
  );
}

function Badge({ children, tone = "gray" }: { children: React.ReactNode; tone?: "green" | "blue" | "red" | "gray" | "purple" }) {
  const palette: Record<string, string> = {
    green: "#198754",
    blue: "#0d6efd",
    red: "#b00020",
    purple: "#6f42c1",
    gray: "#6c757d",
  };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "5px 8px",
        borderRadius: 999,
        background: palette[tone],
        color: "#fff",
        fontWeight: 800,
        fontSize: 12,
      }}
    >
      {children}
    </span>
  );
}

function EvidenceThumb({ item }: { item: any }) {
  const src = item.screenshot_banner_url || item.image_url || item.screenshot_page_url;
  const url = item.screenshot_banner_url || item.evidence_html_url || item.image_url || item.page_url;
  return (
    <a
      href={url || "#"}
      target="_blank"
      rel="noreferrer"
      style={{
        display: "grid",
        gridTemplateColumns: "70px 1fr",
        gap: 10,
        alignItems: "center",
        color: "inherit",
        textDecoration: "none",
        border: "1px solid #eceff4",
        borderRadius: 12,
        padding: 8,
        background: "#fafbfe",
      }}
    >
      {src ? (
        <img
          src={src}
          alt={item.advertiser_name || "Evidência"}
          style={{ width: 70, height: 52, objectFit: "cover", borderRadius: 8, background: "#eee" }}
        />
      ) : (
        <div style={{ width: 70, height: 52, borderRadius: 8, background: "#e9edf4" }} />
      )}
      <div style={{ minWidth: 0 }}>
        <div style={{ fontWeight: 800, color: "#303846", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          {item.source_name || "Portal não informado"}
        </div>
        <div style={{ fontSize: 12, color: "#68707f" }}>
          {item.format} · {formatBRL(item.estimated_value)} · score {item.publicity_score || 0}
        </div>
      </div>
    </a>
  );
}

export default function IntelComparativoPage() {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [advertisers, setAdvertisers] = useState<Advertiser[]>([]);
  const [selectedSegment, setSelectedSegment] = useState("");
  const [selectedAdvertisers, setSelectedAdvertisers] = useState<string[]>([]);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [evidenceScope, setEvidenceScope] = useState("market");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);

  useEffect(() => {
    setProjectId(getProjectIdFromUrl());
  }, []);

  const filteredAdvertisers = useMemo(() => {
    if (!selectedSegment) return advertisers;
    return advertisers.filter((item) => item.segment_id === selectedSegment);
  }, [advertisers, selectedSegment]);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (selectedSegment) params.set("segment_id", selectedSegment);
      if (selectedAdvertisers.length) params.set("advertiser_ids", selectedAdvertisers.join(","));
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      if (evidenceScope) params.set("evidence_scope", evidenceScope);

      const compareRes = await authorizedFetch(`${API}/intel/compare/${projectId}?${params.toString()}`);
      if (!compareRes.ok) throw new Error(await compareRes.text());
      setData(await compareRes.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar comparativo.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function loadRegistry() {
      const [segmentsRes, advertisersRes] = await Promise.all([
        authorizedFetch(`${API}/registry/segments`),
        authorizedFetch(`${API}/registry/advertisers`),
      ]);
      if (segmentsRes.ok) setSegments(await segmentsRes.json());
      if (advertisersRes.ok) setAdvertisers(await advertisersRes.json());
    }
    loadRegistry();
  }, []);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSegment, selectedAdvertisers.join(","), dateFrom, dateTo, evidenceScope, projectId]);

  function toggleAdvertiser(id: string) {
    setSelectedAdvertisers((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id]
    );
  }

  function clearAdvertisers() {
    setSelectedAdvertisers([]);
  }

  function selectSegmentByName(name: string) {
    const seg = segments.find((item) => item.name.toLowerCase() === name.toLowerCase());
    if (seg) {
      setSelectedSegment(seg.id);
      setSelectedAdvertisers([]);
    }
  }

  const advertisersData: CompareAdvertiser[] = Array.isArray(data?.advertisers) ? data.advertisers : [];
  const maxInvestment = Math.max(...advertisersData.map((item) => item.investment || 0), 1);
  const maxStrength = Math.max(...advertisersData.map((item) => item.strength_score || 0), 1);

  const reportParams = new URLSearchParams();
  if (selectedSegment) reportParams.set("segment_id", selectedSegment);
  if (selectedAdvertisers.length) reportParams.set("advertiser_ids", selectedAdvertisers.join(","));
  if (dateFrom) reportParams.set("date_from", dateFrom);
  if (dateTo) reportParams.set("date_to", dateTo);
  if (evidenceScope) reportParams.set("evidence_scope", evidenceScope);
  const reportQuery = reportParams.toString() ? `?${reportParams.toString()}` : "";

  return (
    <AppShell
      title="Intel Comparativo"
      subtitle="Cruzamento competitivo por segmento, anunciante, portais, formatos, evidências e investimento estimado."
    >
      <section style={panelStyle}>
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 18 }}>
          <div>
            <h2 style={sectionTitle}>Filtros estratégicos</h2>
            <div style={filterGridStyle}>
              <label style={labelStyle}>
                Segmento
                <select
                  value={selectedSegment}
                  onChange={(event) => {
                    setSelectedSegment(event.target.value);
                    setSelectedAdvertisers([]);
                  }}
                  style={inputStyle}
                >
                  <option value="">Todos os segmentos</option>
                  {segments.map((segment) => (
                    <option key={segment.id} value={segment.id}>{segment.name}</option>
                  ))}
                </select>
              </label>
              <label style={labelStyle}>
                Data inicial
                <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} style={inputStyle} />
              </label>
              <label style={labelStyle}>
                Data final
                <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} style={inputStyle} />
              </label>
              <label style={labelStyle}>
                Modo de análise
                <select value={evidenceScope} onChange={(event) => setEvidenceScope(event.target.value)} style={inputStyle}>
                  <option value="market">Mercado amplo</option>
                  <option value="preserved">Somente com evidência preservada</option>
                  <option value="advertising">Somente publicidade classificada</option>
                  <option value="auditavel">Somente checking auditável</option>
                </select>
              </label>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 14 }}>
              {['Saúde', 'Telecom', 'Varejo', 'Bancos', 'Educação'].map((segment) => (
                <button key={segment} onClick={() => selectSegmentByName(segment)} style={quickButtonStyle}>{segment}</button>
              ))}
              <button onClick={() => { setSelectedSegment(''); setSelectedAdvertisers([]); }} style={quickButtonStyle}>Limpar</button>
            </div>
            <div style={{ marginTop: 12, fontSize: 12, color: "#68707f", lineHeight: 1.45 }}>
              <strong>Mercado amplo</strong> mostra presença referencial. Para checking comprovado, use <strong>Somente checking auditável</strong>.
            </div>
          </div>

          <div>
            <h2 style={sectionTitle}>Anunciantes</h2>
            <div style={{ maxHeight: 180, overflow: "auto", display: "grid", gap: 8, paddingRight: 4 }}>
              {filteredAdvertisers.map((advertiser) => (
                <label key={advertiser.id} style={checkStyle}>
                  <input
                    type="checkbox"
                    checked={selectedAdvertisers.includes(advertiser.id)}
                    onChange={() => toggleAdvertiser(advertiser.id)}
                  />
                  <span>{advertiser.name}</span>
                  {advertiser.segment_name ? <small style={{ color: "#777" }}>{advertiser.segment_name}</small> : null}
                </label>
              ))}
            </div>
            <button onClick={clearAdvertisers} style={{ ...quickButtonStyle, marginTop: 10 }}>Comparar todos do segmento</button>
          </div>
        </div>
      </section>

      <section style={{ ...panelStyle, display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h2 style={{ ...sectionTitle, marginBottom: 4 }}>Relatórios comparativos</h2>
          <div style={{ color: "#68707f", fontSize: 13 }}>Exporte o recorte atual com segmento, anunciantes e período selecionados.</div>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          <button
            onClick={() =>
              downloadWithAuth(
                `${API}/intel/compare/report/pptx/${projectId}${reportQuery}`,
                `intel_comparativo_${projectId}.pptx`
              ).catch((err) =>
                setError(err instanceof Error ? err.message : "Erro ao gerar PPTX comparativo.")
              )
            }
            style={{ ...quickButtonStyle, background: "#b00020", color: "#fff" }}
          >
            Gerar PPTX Comparativo
          </button>
          <button
            onClick={() =>
              downloadWithAuth(
                `${API}/intel/compare/report/pdf/${projectId}${reportQuery}`,
                `intel_comparativo_${projectId}.pdf`
              ).catch((err) =>
                setError(err instanceof Error ? err.message : "Erro ao gerar PDF comparativo.")
              )
            }
            style={{ ...quickButtonStyle, background: "#303846", color: "#fff" }}
          >
            Gerar PDF Comparativo
          </button>
        </div>
      </section>

      {loading ? <div style={panelStyle}>Carregando comparativo...</div> : null}
      {error ? <div style={{ ...panelStyle, color: "#b00020", fontWeight: 800 }}>{error}</div> : null}

      {data ? (
        <>
          {data.totals?.items > 0 && data.totals?.auditables === 0 ? (
            <section style={{ ...panelStyle, borderLeft: "5px solid #f0ad4e", background: "#fffaf0" }}>
              <h2 style={{ ...sectionTitle, marginBottom: 6 }}>Atenção: leitura referencial, não checking comprovado</h2>
              <div style={{ color: "#5f4b16", lineHeight: 1.5 }}>
                O recorte atual tem {data.totals?.items || 0} evidência(s) de mercado, mas nenhuma auditável para checking.
                Use o modo <strong>Somente checking auditável</strong> para relatórios de prova, ou mantenha <strong>Mercado amplo</strong> para análise competitiva referencial.
              </div>
            </section>
          ) : null}

          <section style={metricGridStyle}>
            <MetricCard title="Anunciantes comparados" value={data.totals?.advertisers || 0} hint="com registros ou cadastro selecionado" />
            <MetricCard title="Modo de análise" value={evidenceScope === "auditavel" ? "Checking" : evidenceScope === "preserved" ? "Preservado" : evidenceScope === "advertising" ? "Publicidade" : "Mercado"} hint="qualidade do dado usada no comparativo" />
            <MetricCard title="Evidências consideradas" value={data.totals?.items || 0} hint={evidenceScope === "market" ? "market_status = incluído" : "conforme modo selecionado"} />
            <MetricCard title="Investimento estimado" value={formatBRL(data.totals?.investment)} hint="baseado nos formatos capturados" />
            <MetricCard title="Auditáveis" value={data.totals?.auditables || 0} hint="prontos para checking" />
            <MetricCard title="Portais envolvidos" value={data.totals?.portals || 0} hint="capilaridade competitiva" />
          </section>

          <section style={panelStyle}>
            <h2 style={sectionTitle}>Insights competitivos</h2>
            <div style={{ display: "grid", gap: 10 }}>
              {(data.insights || []).map((item: string, index: number) => (
                <div key={index} style={insightStyle}>• {item}</div>
              ))}
            </div>
          </section>

          <section style={panelStyle}>
            <h2 style={sectionTitle}>Ranking comparativo</h2>
            <div style={{ overflowX: "auto" }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Anunciante</th>
                    <th style={thStyle}>Segmento</th>
                    <th style={thStyle}>Evidências</th>
                    <th style={thStyle}>Auditáveis</th>
                    <th style={thStyle}>Investimento</th>
                    <th style={thStyle}>Share</th>
                    <th style={thStyle}>Força</th>
                    <th style={thStyle}>Portais</th>
                  </tr>
                </thead>
                <tbody>
                  {advertisersData.map((item) => (
                    <tr key={item.advertiser_id}>
                      <td style={tdStyle}><strong>{item.advertiser}</strong></td>
                      <td style={tdStyle}>{item.segment_name || "—"}</td>
                      <td style={tdStyle}>{item.items}</td>
                      <td style={tdStyle}><Badge tone={item.auditables ? "green" : "gray"}>{item.auditables}</Badge></td>
                      <td style={tdStyle}>{formatBRL(item.investment)}</td>
                      <td style={tdStyle}>{formatPct(item.share_investment_percent)}</td>
                      <td style={tdStyle}>
                        <div style={{ minWidth: 110 }}>
                          <div style={{ fontWeight: 800 }}>{item.strength_score}</div>
                          <ProgressBar value={item.strength_score} max={maxStrength} />
                        </div>
                      </td>
                      <td style={tdStyle}>{item.portals.length}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(330px,1fr))", gap: 18 }}>
            {advertisersData.map((item) => (
              <div key={item.advertiser_id} style={panelStyle}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
                  <div>
                    <h2 style={{ ...sectionTitle, marginBottom: 4 }}>{item.advertiser}</h2>
                    <div style={{ color: "#68707f", fontSize: 13 }}>{item.segment_name || "Segmento não informado"}</div>
                  </div>
                  <Badge tone="red">{formatPct(item.share_investment_percent)}</Badge>
                </div>

                <div style={{ display: "grid", gap: 12, marginTop: 18 }}>
                  <div>
                    <div style={miniLabel}>Investimento</div>
                    <div style={{ fontWeight: 900, color: "#b00020", fontSize: 24 }}>{formatBRL(item.investment)}</div>
                    <ProgressBar value={item.investment} max={maxInvestment} />
                  </div>
                  <div style={smallGridStyle}>
                    <div><div style={miniLabel}>Evidências</div><strong>{item.items}</strong></div>
                    <div><div style={miniLabel}>Auditáveis</div><strong>{item.auditables}</strong></div>
                    <div><div style={miniLabel}>Score publicidade</div><strong>{item.avg_publicity_score}</strong></div>
                    <div><div style={miniLabel}>Score visibilidade</div><strong>{item.avg_visibility_score}</strong></div>
                  </div>
                </div>

                <h3 style={subTitle}>Portais</h3>
                <div style={{ display: "grid", gap: 8 }}>
                  {item.portals.slice(0, 5).map((portal) => (
                    <div key={portal.portal} style={rowBetweenStyle}>
                      <span>{portal.portal}</span><strong>{portal.items}</strong>
                    </div>
                  ))}
                  {!item.portals.length ? <div style={{ color: "#777" }}>Sem portais com evidência.</div> : null}
                </div>

                <h3 style={subTitle}>Formatos</h3>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {item.formats.slice(0, 6).map((fmt) => (
                    <Badge key={fmt.format} tone="blue">{fmt.format}: {fmt.items}</Badge>
                  ))}
                  {!item.formats.length ? <span style={{ color: "#777" }}>Sem formatos.</span> : null}
                </div>

                <h3 style={subTitle}>Últimas evidências</h3>
                <div style={{ display: "grid", gap: 8 }}>
                  {item.latest_evidences.slice(0, 4).map((evidence) => (
                    <EvidenceThumb key={evidence.id} item={evidence} />
                  ))}
                  {!item.latest_evidences.length ? <div style={{ color: "#777" }}>Sem evidências para exibir.</div> : null}
                </div>
              </div>
            ))}
          </section>

          <section style={panelStyle}>
            <h2 style={sectionTitle}>Matriz de confronto direto</h2>
            <div style={{ overflowX: "auto" }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Confronto</th>
                    <th style={thStyle}>Líder</th>
                    <th style={thStyle}>Equilíbrio</th>
                    <th style={thStyle}>Classificação</th>
                    <th style={thStyle}>Delta investimento</th>
                    <th style={thStyle}>Delta evidências</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.pairs || []).map((pair: any, index: number) => (
                    <tr key={`${pair.left}-${pair.right}-${index}`}>
                      <td style={tdStyle}><strong>{pair.left}</strong> x <strong>{pair.right}</strong></td>
                      <td style={tdStyle}>{pair.leader}</td>
                      <td style={tdStyle}>{pair.balance_score}</td>
                      <td style={tdStyle}>{pair.relation}</td>
                      <td style={tdStyle}>{formatBRL(pair.investment_delta)}</td>
                      <td style={tdStyle}>{pair.items_delta}</td>
                    </tr>
                  ))}
                  {!(data.pairs || []).length ? (
                    <tr><td style={tdStyle} colSpan={6}>Selecione ao menos dois anunciantes ou um segmento com mais de um anunciante.</td></tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>

          <section style={panelStyle}>
            <h2 style={sectionTitle}>Sobreposição de portais</h2>
            <div style={{ display: "grid", gap: 10 }}>
              {(data.portal_overlap || []).slice(0, 10).map((item: any, index: number) => (
                <div key={index} style={insightStyle}>
                  <strong>{item.left}</strong> x <strong>{item.right}</strong>: {item.count} portal(is) em comum — {item.common_portals.join(", ")}
                </div>
              ))}
              {!(data.portal_overlap || []).length ? <div style={{ color: "#777" }}>Sem sobreposição de portais nos filtros atuais.</div> : null}
            </div>
          </section>
        </>
      ) : null}
    </AppShell>
  );
}

const panelStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 18,
  padding: 22,
  boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
  marginBottom: 20,
};

const sectionTitle: React.CSSProperties = {
  margin: "0 0 14px",
  color: "#303846",
  fontSize: 20,
};

const subTitle: React.CSSProperties = {
  margin: "18px 0 10px",
  color: "#303846",
  fontSize: 15,
};

const filterGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))",
  gap: 12,
};

const labelStyle: React.CSSProperties = {
  display: "grid",
  gap: 6,
  color: "#505866",
  fontSize: 13,
  fontWeight: 800,
};

const inputStyle: React.CSSProperties = {
  border: "1px solid #d8dde8",
  borderRadius: 10,
  padding: "11px 12px",
  fontSize: 14,
  background: "#fff",
  color: "#111827",
  WebkitTextFillColor: "#111827",
  colorScheme: "light",
  appearance: "auto",
};

const quickButtonStyle: React.CSSProperties = {
  border: "none",
  borderRadius: 999,
  padding: "9px 13px",
  background: "#f1f3f8",
  color: "#303846",
  fontWeight: 800,
  cursor: "pointer",
};

const checkStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "18px 1fr auto",
  gap: 8,
  alignItems: "center",
  padding: 9,
  borderRadius: 10,
  background: "#f7f8fb",
  fontSize: 14,
};

const metricGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit,minmax(190px,1fr))",
  gap: 16,
  marginBottom: 20,
};

const metricCardStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 18,
  padding: 20,
  boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
};

const insightStyle: React.CSSProperties = {
  background: "#f8f9fc",
  borderLeft: "4px solid #b00020",
  padding: 12,
  borderRadius: 10,
  color: "#303846",
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 14,
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "12px 10px",
  background: "#f4f6fa",
  color: "#303846",
  borderBottom: "1px solid #e3e7ef",
  whiteSpace: "nowrap",
};

const tdStyle: React.CSSProperties = {
  padding: "12px 10px",
  borderBottom: "1px solid #edf0f5",
  verticalAlign: "top",
};

const smallGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(2,1fr)",
  gap: 10,
  background: "#f8f9fc",
  borderRadius: 12,
  padding: 12,
};

const miniLabel: React.CSSProperties = {
  color: "#68707f",
  fontSize: 12,
  fontWeight: 800,
  marginBottom: 4,
};

const rowBetweenStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: 12,
  borderBottom: "1px solid #eef1f6",
  paddingBottom: 6,
};
