"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import type { BannerItem } from "../lib/types";

const API_BASE =
  (process.env.NEXT_PUBLIC_API_BASE ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000").replace(/\/$/, "");

function getLocalAuthHeaders() {
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

const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

function getProjectIdFromUrl() {
  if (typeof window === "undefined") return DEFAULT_PROJECT_ID;
  const value = new URLSearchParams(window.location.search).get("project_id");
  return value || DEFAULT_PROJECT_ID;
}

type EvidenceItem = BannerItem & {
  id?: string;
  project_id?: string;
  normalized_width?: number | null;
  normalized_height?: number | null;
  estimated_value?: number | null;
  classification_reason?: string | null;
  detection_confidence?: string | null;
  detection_evidence?: string | null;
  evidence_html_url?: string | null;
  page_url?: string | null;
  created_at?: string | null;
  advertiser_registry_id?: string | null;
  advertiser_registry_name?: string | null;
  advertiser_alias_matched?: string | null;
  segment_id?: string | null;
  segment_name?: string | null;
  effective_advertiser_name?: string | null;
};

type RegistrySegment = { id: string; name: string };
type RegistryAdvertiser = { id: string; name: string; segment_id?: string | null; segment_name?: string | null };

type Filters = {
  q: string;
  usage: "all" | "checking" | "market" | "news" | "rejected";
  portal: string;
  contentType: string;
  checkingStatus: string;
  segmentId: string;
  advertiserId: string;
  preservedOnly: boolean;
  minPublicityScore: string;
  minNewsScore: string;
};

const initialFilters: Filters = {
  q: "",
  usage: "all",
  portal: "",
  contentType: "",
  checkingStatus: "",
  segmentId: "",
  advertiserId: "",
  preservedOnly: false,
  minPublicityScore: "",
  minNewsScore: "",
};

function normalize(value: unknown) {
  return String(value || "").trim().toLowerCase();
}

function formatDate(value?: string | null) {
  if (!value) return "Sem data";
  const normalized = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value) && !value.endsWith("Z") && !value.includes("+")
    ? `${value}Z`
    : value;
  const d = new Date(normalized);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString("pt-BR");
}

function formatBRL(value?: number | null) {
  return Number(value || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

function formatSize(item: EvidenceItem) {
  const width = item.width || item.normalized_width || 0;
  const height = item.height || item.normalized_height || 0;
  return width && height ? `${width} x ${height}` : "N/D";
}

function contentTypeLabel(value?: string | null) {
  const raw = normalize(value);
  if (raw === "advertising") return "Publicidade";
  if (raw === "news") return "Notícia";
  if (raw === "mixed") return "Misto";
  if (raw === "institutional") return "Institucional";
  return "Indefinido";
}

function checkingLabel(value?: string | null) {
  const raw = normalize(value);
  if (raw === "auditavel") return "Auditável";
  if (raw === "parcial") return "Parcial";
  if (raw === "revisao") return "Revisão";
  if (raw === "rejeitado") return "Rejeitado";
  return "N/D";
}

type StatusKind = "auditavel" | "parcial" | "revisao" | "rejeitado" | "news" | "market" | "default";

function checkingKind(value?: string | null): StatusKind {
  const raw = normalize(value);
  if (["auditavel", "parcial", "revisao", "rejeitado"].includes(raw)) {
    return raw as StatusKind;
  }
  return "default";
}

function statusStyle(kind: StatusKind) {
  const colors: Record<StatusKind, string> = {
    auditavel: "#16803a",
    parcial: "#d97706",
    revisao: "#6d28d9",
    rejeitado: "#64748b",
    news: "#0f5fb8",
    market: "#1f4e79",
    default: "#6b7280",
  };

  return {
    ...badgeStyle,
    background: colors[kind],
  };
}

function getEvidenceUrl(item: EvidenceItem) {
  return item.screenshot_banner_url || item.screenshot_page_url || item.evidence_html_url || "";
}

function getImageUrl(item: EvidenceItem) {
  return item.screenshot_banner_url || item.image_url || item.screenshot_page_url || "";
}

function getPreviewCandidates(item: EvidenceItem) {
  const raw = [
    item.screenshot_banner_url,
    item.image_url,
    item.screenshot_page_url,
  ].filter(Boolean) as string[];

  return Array.from(new Set(raw));
}

function EvidencePreview({ item, compact = false }: { item: EvidenceItem; compact?: boolean }) {
  const candidates = useMemo(() => getPreviewCandidates(item), [
    item.id,
    item.screenshot_banner_url,
    item.image_url,
    item.screenshot_page_url,
  ]);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
  }, [candidates.join("|")]);

  const current = candidates[index];

  if (current) {
    return (
      <img
        src={current}
        alt={item.alt_text || item.advertiser_name || "Evidência"}
        style={compact ? previewStyle : modalImageStyle}
        loading={compact ? "lazy" : "eager"}
        referrerPolicy="no-referrer"
        onError={() => {
          setIndex((currentIndex) => {
            const nextIndex = currentIndex + 1;
            return nextIndex < candidates.length ? nextIndex : currentIndex;
          });
        }}
      />
    );
  }

  if (!compact && item.evidence_html_url) {
    return (
      <iframe
        src={item.evidence_html_url}
        title="Evidência preservada"
        style={modalIframeStyle}
      />
    );
  }

  return <div style={compact ? compactEmptyPreviewStyle : emptyPreviewStyle}>Sem imagem</div>;
}

function isChecking(item: EvidenceItem) {
  return ["auditavel", "parcial", "revisao"].includes(normalize(item.checking_status));
}

function itemMatchesFilter(item: EvidenceItem, filters: Filters) {
  const query = normalize(filters.q);
  if (query) {
    const haystack = normalize([
      item.advertiser_name,
      item.source_name,
      item.alt_text,
      item.ocr_text,
      item.page_url,
      item.image_url,
      item.classification_reason,
    ].join(" "));
    if (!haystack.includes(query)) return false;
  }

  if (filters.usage === "checking" && !isChecking(item)) return false;
  if (filters.usage === "market" && item.market_status !== "incluido") return false;
  if (filters.usage === "news" && item.news_status !== "candidato") return false;
  if (filters.usage === "rejected" && item.checking_status !== "rejeitado") return false;

  if (filters.portal && item.source_name !== filters.portal) return false;
  if (filters.contentType && item.content_type !== filters.contentType) return false;
  if (filters.checkingStatus && item.checking_status !== filters.checkingStatus) return false;
  if (filters.segmentId && item.segment_id !== filters.segmentId) return false;
  if (filters.advertiserId && item.advertiser_registry_id !== filters.advertiserId) return false;
  if (filters.preservedOnly && !item.has_preserved_evidence) return false;

  const minPub = filters.minPublicityScore ? Number(filters.minPublicityScore) : null;
  if (minPub !== null && Number(item.publicity_score || 0) < minPub) return false;

  const minNews = filters.minNewsScore ? Number(filters.minNewsScore) : null;
  if (minNews !== null && Number(item.news_score || 0) < minNews) return false;

  return true;
}

export default function EvidenceConsole() {
  const [items, setItems] = useState<EvidenceItem[]>([]);
  const [segments, setSegments] = useState<RegistrySegment[]>([]);
  const [advertisers, setAdvertisers] = useState<RegistryAdvertiser[]>([]);
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<EvidenceItem | null>(null);
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);

  useEffect(() => {
    setProjectId(getProjectIdFromUrl());
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        setLoading(true);
        const [response, segmentsResponse, advertisersResponse] = await Promise.all([
          authorizedFetch(`${API_BASE}/banners/${projectId}?limit=1000`),
          authorizedFetch(`${API_BASE}/registry/segments`),
          authorizedFetch(`${API_BASE}/registry/advertisers`),
        ]);

        if (!response.ok) {
          throw new Error(`Erro HTTP ${response.status}`);
        }

        const json = await response.json();
        const segmentsJson = segmentsResponse.ok ? await segmentsResponse.json() : [];
        const advertisersJson = advertisersResponse.ok ? await advertisersResponse.json() : [];
        if (isMounted) {
          setItems(Array.isArray(json) ? json : []);
          setSegments(Array.isArray(segmentsJson) ? segmentsJson : []);
          setAdvertisers(Array.isArray(advertisersJson) ? advertisersJson : []);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Erro ao carregar evidências.");
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    load();

    return () => {
      isMounted = false;
    };
  }, [projectId]);

  const portals = useMemo(() => {
    return Array.from(new Set(items.map((item) => item.source_name).filter(Boolean) as string[])).sort();
  }, [items]);

  const filteredAdvertisers = useMemo(() => {
    return filters.segmentId
      ? advertisers.filter((advertiser) => advertiser.segment_id === filters.segmentId)
      : advertisers;
  }, [advertisers, filters.segmentId]);

  const filtered = useMemo(() => {
    return items.filter((item) => itemMatchesFilter(item, filters));
  }, [items, filters]);

  const stats = useMemo(() => {
    return {
      total: items.length,
      filtered: filtered.length,
      auditavel: items.filter((item) => item.checking_status === "auditavel").length,
      revisao: items.filter((item) => ["parcial", "revisao"].includes(normalize(item.checking_status))).length,
      rejeitado: items.filter((item) => item.checking_status === "rejeitado").length,
      mercado: items.filter((item) => item.market_status === "incluido").length,
      noticias: items.filter((item) => item.news_status === "candidato").length,
      preserved: items.filter((item) => item.has_preserved_evidence).length,
    };
  }, [items, filtered]);

  function updateFilter<K extends keyof Filters>(key: K, value: Filters[K]) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  return (
    <div>
      <section style={introStyle}>
        <div>
          <div style={eyebrowStyle}>Console operacional</div>
          <h2 style={{ margin: "6px 0 8px", fontSize: 30 }}>Evidências de checking e inteligência</h2>
          <p style={{ margin: 0, lineHeight: 1.6, maxWidth: 900 }}>
            Esta tela separa publicidade auditável, itens úteis para inteligência de mercado e candidatos a notícia. Os registros rejeitados para checking permanecem preservados para auditoria, revisão e evolução do módulo editorial.
          </p>
        </div>

        <a href={`/intel?project_id=${encodeURIComponent(projectId)}`} style={heroButtonStyle}>Voltar ao Intel</a>
      </section>

      <section style={statsGridStyle}>
        <Stat title="Itens detectados" value={stats.total} hint="Todos os registros preservados" />
        <Stat title="Publicidade auditável" value={stats.auditavel} hint="Pronto para checking" />
        <Stat title="Revisão/parcial" value={stats.revisao} hint="Exige validação humana" />
        <Stat title="Candidatos a notícia" value={stats.noticias} hint="Fila editorial futura" />
        <Stat title="Inteligência de mercado" value={stats.mercado} hint="Itens comerciais incluídos" />
        <Stat title="Com prova preservada" value={stats.preserved} hint="Screenshot ou HTML salvo" />
      </section>

      <section style={filterPanelStyle}>
        <div style={filterHeaderStyle}>
          <div>
            <h3 style={{ margin: 0 }}>Filtros operacionais</h3>
            <p style={{ margin: "6px 0 0", color: "#6b7280" }}>{stats.filtered} registros exibidos</p>
          </div>

          <button type="button" onClick={() => setFilters(initialFilters)} style={secondaryButtonStyle}>
            Limpar filtros
          </button>
        </div>

        <div style={filterGridStyle}>
          <label style={labelStyle}>
            Busca livre
            <input
              value={filters.q}
              onChange={(event) => updateFilter("q", event.target.value)}
              placeholder="Anunciante, portal, OCR, URL..."
              style={inputStyle}
            />
          </label>

          <label style={labelStyle}>
            Finalidade
            <select value={filters.usage} onChange={(event) => updateFilter("usage", event.target.value as Filters["usage"])} style={inputStyle}>
              <option value="all">Todos</option>
              <option value="checking">Checking publicitário</option>
              <option value="market">Inteligência de mercado</option>
              <option value="news">Notícia candidata</option>
              <option value="rejected">Rejeitados para checking</option>
            </select>
          </label>

          <label style={labelStyle}>
            Portal
            <select value={filters.portal} onChange={(event) => updateFilter("portal", event.target.value)} style={inputStyle}>
              <option value="">Todos</option>
              {portals.map((portal) => (
                <option key={portal} value={portal}>{portal}</option>
              ))}
            </select>
          </label>

          <label style={labelStyle}>
            Tipo de conteúdo
            <select value={filters.contentType} onChange={(event) => updateFilter("contentType", event.target.value)} style={inputStyle}>
              <option value="">Todos</option>
              <option value="advertising">Publicidade</option>
              <option value="news">Notícia</option>
              <option value="mixed">Misto</option>
              <option value="institutional">Institucional</option>
              <option value="unknown">Indefinido</option>
            </select>
          </label>

          <label style={labelStyle}>
            Status checking
            <select value={filters.checkingStatus} onChange={(event) => updateFilter("checkingStatus", event.target.value)} style={inputStyle}>
              <option value="">Todos</option>
              <option value="auditavel">Auditável</option>
              <option value="parcial">Parcial</option>
              <option value="revisao">Revisão</option>
              <option value="rejeitado">Rejeitado</option>
            </select>
          </label>

          <label style={labelStyle}>
            Segmento
            <select value={filters.segmentId} onChange={(event) => updateFilter("segmentId", event.target.value)} style={inputStyle}>
              <option value="">Todos</option>
              {segments.map((segment) => (
                <option key={segment.id} value={segment.id}>{segment.name}</option>
              ))}
            </select>
          </label>

          <label style={labelStyle}>
            Anunciante cadastrado
            <select value={filters.advertiserId} onChange={(event) => updateFilter("advertiserId", event.target.value)} style={inputStyle}>
              <option value="">Todos</option>
              {filteredAdvertisers.map((advertiser) => (
                <option key={advertiser.id} value={advertiser.id}>{advertiser.name}{advertiser.segment_name ? ` · ${advertiser.segment_name}` : ""}</option>
              ))}
            </select>
          </label>

          <label style={labelStyle}>
            Score pub. mínimo
            <input
              value={filters.minPublicityScore}
              onChange={(event) => updateFilter("minPublicityScore", event.target.value)}
              type="number"
              min={0}
              max={100}
              placeholder="0-100"
              style={inputStyle}
            />
          </label>

          <label style={labelStyle}>
            Score notícia mínimo
            <input
              value={filters.minNewsScore}
              onChange={(event) => updateFilter("minNewsScore", event.target.value)}
              type="number"
              min={0}
              max={100}
              placeholder="0-100"
              style={inputStyle}
            />
          </label>

          <label style={{ ...labelStyle, flexDirection: "row", alignItems: "center", gap: 10, paddingTop: 22 }}>
            <input
              checked={filters.preservedOnly}
              onChange={(event) => updateFilter("preservedOnly", event.target.checked)}
              type="checkbox"
            />
            Apenas com evidência preservada
          </label>
        </div>
      </section>

      {loading && <div style={panelStyle}>Carregando evidências...</div>}
      {error && <div style={errorStyle}>{error}</div>}

      {!loading && !error && (
        <section style={panelStyle}>
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>Preview</th>
                  <th style={thStyle}>Data</th>
                  <th style={thStyle}>Anunciante/tema</th>
                  <th style={thStyle}>Portal</th>
                  <th style={thStyle}>Tipo</th>
                  <th style={thStyle}>Checking</th>
                  <th style={thStyle}>Mercado</th>
                  <th style={thStyle}>Notícia</th>
                  <th style={thStyle}>Scores</th>
                  <th style={thStyle}>Ações</th>
                </tr>
              </thead>

              <tbody>
                {filtered.slice(0, 300).map((item, index) => {
                  return (
                    <tr key={item.id || `${item.image_url}-${index}`}>
                      <td style={tdStyle}>
                        <EvidencePreview item={item} compact />
                      </td>
                      <td style={tdStyle}>{formatDate(item.created_at)}</td>
                      <td style={tdStyle}>
                        <strong>{item.effective_advertiser_name || item.advertiser_registry_name || item.advertiser_name || item.alt_text || "Não identificado"}</strong>
                        {item.segment_name ? <div style={mutedSmallStyle}>Segmento: {item.segment_name}</div> : null}
                        {item.ocr_text ? <div style={mutedSmallStyle}>{item.ocr_text.slice(0, 90)}</div> : null}
                      </td>
                      <td style={tdStyle}>{item.source_name || "Web aberto"}</td>
                      <td style={tdStyle}>{contentTypeLabel(item.content_type)}</td>
                      <td style={tdStyle}>
                        <span style={statusStyle(checkingKind(item.checking_status))}>{checkingLabel(item.checking_status)}</span>
                      </td>
                      <td style={tdStyle}>
                        {item.market_status === "incluido" ? <span style={statusStyle("market")}>Incluído</span> : <span style={mutedBadgeStyle}>Ignorado</span>}
                      </td>
                      <td style={tdStyle}>
                        {item.news_status === "candidato" ? <span style={statusStyle("news")}>Candidato</span> : <span style={mutedBadgeStyle}>Ignorado</span>}
                      </td>
                      <td style={tdStyle}>
                        <div>Pub: <strong>{item.publicity_score ?? 0}</strong></div>
                        <div>Notícia: <strong>{item.news_score ?? 0}</strong></div>
                      </td>
                      <td style={tdStyle}>
                        <button type="button" onClick={() => setSelected(item)} style={primaryButtonStyle}>Detalhar</button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {filtered.length === 0 && <p style={{ color: "#6b7280" }}>Nenhum registro encontrado com os filtros atuais.</p>}
          {filtered.length > 300 && <p style={{ color: "#6b7280" }}>Exibindo os 300 registros mais recentes filtrados.</p>}
        </section>
      )}

      {selected && <EvidenceModal item={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function Stat({ title, value, hint }: { title: string; value: number; hint: string }) {
  return (
    <div style={statStyle}>
      <div style={{ fontSize: 12, color: "#6b7280", textTransform: "uppercase", letterSpacing: 0.8, fontWeight: 800 }}>{title}</div>
      <div style={{ fontSize: 32, fontWeight: 900, color: "#b00020", marginTop: 8 }}>{value}</div>
      <div style={{ fontSize: 13, color: "#6b7280", marginTop: 8 }}>{hint}</div>
    </div>
  );
}

function EvidenceModal({ item, onClose }: { item: EvidenceItem; onClose: () => void }) {
  const evidenceUrl = getEvidenceUrl(item);

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        <div style={modalHeaderStyle}>
          <div>
            <div style={eyebrowStyle}>Detalhe da evidência</div>
            <h2 style={{ margin: "6px 0 4px" }}>{item.effective_advertiser_name || item.advertiser_registry_name || item.advertiser_name || item.alt_text || "Não identificado"}</h2>
            <p style={{ margin: 0, color: "#6b7280" }}>{item.source_name || "Web aberto"} · {formatDate(item.created_at)}</p>
          </div>
          <button type="button" onClick={onClose} style={closeButtonStyle}>×</button>
        </div>

        <div style={modalGridStyle}>
          <div>
            <EvidencePreview item={item} />
            <div style={previewHelpStyle}>
              Preview automático: banner preservado → imagem original → screenshot da página.
            </div>
          </div>

          <div style={{ display: "grid", gap: 12 }}>
            <Info label="Tipo" value={contentTypeLabel(item.content_type)} />
            <Info label="Segmento" value={item.segment_name || "N/D"} />
            <Info label="Alias cadastrado" value={item.advertiser_alias_matched || "N/D"} />
            <Info label="Checking" value={checkingLabel(item.checking_status)} />
            <Info label="Mercado" value={item.market_status === "incluido" ? "Incluído" : "Ignorado"} />
            <Info label="Notícia" value={item.news_status === "candidato" ? "Candidato" : "Ignorado"} />
            <Info label="Formato" value={formatSize(item)} />
            <Info label="Valor estimado" value={formatBRL(item.estimated_value)} />
            <Info label="Scores" value={`Publicidade ${item.publicity_score ?? 0} · Notícia ${item.news_score ?? 0} · Mercado ${item.market_score ?? 0}`} />
            <Info label="Tipo de evidência" value={item.evidence_type || "N/D"} />
          </div>
        </div>

        <div style={modalTextGridStyle}>
          <div style={textPanelStyle}>
            <strong>Texto OCR</strong>
            <p style={{ whiteSpace: "pre-wrap", marginBottom: 0 }}>{item.ocr_text || "Nenhum OCR detectado."}</p>
          </div>

          <div style={textPanelStyle}>
            <strong>Motivo técnico</strong>
            <p style={{ whiteSpace: "pre-wrap", marginBottom: 0 }}>{item.classification_reason || "Sem motivo registrado."}</p>
          </div>
        </div>

        <div style={modalActionsStyle}>
          {evidenceUrl ? <a href={evidenceUrl} target="_blank" rel="noreferrer" style={primaryLinkStyle}>Abrir evidência preservada</a> : null}
          {item.screenshot_banner_url ? <a href={item.screenshot_banner_url} target="_blank" rel="noreferrer" style={secondaryLinkStyle}>Abrir banner preservado</a> : null}
          {item.screenshot_page_url ? <a href={item.screenshot_page_url} target="_blank" rel="noreferrer" style={secondaryLinkStyle}>Abrir página preservada</a> : null}
          {item.image_url ? <a href={item.image_url} target="_blank" rel="noreferrer" style={secondaryLinkStyle}>Imagem original</a> : null}
          {item.page_url ? <a href={item.page_url} target="_blank" rel="noreferrer" style={secondaryLinkStyle}>Página original</a> : null}
        </div>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ background: "#f8fafc", border: "1px solid #e5e7eb", borderRadius: 12, padding: 12 }}>
      <div style={{ color: "#6b7280", fontSize: 12, fontWeight: 700, textTransform: "uppercase" }}>{label}</div>
      <div style={{ marginTop: 5, fontWeight: 800 }}>{value}</div>
    </div>
  );
}

const introStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 20,
  background: "linear-gradient(135deg, #6b0012 0%, #b00020 72%, #d1243f 100%)",
  color: "#fff",
  borderRadius: 22,
  padding: 26,
  boxShadow: "0 10px 26px rgba(122,0,21,0.22)",
  marginBottom: 22,
};

const eyebrowStyle: CSSProperties = {
  fontSize: 12,
  letterSpacing: 1.4,
  textTransform: "uppercase",
  fontWeight: 900,
  opacity: 0.86,
};

const heroButtonStyle: CSSProperties = {
  background: "rgba(255,255,255,0.16)",
  border: "1px solid rgba(255,255,255,0.28)",
  color: "#fff",
  padding: "12px 16px",
  borderRadius: 12,
  textDecoration: "none",
  fontWeight: 800,
  whiteSpace: "nowrap",
};

const statsGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: 16,
  marginBottom: 20,
};

const statStyle: CSSProperties = {
  background: "#fff",
  border: "1px solid #eef1f5",
  borderRadius: 16,
  padding: 18,
  boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
};

const filterPanelStyle: CSSProperties = {
  background: "#fff",
  border: "1px solid #eef1f5",
  borderRadius: 18,
  padding: 20,
  boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
  marginBottom: 20,
};

const filterHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 16,
  marginBottom: 16,
};

const filterGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
  gap: 14,
};

const labelStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 6,
  fontSize: 13,
  color: "#374151",
  fontWeight: 800,
};

const inputStyle: CSSProperties = {
  border: "1px solid #d1d5db",
  borderRadius: 10,
  padding: "10px 11px",
  fontSize: 14,
  outline: "none",
  background: "#fff",
  color: "#111827",
  WebkitTextFillColor: "#111827",
  colorScheme: "light",
  appearance: "auto",
};

const panelStyle: CSSProperties = {
  background: "#fff",
  border: "1px solid #eef1f5",
  borderRadius: 18,
  padding: 20,
  boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
};

const errorStyle: CSSProperties = {
  ...panelStyle,
  borderColor: "#fecaca",
  background: "#fff1f2",
  color: "#991b1b",
};

const tableStyle: CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 13,
};

const thStyle: CSSProperties = {
  textAlign: "left",
  background: "#f8fafc",
  borderBottom: "1px solid #e5e7eb",
  padding: "12px 10px",
  color: "#374151",
  whiteSpace: "nowrap",
};

const tdStyle: CSSProperties = {
  borderBottom: "1px solid #edf0f4",
  padding: "11px 10px",
  verticalAlign: "top",
};

const previewStyle: CSSProperties = {
  width: 86,
  height: 58,
  objectFit: "cover",
  borderRadius: 10,
  border: "1px solid #e5e7eb",
  background: "#f3f4f6",
};

const compactEmptyPreviewStyle: CSSProperties = {
  width: 86,
  height: 58,
  display: "grid",
  placeItems: "center",
  borderRadius: 10,
  border: "1px solid #e5e7eb",
  background: "#f3f4f6",
  color: "#94a3b8",
  fontSize: 11,
  textAlign: "center",
};

const badgeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  borderRadius: 999,
  color: "#fff",
  padding: "5px 9px",
  fontWeight: 900,
  fontSize: 12,
  whiteSpace: "nowrap",
};

const mutedBadgeStyle: CSSProperties = {
  ...badgeStyle,
  background: "#e5e7eb",
  color: "#475569",
};

const mutedSmallStyle: CSSProperties = {
  color: "#6b7280",
  fontSize: 12,
  marginTop: 4,
  maxWidth: 360,
};

const primaryButtonStyle: CSSProperties = {
  border: "none",
  background: "#b00020",
  color: "#fff",
  borderRadius: 9,
  padding: "8px 11px",
  fontWeight: 900,
  cursor: "pointer",
};

const secondaryButtonStyle: CSSProperties = {
  border: "1px solid #d1d5db",
  background: "#fff",
  color: "#374151",
  borderRadius: 10,
  padding: "10px 13px",
  fontWeight: 800,
  cursor: "pointer",
};

const overlayStyle: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(15,23,42,0.72)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
  padding: 20,
};

const modalStyle: CSSProperties = {
  width: "min(1100px, 96vw)",
  maxHeight: "92vh",
  overflowY: "auto",
  background: "#fff",
  borderRadius: 20,
  padding: 22,
  boxShadow: "0 24px 80px rgba(0,0,0,0.32)",
};

const modalHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  gap: 16,
  borderBottom: "1px solid #e5e7eb",
  paddingBottom: 16,
  marginBottom: 18,
};

const closeButtonStyle: CSSProperties = {
  border: "none",
  background: "#f1f5f9",
  width: 38,
  height: 38,
  borderRadius: 10,
  fontSize: 24,
  cursor: "pointer",
};

const modalGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1.2fr 0.8fr",
  gap: 18,
};

const modalImageStyle: CSSProperties = {
  width: "100%",
  minHeight: 260,
  maxHeight: 480,
  objectFit: "contain",
  borderRadius: 14,
  background: "#f8fafc",
  border: "1px solid #e5e7eb",
};

const modalIframeStyle: CSSProperties = {
  width: "100%",
  minHeight: 420,
  border: "1px solid #e5e7eb",
  borderRadius: 14,
  background: "#fff",
};

const previewHelpStyle: CSSProperties = {
  color: "#64748b",
  fontSize: 12,
  marginTop: 8,
  lineHeight: 1.45,
};

const emptyPreviewStyle: CSSProperties = {
  minHeight: 260,
  display: "grid",
  placeItems: "center",
  borderRadius: 14,
  background: "#f8fafc",
  color: "#64748b",
};

const modalTextGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: 16,
  marginTop: 18,
};

const textPanelStyle: CSSProperties = {
  background: "#f8fafc",
  border: "1px solid #e5e7eb",
  borderRadius: 14,
  padding: 14,
  color: "#1f2937",
};

const modalActionsStyle: CSSProperties = {
  display: "flex",
  gap: 12,
  flexWrap: "wrap",
  marginTop: 18,
};

const primaryLinkStyle: CSSProperties = {
  background: "#b00020",
  color: "#fff",
  borderRadius: 10,
  padding: "10px 13px",
  textDecoration: "none",
  fontWeight: 900,
};

const secondaryLinkStyle: CSSProperties = {
  background: "#f1f5f9",
  color: "#1f2937",
  borderRadius: 10,
  padding: "10px 13px",
  textDecoration: "none",
  fontWeight: 900,
};
