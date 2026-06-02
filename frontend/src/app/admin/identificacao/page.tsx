"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";

const API =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";
const TOKEN_STORAGE_KEY = "tvfiscal_admin_token";
const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

type Advertiser = {
  id: string;
  name: string;
  segment_name?: string | null;
  aliases?: string[];
};
type PendingItem = {
  id: string;
  portal?: string | null;
  page_url?: string | null;
  image_url?: string | null;
  value?: number;
  created_at?: string | null;
};
type PendingGroup = {
  group_key: string;
  count: number;
  estimated_investment: number;
  sample_id: string;
  sample_image_url?: string | null;
  sample_page_url?: string | null;
  sample_preview_url?: string | null;
  sample_ocr?: string | null;
  sample_alt?: string | null;
  source_name?: string | null;
  format?: string | null;
  publicity_score?: number;
  market_score?: number;
  confidence_hint?: string;
  suggestion?: string;
  suggested_advertiser_id?: string | null;
  suggested_advertiser_name?: string | null;
  suggested_alias?: string | null;
  suggested_origin?: string | null;
  first_seen?: string | null;
  last_seen?: string | null;
  portals?: string[];
  portals_count?: number;
  items?: PendingItem[];
};
type PendingResponse = {
  project_id: string;
  groups: PendingGroup[];
  summary: {
    pending_groups: number;
    pending_items: number;
    pending_investment: number;
    auto_suggested_groups?: number;
  };
};
type QualityResponse = {
  total_market_items: number;
  total_market_investment: number;
  identified_items: number;
  identified_investment: number;
  pending_items: number;
  pending_investment: number;
  auditables_pending: number;
  qualified_manual: number;
  qualified_auto: number;
  ignored: number;
  identified_rate: number;
  pending_rate: number;
  quality_label: string;
};
type ActionItem = {
  id: string;
  status?: string | null;
  advertiser_name?: string | null;
  note?: string | null;
  portal?: string | null;
  value?: number;
  qualified_at?: string | null;
  created_at?: string | null;
  preview_url?: string | null;
  page_url?: string | null;
};
type ActionResponse = { actions: ActionItem[] };

function brl(value: number | undefined) {
  return `R$ ${Number(value || 0).toLocaleString("pt-BR")}`;
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("pt-BR");
  } catch {
    return value;
  }
}

function cleanSuggestion(text?: string | null) {
  return (text || "").replace(/\s+/g, " ").trim();
}

export default function AdminIdentificacaoPage() {
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [data, setData] = useState<PendingResponse | null>(null);
  const [quality, setQuality] = useState<QualityResponse | null>(null);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [advertisers, setAdvertisers] = useState<Advertiser[]>([]);
  const [selectedAdvertiser, setSelectedAdvertiser] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<PendingGroup | null>(null);
  const [alias, setAlias] = useState("");
  const [createAlias, setCreateAlias] = useState(true);
  const [applyAliasToPending, setApplyAliasToPending] = useState(false);
  const [note, setNote] = useState("");
  const [limit, setLimit] = useState(120);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const authenticated = Boolean(token);

  function headers() {
    return { "Content-Type": "application/json", "X-Admin-Token": token };
  }

  async function apiGet<T>(path: string): Promise<T> {
    const res = await fetch(`${API}${path}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);
    return res.json();
  }

  async function apiPost<T>(path: string, body: unknown): Promise<T> {
    const res = await fetch(`${API}${path}`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Erro HTTP ${res.status}`);
    }
    return res.json();
  }

  async function loadAll(customProjectId = projectId) {
    setLoading(true);
    try {
      setError("");
      const [pending, qualityPayload, actionPayload, advs] = await Promise.all([
        apiGet<PendingResponse>(
          `/identification/pending/${customProjectId}?limit=${limit}`,
        ),
        apiGet<QualityResponse>(`/identification/quality/${customProjectId}`),
        apiGet<ActionResponse>(
          `/identification/actions/${customProjectId}?limit=60`,
        ),
        apiGet<Advertiser[]>("/registry/advertisers?active_only=true"),
      ]);
      setData(pending);
      setQuality(qualityPayload);
      setActions(actionPayload.actions || []);
      setAdvertisers(advs);
      if (!selectedAdvertiser && advs.length) setSelectedAdvertiser(advs[0].id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erro ao carregar fila de identificação.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_STORAGE_KEY) || "";
    setToken(saved);
    setTokenInput(saved);
    const params = new URLSearchParams(window.location.search);
    const p = params.get("project_id") || DEFAULT_PROJECT_ID;
    setProjectId(p);
    loadAll(p);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function login() {
    const cleaned = tokenInput.trim();
    if (!cleaned) {
      setError("Informe o token administrativo.");
      return;
    }
    localStorage.setItem(TOKEN_STORAGE_KEY, cleaned);
    setToken(cleaned);
    setMessage("Token administrativo carregado.");
  }

  function openGroup(group: PendingGroup) {
    setSelectedGroup(group);
    setAlias(
      cleanSuggestion(
        group.suggested_alias ||
          group.sample_alt ||
          group.sample_ocr ||
          group.suggestion ||
          "",
      ).slice(0, 240),
    );
    if (group.suggested_advertiser_id)
      setSelectedAdvertiser(group.suggested_advertiser_id);
    setApplyAliasToPending(Boolean(group.suggested_advertiser_id));
    setNote(
      group.suggested_advertiser_name
        ? `Sugestão automática: ${group.suggested_advertiser_name} via ${group.suggested_alias || "alias"}.`
        : "",
    );
  }

  async function qualifySelected() {
    if (!selectedGroup) return;
    if (!selectedAdvertiser) {
      setError("Selecione um anunciante para qualificar o grupo.");
      return;
    }
    try {
      setError("");
      const result = await apiPost<{ message: string }>(
        `/identification/qualify/${projectId}`,
        {
          group_key: selectedGroup.group_key,
          advertiser_id: selectedAdvertiser,
          create_alias: createAlias,
          alias: createAlias ? alias : null,
          note: note || "Qualificação manual pelo painel administrativo.",
          apply_alias_to_pending: applyAliasToPending,
        },
      );
      setMessage(result.message || "Grupo qualificado.");
      setSelectedGroup(null);
      await loadAll();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erro ao qualificar grupo.",
      );
    }
  }

  async function reprocessAliases() {
    try {
      setError("");
      const result = await apiPost<{ message: string; updated: number }>(
        `/identification/reprocess-aliases/${projectId}`,
        {},
      );
      setMessage(
        result.message ||
          `${result.updated || 0} item(ns) reprocessado(s) por alias.`,
      );
      await loadAll();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erro ao reprocessar aliases.",
      );
    }
  }

  async function runAutoIdentification() {
    try {
      setError("");
      const result = await apiPost<{ message: string; updated: number; quality?: QualityResponse }>(
        `/identification/auto-run/${projectId}`,
        {},
      );
      setMessage(
        result.message ||
          `${result.updated || 0} item(ns) qualificado(s) automaticamente por alias.`,
      );
      await loadAll();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erro ao executar autoidentificação.",
      );
    }
  }

  function downloadCsv(kind: "pending" | "actions") {
    const path =
      kind === "pending"
        ? `/identification/pending/${projectId}/export.csv?limit=2000`
        : `/identification/actions/${projectId}/export.csv?limit=2000`;
    window.open(`${API}${path}`, "_blank");
  }

  async function ignoreSelected(removeFromMarket = true) {
    if (!selectedGroup) return;
    try {
      setError("");
      const result = await apiPost<{ message: string }>(
        `/identification/ignore/${projectId}`,
        {
          group_key: selectedGroup.group_key,
          note: note || "Ignorado pela qualificação manual.",
          remove_from_market: removeFromMarket,
        },
      );
      setMessage(result.message || "Grupo ignorado.");
      setSelectedGroup(null);
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao ignorar grupo.");
    }
  }

  const topGroups = useMemo(() => data?.groups || [], [data]);

  return (
    <AppShell
      title="Qualificação de marcas"
      subtitle="Fila operacional para transformar pendentes de identificação em anunciantes cadastrados ou remover ruído da inteligência de mercado."
    >
      <section style={heroStyle}>
        <div>
          <div style={eyebrowStyle}>Auditoria comercial · Intel de mercado</div>
          <h2 style={{ margin: "6px 0 8px", fontSize: 30 }}>
            Pendente de identificação não é anunciante líder
          </h2>
          <p style={{ margin: 0, lineHeight: 1.6 }}>
            Revise grupos de peças não identificadas, atribua a um anunciante
            cadastrado, crie alias de reconhecimento e limpe itens que não devem
            compor o mercado.
          </p>
        </div>
        <div style={{ display: "grid", gap: 10, minWidth: 360 }}>
          <input
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
            placeholder="Token administrativo"
            style={inputStyle}
          />
          <input
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            placeholder="project_id"
            style={inputStyle}
          />
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={login} style={primaryButtonStyle}>
              Usar token
            </button>
            <button onClick={() => loadAll()} style={secondaryButtonStyle}>
              {loading ? "Carregando..." : "Atualizar fila"}
            </button>
            <button
              disabled={!authenticated}
              onClick={reprocessAliases}
              style={secondaryButtonStyle}
            >
              Reprocessar aliases
            </button>
            <button
              disabled={!authenticated}
              onClick={runAutoIdentification}
              style={secondaryButtonStyle}
            >
              Autoidentificar agora
            </button>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button onClick={() => downloadCsv("pending")} style={miniButtonStyle}>
              Exportar pendentes CSV
            </button>
            <button onClick={() => downloadCsv("actions")} style={miniButtonStyle}>
              Exportar ações CSV
            </button>
            <span style={{ color: "rgba(255,255,255,.72)", fontSize: 12, alignSelf: "center" }}>
              Pós-coleta: aliases aprendidos são aplicados automaticamente ao Scheduler.
            </span>
          </div>
        </div>
      </section>

      {message ? <div style={successStyle}>{message}</div> : null}
      {error ? <div style={errorStyle}>{error}</div> : null}

      <section style={kpiGridStyle}>
        <Kpi
          label="Qualidade da base"
          value={`${quality?.identified_rate ?? 0}%`}
          hint={quality?.quality_label || "—"}
        />
        <Kpi
          label="Itens pendentes"
          value={data?.summary.pending_items || 0}
          hint={`${data?.summary.pending_groups || 0} grupo(s)`}
        />
        <Kpi
          label="Investimento pendente"
          value={brl(data?.summary.pending_investment)}
          hint="fila de qualificação"
        />
        <Kpi
          label="Sugestões por alias"
          value={data?.summary.auto_suggested_groups || 0}
          hint="prontas para revisar"
        />
        <Kpi
          label="Qualificados manualmente"
          value={quality?.qualified_manual || 0}
          hint="curadoria humana"
        />
        <Kpi
          label="Qualificados por alias"
          value={quality?.qualified_auto || 0}
          hint="aprendizado aplicado"
        />
        <Kpi
          label="Auditáveis pendentes"
          value={quality?.auditables_pending || 0}
          hint="prioridade checking"
        />
        <Kpi
          label="Anunciantes cadastrados"
          value={advertisers.length}
          hint="base comercial"
        />
      </section>

      <section style={panelStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 16,
            alignItems: "center",
            marginBottom: 16,
          }}
        >
          <div>
            <h3 style={{ margin: 0 }}>Fila de qualificação</h3>
            <p style={{ margin: "4px 0 0", color: "#667085" }}>
              Prioridade por investimento estimado e volume de repetições. Ao
              qualificar, o Intel e os relatórios deixam de inflar “Pendente de
              identificação”.
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "#667085" }}>Limite</span>
            <input
              type="number"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value || 120))}
              style={{ ...inputStyle, width: 90 }}
            />
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Grupo</th>
                <th style={thStyle}>Amostra</th>
                <th style={thStyle}>Portais</th>
                <th style={thStyle}>Formato</th>
                <th style={thStyle}>Itens</th>
                <th style={thStyle}>Invest.</th>
                <th style={thStyle}>Score</th>
                <th style={thStyle}>Ação</th>
              </tr>
            </thead>
            <tbody>
              {topGroups.length ? (
                topGroups.map((group) => (
                  <tr key={group.group_key}>
                    <td style={tdStyle}>
                      <code>{group.group_key}</code>
                      <br />
                      <small>{formatDate(group.last_seen)}</small>
                    </td>
                    <td style={tdStyle}>
                      <div
                        style={{
                          maxWidth: 420,
                          fontWeight: 700,
                          color: "#101828",
                        }}
                      >
                        {cleanSuggestion(group.suggestion) || "Sem sugestão"}
                      </div>
                      <div
                        style={{ color: "#667085", fontSize: 12, marginTop: 4 }}
                      >
                        {group.sample_image_url || group.sample_page_url}
                      </div>
                      {group.suggested_advertiser_name ? (
                        <div style={suggestionBadgeStyle}>
                          Sugestão: {group.suggested_advertiser_name} ·{" "}
                          {group.suggested_alias}
                        </div>
                      ) : null}
                    </td>
                    <td style={tdStyle}>
                      {group.portals?.join(", ") || group.source_name || "—"}
                    </td>
                    <td style={tdStyle}>{group.format || "—"}</td>
                    <td style={tdStyle}>{group.count}</td>
                    <td style={tdStyle}>{brl(group.estimated_investment)}</td>
                    <td style={tdStyle}>
                      {group.publicity_score || group.market_score || 0}
                    </td>
                    <td style={tdStyle}>
                      <button
                        onClick={() => openGroup(group)}
                        style={smallButtonStyle}
                      >
                        Qualificar
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={8}
                    style={{
                      ...tdStyle,
                      textAlign: "center",
                      color: "#667085",
                      padding: 30,
                    }}
                  >
                    Nenhum grupo pendente encontrado.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section style={{ ...panelStyle, marginTop: 18 }}>
        <h3 style={{ margin: 0 }}>Últimas ações de identificação</h3>
        <p style={{ margin: "4px 0 14px", color: "#667085" }}>
          Trilha operacional das qualificações manuais, automáticas e itens
          ignorados.
        </p>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Data</th>
                <th style={thStyle}>Status</th>
                <th style={thStyle}>Anunciante</th>
                <th style={thStyle}>Portal</th>
                <th style={thStyle}>Valor</th>
                <th style={thStyle}>Observação</th>
              </tr>
            </thead>
            <tbody>
              {actions.length ? (
                actions.map((action) => (
                  <tr key={action.id}>
                    <td style={tdStyle}>
                      {formatDate(action.qualified_at || action.created_at)}
                    </td>
                    <td style={tdStyle}>
                      <span
                        style={
                          action.status === "ignorado"
                            ? dangerPillStyle
                            : okPillStyle
                        }
                      >
                        {action.status || "—"}
                      </span>
                    </td>
                    <td style={tdStyle}>{action.advertiser_name || "—"}</td>
                    <td style={tdStyle}>{action.portal || "—"}</td>
                    <td style={tdStyle}>{brl(action.value)}</td>
                    <td style={tdStyle}>{action.note || "—"}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={6}
                    style={{
                      ...tdStyle,
                      textAlign: "center",
                      color: "#667085",
                    }}
                  >
                    Sem ações recentes.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {selectedGroup ? (
        <div style={modalBackdropStyle} onClick={() => setSelectedGroup(null)}>
          <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
              }}
            >
              <div>
                <h2 style={{ margin: 0 }}>Qualificar grupo</h2>
                <p style={{ margin: "6px 0 0", color: "#667085" }}>
                  {selectedGroup.count} item(ns) ·{" "}
                  {brl(selectedGroup.estimated_investment)} ·{" "}
                  {selectedGroup.portals?.join(", ") || "sem portal"}
                </p>
                {selectedGroup.suggested_advertiser_name ? (
                  <div style={suggestionBadgeStyle}>
                    Sugestão automática:{" "}
                    {selectedGroup.suggested_advertiser_name} via{" "}
                    {selectedGroup.suggested_alias}
                  </div>
                ) : null}
              </div>
              <button
                onClick={() => setSelectedGroup(null)}
                style={ghostButtonStyle}
              >
                ×
              </button>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 16,
                marginTop: 18,
              }}
            >
              <div style={previewBoxStyle}>
                <strong>Amostra</strong>
                {selectedGroup.sample_image_url ? (
                  <img
                    src={selectedGroup.sample_image_url}
                    alt="amostra"
                    style={{
                      maxWidth: "100%",
                      maxHeight: 180,
                      objectFit: "contain",
                      display: "block",
                      marginTop: 12,
                    }}
                  />
                ) : (
                  <div style={{ marginTop: 12, color: "#667085" }}>
                    Sem imagem direta disponível.
                  </div>
                )}
                <p style={{ color: "#475467", fontSize: 13 }}>
                  {cleanSuggestion(
                    selectedGroup.sample_ocr ||
                      selectedGroup.sample_alt ||
                      selectedGroup.suggestion,
                  )}
                </p>
                {selectedGroup.sample_page_url ? (
                  <a
                    href={selectedGroup.sample_page_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Abrir página original
                  </a>
                ) : null}
              </div>

              <div style={{ display: "grid", gap: 12 }}>
                <label style={labelStyle}>Anunciante correto</label>
                <select
                  value={selectedAdvertiser}
                  onChange={(e) => setSelectedAdvertiser(e.target.value)}
                  style={inputStyle}
                >
                  {advertisers.map((adv) => (
                    <option key={adv.id} value={adv.id}>
                      {adv.name}
                      {adv.segment_name ? ` · ${adv.segment_name}` : ""}
                    </option>
                  ))}
                </select>

                <label style={labelStyle}>
                  Alias para reconhecimento futuro
                </label>
                <input
                  value={alias}
                  onChange={(e) => setAlias(e.target.value)}
                  style={inputStyle}
                  placeholder="Ex.: marca, domínio, texto do banner"
                />
                <label
                  style={{
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                    color: "#344054",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={createAlias}
                    onChange={(e) => setCreateAlias(e.target.checked)}
                  />{" "}
                  Criar alias automaticamente
                </label>
                <label
                  style={{
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                    color: "#344054",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={applyAliasToPending}
                    onChange={(e) => setApplyAliasToPending(e.target.checked)}
                  />{" "}
                  Aplicar alias aos demais pendentes
                </label>

                <label style={labelStyle}>Observação interna</label>
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  style={{ ...inputStyle, minHeight: 90 }}
                  placeholder="Ex.: validado visualmente pelo operador"
                />

                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                  <button
                    disabled={!authenticated}
                    onClick={qualifySelected}
                    style={primaryButtonStyle}
                  >
                    Aplicar anunciante
                  </button>
                  <button
                    disabled={!authenticated}
                    onClick={() => ignoreSelected(true)}
                    style={dangerButtonStyle}
                  >
                    Ignorar e remover do mercado
                  </button>
                  <button
                    disabled={!authenticated}
                    onClick={() => ignoreSelected(false)}
                    style={secondaryButtonStyle}
                  >
                    Só retirar da fila
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}

function Kpi({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div style={kpiStyle}>
      <div style={{ color: "#667085", fontSize: 13 }}>{label}</div>
      <div
        style={{
          color: "#101828",
          fontSize: 28,
          fontWeight: 800,
          marginTop: 4,
        }}
      >
        {value}
      </div>
      {hint ? (
        <div style={{ color: "#98a2b3", fontSize: 12, marginTop: 2 }}>
          {hint}
        </div>
      ) : null}
    </div>
  );
}

const heroStyle: React.CSSProperties = {
  background: "linear-gradient(135deg,#071c33 0%,#0b2c4d 60%,#b00020 100%)",
  color: "#fff",
  borderRadius: 18,
  padding: 26,
  display: "flex",
  justifyContent: "space-between",
  gap: 24,
  alignItems: "center",
  boxShadow: "0 12px 32px rgba(7,28,51,.22)",
  marginBottom: 18,
};
const eyebrowStyle: React.CSSProperties = {
  textTransform: "uppercase",
  letterSpacing: 1.8,
  fontSize: 12,
  opacity: 0.82,
  fontWeight: 800,
};
const miniButtonStyle: React.CSSProperties = {
  border: "1px solid rgba(255,255,255,.28)",
  background: "rgba(255,255,255,.10)",
  color: "#fff",
  borderRadius: 999,
  padding: "8px 12px",
  fontWeight: 800,
  cursor: "pointer",
};

const inputStyle: React.CSSProperties = {
  padding: "11px 12px",
  borderRadius: 10,
  border: "1px solid #d0d5dd",
  background: "#fff",
  color: "#101828",
  WebkitTextFillColor: "#101828",
  colorScheme: "light",
  boxSizing: "border-box",
  width: "100%",
};
const primaryButtonStyle: React.CSSProperties = {
  background: "#b00020",
  color: "#fff",
  border: 0,
  borderRadius: 10,
  padding: "11px 14px",
  fontWeight: 800,
  cursor: "pointer",
};
const secondaryButtonStyle: React.CSSProperties = {
  background: "#eef2f6",
  color: "#102033",
  border: "1px solid #d0d5dd",
  borderRadius: 10,
  padding: "11px 14px",
  fontWeight: 800,
  cursor: "pointer",
};
const dangerButtonStyle: React.CSSProperties = {
  background: "#dc2626",
  color: "#fff",
  border: 0,
  borderRadius: 10,
  padding: "11px 14px",
  fontWeight: 800,
  cursor: "pointer",
};
const ghostButtonStyle: React.CSSProperties = {
  background: "transparent",
  color: "#101828",
  border: 0,
  fontSize: 28,
  cursor: "pointer",
};
const smallButtonStyle: React.CSSProperties = {
  ...primaryButtonStyle,
  padding: "8px 10px",
  fontSize: 12,
};
const successStyle: React.CSSProperties = {
  background: "#ecfdf3",
  border: "1px solid #abefc6",
  color: "#067647",
  padding: 12,
  borderRadius: 12,
  marginBottom: 14,
};
const errorStyle: React.CSSProperties = {
  background: "#fef3f2",
  border: "1px solid #fecdca",
  color: "#b42318",
  padding: 12,
  borderRadius: 12,
  marginBottom: 14,
};
const kpiGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(4,minmax(0,1fr))",
  gap: 14,
  marginBottom: 18,
};
const kpiStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e4e7ec",
  borderRadius: 16,
  padding: 18,
  boxShadow: "0 8px 20px rgba(16,24,40,.06)",
};
const panelStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 18,
  padding: 22,
  boxShadow: "0 8px 20px rgba(16,24,40,.06)",
  border: "1px solid #e4e7ec",
};
const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 13,
};
const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "10px 9px",
  background: "#f8fafc",
  color: "#344054",
  borderBottom: "1px solid #e4e7ec",
};
const tdStyle: React.CSSProperties = {
  padding: "12px 9px",
  borderBottom: "1px solid #edf0f3",
  verticalAlign: "top",
  color: "#344054",
};
const modalBackdropStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,.55)",
  zIndex: 50,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: 24,
};
const modalStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 18,
  padding: 24,
  width: "min(1060px,96vw)",
  maxHeight: "88vh",
  overflow: "auto",
  boxShadow: "0 24px 60px rgba(0,0,0,.26)",
};
const previewBoxStyle: React.CSSProperties = {
  border: "1px solid #e4e7ec",
  background: "#f8fafc",
  borderRadius: 14,
  padding: 16,
  minHeight: 320,
};
const labelStyle: React.CSSProperties = {
  fontWeight: 800,
  color: "#344054",
  fontSize: 13,
};
const suggestionBadgeStyle: React.CSSProperties = {
  display: "inline-block",
  marginTop: 6,
  padding: "5px 8px",
  borderRadius: 999,
  background: "#fff7ed",
  color: "#c2410c",
  fontSize: 12,
  fontWeight: 800,
};
const okPillStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "4px 8px",
  borderRadius: 999,
  background: "#ecfdf3",
  color: "#067647",
  fontSize: 12,
  fontWeight: 800,
};
const dangerPillStyle: React.CSSProperties = {
  display: "inline-block",
  padding: "4px 8px",
  borderRadius: 999,
  background: "#fef3f2",
  color: "#b42318",
  fontSize: 12,
  fontWeight: 800,
};
