"use client";

import React, { useEffect, useState } from "react";
import AppShell from "../../components/AppShell";
import { adminFetch, API_BASE } from "../../lib/apiClient";

const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

const SOCIAL_PLATFORMS = [
  { value: "", label: "Todas as plataformas" },
  { value: "youtube", label: "YouTube" },
  { value: "instagram", label: "Instagram" },
  { value: "facebook", label: "Facebook" },
  { value: "x", label: "X / Twitter" },
  { value: "tiktok", label: "TikTok" },
  { value: "linkedin", label: "LinkedIn" },
 ];

function platformLabel(value: string) {
  return SOCIAL_PLATFORMS.find((platform) => platform.value === value)?.label || "Todas as plataformas";
}


type SocialSource = {
  id: string;
  platform: string;
  name: string;
  source_type: string;
  query?: string;
  active: boolean;
};

type SocialItem = {
  id: string;
  platform: string;
  title: string;
  author_name?: string;
  url?: string;
  published_at?: string;
  thumbnail_url?: string;
};

export default function SocialMonitorPage() {
  const [sources, setSources] = useState<SocialSource[]>([]);
  const [items, setItems] = useState<SocialItem[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [platformStatuses, setPlatformStatuses] = useState<any[]>([]);
  const [performanceRows, setPerformanceRows] = useState<any[]>([]);
  const [evolutionRows, setEvolutionRows] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const [manualQuery, setManualQuery] = useState("");
  const [filterSourceId, setFilterSourceId] = useState("");
  const [filterPlatform, setFilterPlatform] = useState("youtube");
  const [sourcePlatform, setSourcePlatform] = useState("youtube");
  const [filterQuery, setFilterQuery] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  function buildItemParams(limit = "50") {
    const params = new URLSearchParams();
    if (filterPlatform) params.set("platform", filterPlatform);
    params.set("limit", limit);
    if (filterSourceId) params.set("source_id", filterSourceId);
    if (filterQuery.trim()) params.set("q", filterQuery.trim());
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    return params;
  }

  function buildReportParams(limit = "100") {
    const params = new URLSearchParams();
    params.set("limit", limit);
      if (filterPlatform) params.set("platform", filterPlatform);
    if (filterSourceId) params.set("source_id", filterSourceId);
    if (filterQuery.trim()) params.set("q", filterQuery.trim());
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    return params;
  }

  async function loadData() {
    const [summaryRes, sourcesRes, itemsRes, runsRes, platformStatusRes, performanceRes, evolutionRes] = await Promise.all([
      adminFetch(`${API_BASE}/social/summary/${DEFAULT_PROJECT_ID}`, { cache: "no-store" }),
      adminFetch(`${API_BASE}/social/sources/${DEFAULT_PROJECT_ID}`, { cache: "no-store" }),
      adminFetch(`${API_BASE}/social/items/${DEFAULT_PROJECT_ID}?${buildItemParams("50").toString()}`, { cache: "no-store" }),
      adminFetch(`${API_BASE}/social/runs/${DEFAULT_PROJECT_ID}?limit=20`, { cache: "no-store" }),
      adminFetch(`${API_BASE}/social/platform-status/${DEFAULT_PROJECT_ID}`, { cache: "no-store" }),
      adminFetch(`${API_BASE}/social/performance/${DEFAULT_PROJECT_ID}?${buildItemParams("100").toString()}`, { cache: "no-store" }),
      adminFetch(`${API_BASE}/social/evolution/${DEFAULT_PROJECT_ID}?${buildItemParams("100").toString()}`, { cache: "no-store" }),
    ]);

    if (summaryRes.ok) setSummary(await summaryRes.json());
    if (sourcesRes.ok) setSources((await sourcesRes.json()).items || []);
    if (itemsRes.ok) setItems((await itemsRes.json()).items || []);
    if (runsRes.ok) setRuns((await runsRes.json()).items || []);
    if (platformStatusRes.ok) setPlatformStatuses((await platformStatusRes.json()).items || []);
    if (performanceRes.ok) setPerformanceRows((await performanceRes.json()).items || []);
    if (evolutionRes.ok) setEvolutionRows((await evolutionRes.json()).items || []);
  }

  useEffect(() => {
    loadData().catch((error) => setMessage(`Erro ao carregar Social Monitor: ${error}`));
  }, []);

  async function applyFilters() {
    setBusy(true);
    setMessage("Aplicando filtros...");

    try {
      await loadData();
      setMessage("Filtros aplicados. A lista exibida e os PDFs Social Premium V3 usarão este recorte.");
    } catch (error) {
      setMessage(`Erro ao aplicar filtros: ${error}`);
    } finally {
      setBusy(false);
    }
  }

  async function clearFilters() {
    setBusy(true);
    setMessage("Limpando filtros...");

    try {
      setFilterSourceId("");
      setFilterQuery("");
      setDateFrom("");
      setDateTo("");

      setTimeout(async () => {
        await loadData();
        setMessage("Filtros limpos. A lista e os PDFs voltaram ao recorte geral.");
        setBusy(false);
      }, 150);
    } catch (error) {
      setMessage(`Erro ao limpar filtros: ${error}`);
      setBusy(false);
    }
  }

  async function createSource(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");

    try {
      const res = await adminFetch(`${API_BASE}/social/sources`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: DEFAULT_PROJECT_ID,
          platform: sourcePlatform,
          name,
          source_type: "keyword",
          query: query || name,
          active: true,
          monitor_news: true,
          monitor_mentions: true,
          monitor_ads: false,
        }),
      });

      const payload = await res.json();
      setMessage(payload.message || (payload.success ? "Fonte social cadastrada." : "Falha ao cadastrar fonte."));
      setName("");
      setQuery("");
      await loadData();
    } catch (error) {
      setMessage(`Erro ao cadastrar fonte: ${error}`);
    } finally {
      setBusy(false);
    }
  }

  async function collectSocial(sourceId?: string, q?: string) {
    setBusy(true);
    setMessage("");

    const platform = filterPlatform || "youtube";
    const label = platformLabel(platform);

    try {
      if (!["youtube", "x"].includes(platform)) {
        setMessage(`Coleta manual para ${label} ainda não implementada. Cadastre a fonte normalmente; o conector será habilitado na próxima etapa.`);
        return;
      }

      const params = new URLSearchParams();
      params.set("max_results", platform === "x" ? "10" : "15");
      if (sourceId) params.set("source_id", sourceId);
      if (q) params.set("query", q);

      const endpoint = platform === "x" ? "x" : "youtube";

      const res = await adminFetch(`${API_BASE}/social/${endpoint}/collect/${DEFAULT_PROJECT_ID}?${params.toString()}`, {
        method: "POST",
      });

      const payload = await res.json();
      setMessage(payload.message || `Coleta ${label} finalizada.`);
      await loadData();
    } catch (error) {
      setMessage(`Erro na coleta ${label}: ${error}`);
    } finally {
      setBusy(false);
    }
  }



  function downloadEvolutionCsv() {
    const headers = ["Data", "Plataforma", "Itens", "Patrocinados", "Fontes", "Editorial medio", "Publicitario medio"];
    const rows = evolutionRows.map((row: any) => [
      row.date || "",
      platformLabel(row.platform),
      row.total_items || 0,
      row.sponsored_items || 0,
      row.sources_count || 0,
      row.avg_editorial_score ?? "",
      row.avg_ad_score ?? "",
    ]);
    const csv = [headers, ...rows]
      .map((line) => line.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(";"))
      .join(String.fromCharCode(10));
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "TVFISCAL_SOCIAL_EVOLUCAO_TEMPORAL.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }

  function downloadRankingCsv() {
    const headers = [
      "Tipo",
      "Nome",
      "Plataforma",
      "Itens",
      "Patrocinados",
      "Fontes ativas",
      "Total de fontes",
    ];

    const platformRows = platformRanking.map((row: any) => [
      "Plataforma",
      row.platform || "",
      row.platform || "",
      row.totalItems || 0,
      row.sponsoredItems || 0,
      row.activeSources || 0,
      row.totalSources || 0,
    ]);

    const sourceRows = sourceRanking.map((row: any) => [
      "Fonte",
      row.source_name || "",
      platformLabel(row.platform),
      row.total_items || 0,
      row.sponsored_items || 0,
      "",
      "",
    ]);

    const csv = [headers, ...platformRows, ...sourceRows]
      .map((line) => line.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(";"))
      .join(String.fromCharCode(10));

    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "TVFISCAL_SOCIAL_RANKING_EXECUTIVO.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }

  function downloadPerformanceCsv() {
    const headers = [
      "Plataforma",
      "Fonte",
      "Status",
      "Query",
      "Itens",
      "Patrocinados",
      "Editorial medio",
      "Publicitario medio",
      "Primeiro item",
      "Ultimo item",
    ];

    const rows = performanceRows.map((row) => [
      platformLabel(row.platform),
      row.source_name || "",
      row.active ? "Ativa" : "Inativa",
      row.query || "",
      row.total_items || 0,
      row.sponsored_items || 0,
      row.avg_editorial_score ?? "",
      row.avg_ad_score ?? "",
      row.first_item_at || "",
      row.last_item_at || "",
    ]);

    const csv = [headers, ...rows]
      .map((line) => line.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(";"))
      .join(String.fromCharCode(10));

    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "TVFISCAL_SOCIAL_DESEMPENHO_FONTE.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  }


  async function downloadConsolidatedReport() {
    setBusy(true);
    setMessage("");
    try {
      const res = await adminFetch(`${API_BASE}/social/reports/executive-consolidated-v3/${DEFAULT_PROJECT_ID}?${buildReportParams("100").toString()}`, {
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "TVFISCAL_SOCIAL_EXECUTIVO_CONSOLIDADO_PREMIUM_V3.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setMessage("Relatório Social Executivo Consolidado Premium V3 gerado com sucesso.");
    } catch (error) {
      setMessage(`Erro ao gerar relatório consolidado social: ${error}`);
    } finally {
      setBusy(false);
    }
  }

  async function downloadSocialReport(kind: "synthetic" | "analytic") {
    setBusy(true);
    setMessage("");

    try {
      const path = kind === "synthetic" ? "synthetic-v3" : "analytic-v3";
      const filename = kind === "synthetic"
        ? "TVFISCAL_SOCIAL_SINTETICO_PREMIUM_V3.pdf"
        : "TVFISCAL_SOCIAL_ANALITICO_PREMIUM_V3.pdf";

      const res = await adminFetch(`${API_BASE}/social/reports/${path}/${DEFAULT_PROJECT_ID}?${buildReportParams("100").toString()}`, {
        cache: "no-store",
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setMessage("Relatório Social Premium V3 gerado com sucesso.");
    } catch (error) {
      setMessage(`Erro ao gerar relatório social: ${error}`);
    } finally {
      setBusy(false);
    }
  }

  const total = summary?.summary || {};
  const latestRun = runs?.[0] || null;
  const latestRunMessage = latestRun?.message || "Nenhuma coleta automática registrada ainda.";
  const latestRunCollected = latestRun ? `${latestRun.collected || 0} coletados / ${latestRun.saved || 0} salvos` : "0 coletados / 0 salvos";
  const latestRunStatus = latestRun?.status || "sem registro";
  const latestRunPlatform = platformLabel(latestRun?.platform || "youtube");

  function formatDateTime(value?: string) {
    if (!value) return "sem registro";
    const parsed = new Date(String(value).replace(" ", "T"));
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleString("pt-BR");
  }

  function nextCronRunLabel() {
    const next = new Date();
    if (next.getMinutes() < 30) {
      next.setMinutes(30, 1, 0);
    } else {
      next.setHours(next.getHours() + 1, 0, 1, 0);
    }
    return next.toLocaleString("pt-BR");
  }



  function formatDateBR(value: string) {
    if (!value) return "";
    const parts = value.split("-");
    if (parts.length !== 3) return value;
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }

  function currentFilterSummary() {
    const selectedSource = sources.find((source) => source.id === filterSourceId);
    const selectedPlatform = platformLabel(filterPlatform || "youtube");
    const parts = [];

    parts.push(`Plataforma: ${selectedPlatform}`);
    parts.push(`Fonte: ${selectedSource ? selectedSource.name : "Todas as fontes da plataforma"}`);

    if (filterQuery.trim()) {
      parts.push(`Termo: ${filterQuery.trim()}`);
    }

    if (dateFrom || dateTo) {
      parts.push(`Período: ${dateFrom ? formatDateBR(dateFrom) : "início"} a ${dateTo ? formatDateBR(dateTo) : "hoje"}`);
    }

    if (!filterSourceId && !filterQuery.trim() && !dateFrom && !dateTo) {
      return `Recorte atual: ${selectedPlatform}, todas as fontes da plataforma, sem termo ou período restrito.`;
    }

    return `Recorte atual: ${parts.join(" · ")}`;
  }

  const fallbackConnectorStatuses = [
    { platform: "YouTube", status: "Ativo", detail: "Coleta automática via cron a cada 30 minutos.", state: "active" },
    { platform: "X / Twitter", status: "Preparado", detail: "Backend, rota e script prontos. Aguardando X_BEARER_TOKEN.", state: "ready" },
    { platform: "Instagram", status: "Pendente", detail: "Fonte já pode ser cadastrada. Coletor será implementado em fase posterior.", state: "pending" },
    { platform: "Facebook", status: "Pendente", detail: "Fonte já pode ser cadastrada. Coletor será implementado em fase posterior.", state: "pending" },
    { platform: "TikTok", status: "Pendente", detail: "Fonte já pode ser cadastrada. Coletor será implementado em fase posterior.", state: "pending" },
    { platform: "LinkedIn", status: "Pendente", detail: "Fonte já pode ser cadastrada. Coletor será implementado em fase posterior.", state: "pending" },
  ];

  const connectorStatuses = (platformStatuses.length ? platformStatuses : fallbackConnectorStatuses).map((connector: any) => {
    const totalSources = Number(connector.total_sources ?? 0);
    const activeSources = Number(connector.active_sources ?? 0);
    const totalItems = Number(connector.total_items ?? 0);
    const sponsoredItems = Number(connector.sponsored_items ?? 0);
    const lastRunStatus = connector.last_run_status || "sem execução";
    const lastRunWhen = connector.last_run_started_at ? formatDateTime(connector.last_run_started_at) : "sem registro";
    const lastRunCollected = Number(connector.last_run_collected ?? 0);
    const lastRunSaved = Number(connector.last_run_saved ?? 0);

    return {
      platform: connector.label || connector.platform || "Social",
      status: connector.connector_status || connector.status || "Pendente",
      state: connector.connector_state || connector.state || "pending",
      metrics: `Fontes: ${activeSources}/${totalSources} ativas · Itens: ${totalItems} · Patrocinados: ${sponsoredItems}`,
      lastRun: `Última execução: ${lastRunStatus} · ${lastRunCollected} coletados / ${lastRunSaved} salvos · ${lastRunWhen}`,
      detail: connector.last_run_message || connector.detail || "Sem registro operacional.",
    };
  });


  const platformRanking = (platformStatuses || [])
    .map((row: any) => ({
      platform: row.label || platformLabel(row.platform),
      totalItems: Number(row.total_items || 0),
      sponsoredItems: Number(row.sponsored_items || 0),
      activeSources: Number(row.active_sources || 0),
      totalSources: Number(row.total_sources || 0),
    }))
    .sort((a: any, b: any) => b.totalItems - a.totalItems);

  const sourceRanking = [...performanceRows]
    .sort((a: any, b: any) => Number(b.total_items || 0) - Number(a.total_items || 0))
    .slice(0, 10);

  const maxPlatformItems = Math.max(1, ...platformRanking.map((row: any) => row.totalItems));
  const maxSourceItems = Math.max(1, ...sourceRanking.map((row: any) => Number(row.total_items || 0)));

  const executiveSocialKpis = [
    { label: "Total no recorte", value: Number(total.total_items || 0) },
    { label: "Fontes ativas", value: platformRanking.reduce((acc: number, row: any) => acc + Number(row.activeSources || 0), 0) },
    { label: "Plataforma líder", value: platformRanking[0]?.platform || "sem dados" },
    { label: "Fonte líder", value: sourceRanking[0]?.source_name || "sem dados" },
    { label: "Patrocinados", value: Number(total.sponsored_items || 0) },
    { label: "Dias com coleta", value: evolutionRows.length },
  ];

  return (
    <AppShell title="Social Monitor" subtitle="Coleta de vídeos, posts, menções e conteúdos sociais — base multiplataforma">
      <section style={heroStyle}>
        <div>
          <div style={kickerStyle}>TV FISCAL WEBMONITOR · SOCIAL INTELLIGENCE</div>
          <h2 style={titleStyle}>Monitoramento social e audiovisual</h2>
          <p style={textStyle}>
            Módulo social com base multiplataforma para coleta, análise e geração de relatórios Premium V3.
            YouTube já opera em rotina automática; X / Twitter está preparado para ativação com token de API.
          </p>
        </div>
        <div style={statsGridStyle}>
          <Card label="Itens sociais" value={total.total_items || 0} />
          <Card label="YouTube" value={total.youtube_items || 0} />
          <Card label="Fontes com itens" value={total.sources_with_items || 0} />
          <Card label="Patrocinados" value={total.sponsored_items || 0} />
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={panelTitleStyle}>Visão Executiva Consolidada</h3>
        <p style={helpStyle}>Resumo superior do desempenho social, integrando volume, fontes, ranking e evolução temporal.</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginTop: 14 }}>
          {executiveSocialKpis.map((kpi) => (
            <div key={kpi.label} style={autoCardStyle}>
              <strong>{kpi.value}</strong>
              <span>{kpi.label}</span>
            </div>
          ))}
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={panelTitleStyle}>Status dos Conectores Sociais</h3>
        <p style={helpStyle}>Visão operacional das plataformas já ativas, preparadas ou pendentes no Social Monitor.</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 12, marginTop: 14 }}>
          {connectorStatuses.map((connector) => (
            <div
              key={connector.platform}
              style={{
                ...autoCardStyle,
                borderColor: connector.state === "active" ? "#86efac" : connector.state === "ready" ? "#fdba74" : "#e5e7eb",
                background: connector.state === "active" ? "#f0fdf4" : connector.state === "ready" ? "#fff7ed" : "#f8fafc",
              }}
            >
              <strong>{connector.platform}</strong>
              <span style={{ fontWeight: 900 }}>{connector.status}</span>
              <span>{connector.metrics}</span>
              <span>{connector.lastRun}</span>
              <span>{connector.detail}</span>
            </div>
          ))}
        </div>
      </section>

      {message ? <div style={messageStyle}>{message}</div> : null}

        <section style={panelStyle}>
          <h3 style={panelTitleStyle}>Coleta automática Social</h3>
          <p style={helpStyle}>
            Rotina automática ativa via cron da VPS. YouTube já opera a cada 30 minutos; X / Twitter está preparado para ativação com token de API.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginTop: 14 }}>
            <div style={autoCardStyle}>
              <strong>{latestRunStatus}</strong>
              <span>Status da última coleta</span>
            </div>
            <div style={autoCardStyle}>
              <strong>{latestRunPlatform}</strong>
              <span>Plataforma monitorada</span>
            </div>
            <div style={autoCardStyle}>
              <strong>{latestRunCollected}</strong>
              <span>Total do último ciclo</span>
            </div>
            <div style={autoCardStyle}>
              <strong>{formatDateTime(latestRun?.started_at)}</strong>
              <span>Última execução</span>
            </div>
            <div style={autoCardStyle}>
              <strong>{nextCronRunLabel()}</strong>
              <span>Próxima execução estimada</span>
            </div>
          </div>
          <p style={{ ...helpStyle, marginTop: 12 }}>{latestRunMessage}</p>
        </section>

      <section style={panelStyle}>
        <h3 style={panelTitleStyle}>Relatórios Social Premium V3</h3>
        <p style={helpStyle}>
          Gere PDFs executivos com KPIs, canais, vídeos coletados, histórico e evidências por URL.
        </p>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 14 }}>
          <button style={buttonStyle} disabled={busy} onClick={() => downloadSocialReport("synthetic")}>
            Baixar Sintético Social V3
          </button>
          <button style={buttonStyle} disabled={busy} onClick={() => downloadSocialReport("analytic")}>
            Baixar Analítico Social V3
          </button>
          <button style={{ ...buttonStyle, background: "#111827" }} disabled={busy} onClick={downloadConsolidatedReport}>
            Baixar Executivo Consolidado Social V3
          </button>
            <a href="/social-sources" style={{ ...buttonStyle, textDecoration: "none", display: "inline-block", background: "#7c3aed" }}>
              Gestão de Fontes Sociais
            </a>
              <a href="/reports-history?report_family=social&report_type=executive_consolidated_v3" style={{ ...buttonStyle, textDecoration: "none", display: "inline-block", background: "#475467" }}>
                Histórico Social
              </a>
        </div>
      </section>

        <section style={panelStyle}>
          <h3 style={panelTitleStyle}>Filtros de consulta e relatórios</h3>
          <p style={helpStyle}>Os filtros abaixo afetam os últimos conteúdos exibidos na tela e os PDFs Social Premium V3.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 12, marginTop: 14 }}>
              <select style={inputStyle} value={filterPlatform} onChange={(e) => { setFilterPlatform(e.target.value); setFilterSourceId(""); }}>
                {SOCIAL_PLATFORMS.map((platform) => (
                  <option key={platform.value || "all"} value={platform.value}>{platform.label}</option>
                ))}
              </select>

            <select style={inputStyle} value={filterSourceId} onChange={(e) => setFilterSourceId(e.target.value)}>
              <option value="">Todas as fontes da plataforma</option>
              {sources.filter((source) => !filterPlatform || source.platform === filterPlatform).map((source) => (
                <option key={source.id} value={source.id}>{source.name}{source.active ? "" : " (inativa)"}</option>
              ))}
            </select>
            <input style={inputStyle} placeholder="Termo. Ex.: Campina, Juazeiro, São João" value={filterQuery} onChange={(e) => setFilterQuery(e.target.value)} />
            <input style={inputStyle} type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            <input style={inputStyle} type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 14 }}>
            <button style={buttonStyle} disabled={busy} onClick={applyFilters}>{busy ? "Aplicando..." : "Aplicar filtros"}</button>
            <button style={{ ...buttonStyle, background: "#374151" }} disabled={busy} onClick={clearFilters}>Limpar filtros</button>
          </div>
          <p style={{ ...helpStyle, marginTop: 12, fontWeight: 800, color: "#111827" }}>{currentFilterSummary()}</p>
        </section>

      <section style={panelStyle}>
        <h3 style={panelTitleStyle}>Ranking Social Executivo</h3>
        <p style={helpStyle}>Ranking visual de plataformas e fontes sociais conforme o recorte aplicado.</p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12, marginBottom: 12 }}>
          <button style={smallButtonStyle} disabled={platformRanking.length === 0 && sourceRanking.length === 0} onClick={downloadRankingCsv}>
            Exportar Ranking CSV
          </button>
        </div>
        <div style={gridStyle}>
          <div>
            <h4 style={{ margin: "0 0 10px", color: "#111827" }}>Plataformas</h4>
            <div style={listStyle}>
              {platformRanking.length === 0 ? <p style={emptyStyle}>Nenhuma plataforma com dados.</p> : platformRanking.map((row: any) => (
                <div key={row.platform} style={rowStyle}>
                  <div style={{ width: "100%" }}>
                    <strong>{row.platform}</strong>
                    <div style={mutedStyle}>Itens: {row.totalItems} · Patrocinados: {row.sponsoredItems} · Fontes ativas: {row.activeSources}/{row.totalSources}</div>
                    <div style={barTrackStyle}><div style={{ ...barFillStyle, width: `${Math.max(4, (row.totalItems / maxPlatformItems) * 100)}%` }} /></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h4 style={{ margin: "0 0 10px", color: "#111827" }}>Fontes</h4>
            <div style={listStyle}>
              {sourceRanking.length === 0 ? <p style={emptyStyle}>Nenhuma fonte com dados.</p> : sourceRanking.map((row: any) => (
                <div key={`${row.platform}-${row.source_id}`} style={rowStyle}>
                  <div style={{ width: "100%" }}>
                    <strong>{row.source_name}</strong>
                    <div style={mutedStyle}>{platformLabel(row.platform)} · Itens: {row.total_items || 0} · Patrocinados: {row.sponsored_items || 0}</div>
                    <div style={barTrackStyle}><div style={{ ...barFillStyle, width: `${Math.max(4, (Number(row.total_items || 0) / maxSourceItems) * 100)}%` }} /></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={panelTitleStyle}>Desempenho por Fonte</h3>
        <p style={helpStyle}>Resumo analítico por plataforma, fonte e período aplicado nos filtros.</p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12, marginBottom: 12 }}>
          <button style={smallButtonStyle} disabled={performanceRows.length === 0} onClick={downloadPerformanceCsv}>
            Exportar CSV
          </button>
        </div>
        <div style={listStyle}>
          {performanceRows.length === 0 ? (
            <p style={emptyStyle}>Nenhum dado de desempenho encontrado para o recorte atual.</p>
          ) : performanceRows.map((row) => (
            <div key={row.source_id} style={rowStyle}>
              <div>
                <strong>{row.source_name}</strong>
                <div style={mutedStyle}>{platformLabel(row.platform)} · {row.active ? "Ativa" : "Inativa"} · Query: {row.query || "sem query"}</div>
                <div style={mutedStyle}>Itens: {row.total_items || 0} · Patrocinados: {row.sponsored_items || 0} · Editorial médio: {row.avg_editorial_score ?? "—"} · Publicitário médio: {row.avg_ad_score ?? "—"}</div>
                <div style={mutedStyle}>Período coletado: {formatDateTime(row.first_item_at)} até {formatDateTime(row.last_item_at)}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={panelTitleStyle}>Evolução Temporal Social</h3>
        <p style={helpStyle}>Volume diário coletado por plataforma no recorte atual.</p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12, marginBottom: 12 }}>
          <button style={smallButtonStyle} disabled={evolutionRows.length === 0} onClick={downloadEvolutionCsv}>
            Exportar Evolução CSV
          </button>
        </div>
        <div style={listStyle}>
          {evolutionRows.length === 0 ? (
            <p style={emptyStyle}>Nenhuma evolução temporal encontrada para o recorte atual.</p>
          ) : evolutionRows.slice(-15).map((row) => (
            <div key={`${row.date}-${row.platform}`} style={rowStyle}>
              <div style={{ width: "100%" }}>
                <strong>{formatDateBR(String(row.date))} · {platformLabel(row.platform)}</strong>
                <div style={mutedStyle}>Itens: {row.total_items || 0} · Patrocinados: {row.sponsored_items || 0} · Fontes: {row.sources_count || 0}</div>
                <div style={{ height: 8, background: "#e5e7eb", borderRadius: 999, marginTop: 8, overflow: "hidden" }}>
                  <div style={{ height: 8, width: `${Math.max(4, ((row.total_items || 0) / Math.max(1, ...evolutionRows.map((item) => item.total_items || 0))) * 100)}%`, background: "#b00020", borderRadius: 999 }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section style={gridStyle}>
        <div style={panelStyle}>
          <h3 style={panelTitleStyle}>Cadastrar fonte social</h3>
          <form onSubmit={createSource} style={{ display: "grid", gap: 12 }}>
              <select style={inputStyle} value={sourcePlatform} onChange={(e) => setSourcePlatform(e.target.value)}>
                {SOCIAL_PLATFORMS.filter((platform) => platform.value).map((platform) => (
                  <option key={platform.value} value={platform.value}>{platform.label}</option>
                ))}
              </select>
              <p style={{ ...helpStyle, marginTop: -6 }}>Escolha a plataforma antes de cadastrar a fonte.</p>

            <input style={inputStyle} placeholder="Nome da fonte. Ex.: São João Juazeiro" value={name} onChange={(e) => setName(e.target.value)} required />
            <input style={inputStyle} placeholder="Termo de busca. Ex.: Juazeiro Bahia" value={query} onChange={(e) => setQuery(e.target.value)} />
            <button style={buttonStyle} disabled={busy}>{busy ? "Processando..." : "Cadastrar fonte"}</button>
          </form>
        </div>

        <div style={panelStyle}>
          <h3 style={panelTitleStyle}>Coleta rápida por plataforma</h3>
          <div style={{ display: "grid", gap: 12 }}>
            <input style={inputStyle} placeholder="Digite termo para coletar agora" value={manualQuery} onChange={(e) => setManualQuery(e.target.value)} />
            <button style={buttonStyle} disabled={busy || !manualQuery.trim()} onClick={() => collectSocial(undefined, manualQuery)}>
              Coletar agora
            </button>
            <p style={helpStyle}>Necessário configurar YOUTUBE_API_KEY no servidor.</p>
          </div>
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={panelTitleStyle}>Fontes cadastradas</h3>
        <div style={listStyle}>
          {sources.length === 0 ? <p style={emptyStyle}>Nenhuma fonte social cadastrada.</p> : sources.map((source) => (
            <div key={source.id} style={rowStyle}>
              <div>
                <strong>{source.name}</strong>
                <div style={mutedStyle}>{source.platform} · {source.source_type} · {source.query || "sem query"}</div>
              </div>
              <button style={smallButtonStyle} disabled={busy} onClick={() => collectSocial(source.id)}>
                Coletar
              </button>
            </div>
          ))}
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={panelTitleStyle}>Últimos conteúdos coletados</h3>
        <div style={cardsStyle}>
          {items.length === 0 ? <p style={emptyStyle}>Nenhum conteúdo coletado.</p> : items.map((item) => (
            <a key={item.id} href={item.url || "#"} target="_blank" rel="noreferrer" style={itemCardStyle}>
              {item.thumbnail_url ? <img src={item.thumbnail_url} alt="" style={thumbStyle} /> : null}
              <div>
                <strong>{item.title}</strong>
                <div style={mutedStyle}>{item.author_name || "Canal não identificado"} · {item.platform}</div>
                <div style={mutedStyle}>{item.published_at || ""}</div>
              </div>
            </a>
          ))}
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={panelTitleStyle}>Histórico de coletas sociais</h3>
        <div style={listStyle}>
          {runs.length === 0 ? <p style={emptyStyle}>Nenhuma coleta registrada.</p> : runs.map((run) => (
            <div key={run.id} style={rowStyle}>
              <div>
                <strong>{run.status}</strong>
                <div style={mutedStyle}>{run.platform} · coletados: {run.collected} · salvos: {run.saved}</div>
                <div style={mutedStyle}>{run.message}</div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </AppShell>
  );
}

function Card({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={cardStyle}>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

const heroStyle: React.CSSProperties = { background: "linear-gradient(135deg,#9f1027,#d62b44)", color: "#fff", borderRadius: 24, padding: 28, display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: 24, marginBottom: 22 };
const kickerStyle: React.CSSProperties = { fontSize: 12, fontWeight: 900, letterSpacing: 1.2, opacity: 0.9 };
const titleStyle: React.CSSProperties = { fontSize: 32, margin: "10px 0" };
const textStyle: React.CSSProperties = { fontSize: 15, lineHeight: 1.6, maxWidth: 760 };
const statsGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 12 };
const cardStyle: React.CSSProperties = { background: "rgba(255,255,255,0.14)", border: "1px solid rgba(255,255,255,0.25)", borderRadius: 16, padding: 16, display: "grid", gap: 6 };
const gridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 18, marginBottom: 18 };
const panelStyle: React.CSSProperties = { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 20, padding: 20, boxShadow: "0 10px 24px rgba(15,23,42,0.06)", marginBottom: 18 };
const panelTitleStyle: React.CSSProperties = { margin: "0 0 14px", color: "#111827" };
const inputStyle: React.CSSProperties = { border: "1px solid #d1d5db", borderRadius: 12, padding: "12px 14px", fontSize: 14 };
const buttonStyle: React.CSSProperties = { border: 0, borderRadius: 12, padding: "12px 16px", background: "#b00020", color: "#fff", fontWeight: 900, cursor: "pointer" };
const smallButtonStyle: React.CSSProperties = { ...buttonStyle, padding: "9px 12px", fontSize: 12 };
const messageStyle: React.CSSProperties = { background: "#fff7ed", border: "1px solid #fed7aa", color: "#9a3412", borderRadius: 14, padding: 14, marginBottom: 18 };
const helpStyle: React.CSSProperties = { color: "#6b7280", fontSize: 12, margin: 0 };
const listStyle: React.CSSProperties = { display: "grid", gap: 10 };
const rowStyle: React.CSSProperties = { display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", padding: 12, border: "1px solid #eef2f7", borderRadius: 14 };
const mutedStyle: React.CSSProperties = { color: "#6b7280", fontSize: 12, marginTop: 4 };
const emptyStyle: React.CSSProperties = { color: "#6b7280" };
const cardsStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))", gap: 14 };
const itemCardStyle: React.CSSProperties = { color: "#111827", textDecoration: "none", border: "1px solid #eef2f7", borderRadius: 16, overflow: "hidden", background: "#fff", display: "grid" };
const thumbStyle: React.CSSProperties = { width: "100%", height: 145, objectFit: "cover", background: "#f3f4f6" };

const autoCardStyle: React.CSSProperties = { border: "1px solid #e5e7eb", borderRadius: 16, padding: 14, display: "grid", gap: 6, background: "#f8fafc", color: "#0f172a" };

const barTrackStyle: React.CSSProperties = { height: 8, background: "#e5e7eb", borderRadius: 999, marginTop: 8, overflow: "hidden" };
const barFillStyle: React.CSSProperties = { height: 8, background: "#b00020", borderRadius: 999 };
