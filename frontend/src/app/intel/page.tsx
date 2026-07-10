"use client";

import { useEffect, useState } from "react";
import AppShell from "../../components/AppShell";
import { adminFetch, API_BASE } from "../../lib/apiClient";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const API = API_BASE;

const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";


function authorizedFetch(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = 20000) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);

  const url =
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.toString()
        : input.url;

  return adminFetch(url, {
    ...init,
    signal: init.signal || controller.signal,
    bearer: true,
    admin: true,
    json: false,
  }).finally(() => window.clearTimeout(timeout));
}


async function fetchJsonSafely(url: string, timeoutMs = 20000) {
  const res = await authorizedFetch(url, {}, timeoutMs);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Erro HTTP ${res.status}: ${body || res.statusText}`);
  }
  return res.json();
}

async function downloadWithAuth(url: string, filenameFallback: string) {
  const res = await authorizedFetch(url);
  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`Erro ao gerar arquivo: ${res.status} ${msg}`);
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

function getProjectIdFromUrl() {
  if (typeof window === "undefined") return DEFAULT_PROJECT_ID;
  const value = new URLSearchParams(window.location.search).get("project_id");
  return value || DEFAULT_PROJECT_ID;
}

function formatBRL(value: any) {
  return Number(value || 0).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

function formatSignedBRL(value: any) {
  const n = Number(value || 0);
  const prefix = n > 0 ? "+" : "";
  return `${prefix}${formatBRL(n)}`;
}

function formatPct(value: any) {
  return `${Number(value || 0).toFixed(1)}%`;
}

function formatSignedPp(value: any) {
  const n = Number(value || 0);
  const prefix = n > 0 ? "+" : "";
  return `${prefix}${n.toFixed(2)} p.p.`;
}

function formatDate(value: any) {
  if (!value) return "Sem data";

  let normalizedValue = String(value);

  const looksLikeIsoWithoutTimezone =
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(normalizedValue) &&
    !normalizedValue.endsWith("Z") &&
    !normalizedValue.includes("+");

  if (looksLikeIsoWithoutTimezone) {
    normalizedValue = `${normalizedValue}Z`;
  }

  const d = new Date(normalizedValue);

  if (Number.isNaN(d.getTime())) {
    return String(value);
  }

  return d.toLocaleString("pt-BR");
}

function shortDate(value: any) {
  if (!value) return "";

  const d = new Date(value);

  if (Number.isNaN(d.getTime())) {
    return String(value);
  }

  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });
}

function formatBannerSize(item: any) {
  const width = item.width || item.normalized_width || 0;
  const height = item.height || item.normalized_height || 0;

  if (!width || !height) {
    return "Formato não identificado";
  }

  return `${width} x ${height}`;
}

function getPreservedEvidenceUrl(item: any) {
  return (
    item.screenshot_banner_url ||
    item.screenshot_page_url ||
    item.evidence_html_url ||
    ""
  );
}

function getDetectedImageUrl(item: any) {
  return item.image_url || "";
}

function getEvidenceStatus(item: any) {
  const status = String(item.checking_status || "").toLowerCase();

  if (status === "auditavel") return "Auditável";
  if (status === "parcial") return "Parcial";
  if (status === "revisao") return "Revisão";
  if (status === "rejeitado") return "Rejeitado";

  if (item.news_status === "candidato") return "Notícia candidata";
  if (item.market_status === "incluido") return "Mercado";

  if (item.screenshot_banner_url || item.screenshot_page_url) return "Parcial";
  if (item.evidence_html_url || item.image_url) return "Referencial";
  if (item.page_url) return "Referencial";

  return "Sem evidência";
}

function getContentTypeLabel(item: any) {
  const contentType = String(item.content_type || "").toLowerCase();

  if (contentType === "advertising") return "Publicidade";
  if (contentType === "news") return "Notícia";
  if (contentType === "mixed") return "Misto";
  if (contentType === "institutional") return "Institucional";
  return "Indefinido";
}
function evidenceStatusStyle(status: string) {
  const background =
    status === "Auditável"
      ? "#198754"
      : status === "Parcial"
      ? "#f0ad4e"
      : status === "Revisão"
      ? "#6f42c1"
      : status === "Notícia candidata"
      ? "#0d6efd"
      : status === "Mercado"
      ? "#1f4e79"
      : status === "Rejeitado"
      ? "#6c757d"
      : status === "Referencial"
      ? "#6c757d"
      : "#999";

  return {
    display: "inline-block",
    padding: "4px 8px",
    borderRadius: 6,
    color: "#fff",
    background,
    fontSize: 12,
    fontWeight: "bold",
    whiteSpace: "nowrap" as const,
  };
}
export default function IntelPage() {
  const [data, setData] = useState<any>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [timelineAnalysis, setTimelineAnalysis] = useState<any>(null);
  const [evidences, setEvidences] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [auxWarning, setAuxWarning] = useState<string | null>(null);
  const [segments, setSegments] = useState<any[]>([]);
  const [advertisers, setAdvertisers] = useState<any[]>([]);
  const [selectedSegment, setSelectedSegment] = useState("");
  const [selectedAdvertiser, setSelectedAdvertiser] = useState("");
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);

  useEffect(() => {
        setProjectId(getProjectIdFromUrl());
  }, []);

  useEffect(() => {

    async function loadData() {
      setError(null);
      setAuxWarning(null);

      try {
        const params = new URLSearchParams();
        if (selectedSegment) params.set("segment_id", selectedSegment);
        if (selectedAdvertiser) params.set("advertiser_id", selectedAdvertiser);
        const query = params.toString() ? `?${params.toString()}` : "";

        // A tela principal depende apenas do resumo. Carrega e renderiza primeiro.
        const summaryJson = await fetchJsonSafely(`${API}/intel/summary/${projectId}${query}`, 30000);
        setData(summaryJson);

        // Dados complementares não podem travar o painel Intel.
        const evidenceQuery = `${API}/banners/${projectId}?limit=50${selectedSegment ? `&segment_id=${selectedSegment}` : ""}${selectedAdvertiser ? `&registry_advertiser_id=${selectedAdvertiser}` : ""}`;
        const results = await Promise.allSettled([
          fetchJsonSafely(`${API}/intel/timeline/${projectId}`, 15000),
          fetchJsonSafely(evidenceQuery, 30000),
          fetchJsonSafely(`${API}/registry/segments`, 15000),
          fetchJsonSafely(`${API}/registry/advertisers`, 15000),
        ]);

        const warnings: string[] = [];

        const timelineResult = results[0];
        if (timelineResult.status === "fulfilled") {
          const timelineJson = timelineResult.value;
          setTimeline(Array.isArray(timelineJson.points) ? [...timelineJson.points] : []);
          setTimelineAnalysis(timelineJson.analysis || null);
        } else {
          warnings.push("histórico temporal");
          console.warn("Falha ao carregar histórico temporal", timelineResult.reason);
        }

        const evidenceResult = results[1];
        if (evidenceResult.status === "fulfilled") {
          const evidenceJson = evidenceResult.value;
          setEvidences(Array.isArray(evidenceJson) ? evidenceJson : []);
        } else {
          warnings.push("evidências monitoradas");
          console.warn("Falha ao carregar evidências", evidenceResult.reason);
        }

        const segmentsResult = results[2];
        if (segmentsResult.status === "fulfilled") {
          setSegments(Array.isArray(segmentsResult.value) ? segmentsResult.value : []);
        } else {
          warnings.push("segmentos");
          console.warn("Falha ao carregar segmentos", segmentsResult.reason);
        }

        const advertisersResult = results[3];
        if (advertisersResult.status === "fulfilled") {
          setAdvertisers(Array.isArray(advertisersResult.value) ? advertisersResult.value : []);
        } else {
          warnings.push("anunciantes cadastrados");
          console.warn("Falha ao carregar anunciantes", advertisersResult.reason);
        }

        if (warnings.length > 0) {
          setAuxWarning(`Painel carregado, mas houve falha temporária em: ${warnings.join(", ")}.`);
        }
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Erro desconhecido ao carregar o resumo Intel. Verifique sessão, permissões e logs do backend."
        );
      }
    }

    loadData();
  }, [selectedSegment, selectedAdvertiser, projectId]);

  if (error) {
    return (
      <AppShell title="Inteligência de Mercado" subtitle="Painel Intel com KPIs, evidências, qualidade de identificação e relatórios.">
        <main style={{ padding: 20, color: "red", fontFamily: "Arial" }}>
          {error}
        </main>
      </AppShell>
    );
  }

  if (!data) {
    return (
      <AppShell title="Inteligência de Mercado" subtitle="Painel Intel com KPIs, evidências, qualidade de identificação e relatórios.">
        <main style={{ padding: 20, fontFamily: "Arial" }}>
          Carregando...
        </main>
      </AppShell>
    );
  }

  const identifiedShare = data.share_of_voice_identified || (data.share_of_voice || []).filter((item: any) => !String(item.advertiser || "").toLowerCase().includes("nao identificado") && !String(item.advertiser || "").toLowerCase().includes("não identificado"));
  const idQuality = data.identification_quality || {};
  const topAdv = identifiedShare?.[0] || {};
  const topPortal = data.portal_ranking?.[0] || {};

  const chartData = [...timeline].slice(-12).map((point: any) => ({
    label: shortDate(point.created_at),
    created_at: point.created_at,
    investment: Number(point.total_investment || 0),
    leaderShare: Number(point.top_advertiser_share || 0),
  }));

  const deltas = timelineAnalysis?.deltas || {};

  const investmentDelta = Number(deltas.investment_delta || 0);
  const shareDelta = Number(deltas.share_delta || 0);

  const currentLeader =
    deltas.current_leader || topAdv.advertiser || "Sem dados";

  const previousLeader = deltas.previous_leader || "Sem dados";

  const trendInsights = Array.isArray(timelineAnalysis?.insights)
    ? timelineAnalysis.insights
    : [];

  const reportParams = new URLSearchParams();
  if (selectedSegment) reportParams.set("segment_id", selectedSegment);
  if (selectedAdvertiser) reportParams.set("advertiser_id", selectedAdvertiser);
  const reportQuery = reportParams.toString() ? `?${reportParams.toString()}` : "";

  const completeReportParams = new URLSearchParams();
  completeReportParams.set("analysis_mode", "market_wide");
  const completeReportQuery = `?${completeReportParams.toString()}`;

  const evidenceStats = evidences.reduce(
    (acc: any, item: any) => {
      const status = getEvidenceStatus(item);
      acc.Total = (acc.Total || 0) + 1;
      acc[status] = (acc[status] || 0) + 1;
      return acc;
    },
    {
      Auditável: 0,
      Parcial: 0,
      Revisão: 0,
      "Notícia candidata": 0,
      Mercado: 0,
      Rejeitado: 0,
      Referencial: 0,
      "Sem evidência": 0,
      Total: 0,
    }
  );

  const filteredAdvertisers = selectedSegment
    ? advertisers.filter((advertiser: any) => advertiser.segment_id === selectedSegment)
    : advertisers;

  const strategicNote =
    currentLeader !== previousLeader && previousLeader !== "Sem dados"
      ? [
          `Houve troca de liderança: ${previousLeader} perdeu posição para ${currentLeader}.`,
          "Recomenda-se avaliar os canais onde ocorreu a virada competitiva.",
          "A mudança pode indicar reposicionamento de verba ou ampliação de presença.",
        ]
      : investmentDelta > 0
      ? [
          `${currentLeader} manteve a liderança com expansão do investimento monitorado.`,
          "O movimento sugere aumento de pressão competitiva no curto prazo.",
          "Recomenda-se monitorar frequência, portais e share por segmento.",
        ]
      : investmentDelta < 0
      ? [
          `${currentLeader} manteve a liderança, mas com retração no investimento monitorado.`,
          "A queda pode abrir oportunidade para avanço de concorrentes.",
          "Recomenda-se observar portais com menor saturação.",
        ]
      : [
          "O cenário permaneceu estável entre os snapshots comparados.",
          "A estabilidade indica baixa movimentação competitiva no período.",
          "Recomenda-se ampliar a janela temporal para leitura mais precisa.",
        ];

  return (
    <AppShell title="Inteligência de Mercado" subtitle="Painel Intel com KPIs, evidências, qualidade de identificação e relatórios.">
    <main
      style={{
        padding: 30,
        fontFamily: "Arial",
        background: "#f5f6fa",
        minHeight: "100vh",
      }}
    >
      <h1 style={{ marginBottom: 0 }}>TV Fiscal WebMonitor</h1>

      <p style={{ marginTop: 5, color: "#666" }}>
        Inteligência de Mercado Publicitário
      </p>

      {auxWarning && (
        <div style={{ marginTop: 16, background: "#fff7ed", border: "1px solid #fb923c", color: "#7c2d12", padding: 12, borderRadius: 10 }}>
          {auxWarning}
        </div>
      )}

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14, background: "#fff", borderRadius: 14, padding: 16, marginTop: 18, boxShadow: "0 4px 14px rgba(0,0,0,0.06)" }}>
        <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 700, color: "#555" }}>
          Segmento
          <select value={selectedSegment} onChange={(event) => { setSelectedSegment(event.target.value); setSelectedAdvertiser(""); }} style={selectStyle}>
            <option value="">Todos os segmentos</option>
            {segments.map((segment: any) => (
              <option key={segment.id} value={segment.id}>{segment.name}</option>
            ))}
          </select>
        </label>

        <label style={{ display: "grid", gap: 6, fontSize: 13, fontWeight: 700, color: "#555" }}>
          Anunciante cadastrado
          <select value={selectedAdvertiser} onChange={(event) => setSelectedAdvertiser(event.target.value)} style={selectStyle}>
            <option value="">Todos os anunciantes</option>
            {filteredAdvertisers.map((advertiser: any) => (
              <option key={advertiser.id} value={advertiser.id}>{advertiser.name}{advertiser.segment_name ? ` · ${advertiser.segment_name}` : ""}</option>
            ))}
          </select>
        </label>

        <div style={{ display: "flex", gap: 10, alignItems: "end" }}>
          <a href={`/evidencias${selectedSegment || selectedAdvertiser ? "" : ""}`} style={{ background: "#b00020", color: "#fff", borderRadius: 10, padding: "11px 14px", textDecoration: "none", fontWeight: "bold" }}>
            Abrir evidências
          </a>
          <a href="/admin/cadastros" style={{ background: "#334155", color: "#fff", borderRadius: 10, padding: "11px 14px", textDecoration: "none", fontWeight: "bold" }}>
            Cadastros
          </a>
        </div>
      </section>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 20,
          marginTop: 20,
        }}
      >
        <Card title="Investimento" value={formatBRL(data.total_investment)} />
        <Card title="Itens detectados" value={data.total_detected_items ?? evidenceStats.Total ?? data.total_banners} />
        <Card title="Itens para mercado" value={data.total_market_items ?? data.total_banners} />
        <Card title="Publicidade auditável" value={data.total_checking_ready ?? data.evidence_summary?.auditavel ?? 0} />
        <Card title="Revisão/parcial" value={data.total_checking_review ?? ((data.evidence_summary?.parcial || 0) + (data.evidence_summary?.revisao || 0))} />
        <Card title="Candidatos a notícia" value={data.total_news_candidates ?? data.evidence_summary?.news_candidates ?? 0} />
        <Card title="Anunciantes identificados" value={identifiedShare?.length || 0} />
        <Card title="Pendentes ID" value={idQuality.unknown_items || 0} />
        <Card title="Portais" value={data.portal_ranking?.length || 0} />
      </section>

      {idQuality.unknown_items > 0 && (
        <section style={{ marginTop: 18, padding: 16, background: "#fff7ed", border: "1px solid #fb923c", borderLeft: "5px solid #f97316", borderRadius: 12, color: "#7c2d12" }}>
          <strong>Qualidade de identificação:</strong> {idQuality.unknown_items} item(ns) permanecem como pendentes de identificação ({formatPct(idQuality.unknown_share_items || 0)} dos itens de mercado). Esse bloco não é tratado como anunciante líder; ele entra como fila de auditoria comercial.
        </section>
      )}

      <section style={{ display: "flex", gap: 20, marginTop: 30 }}>
        <Highlight
          title="Líder identificado"
          value={`${topAdv.advertiser || "Sem anunciante identificado"} (${formatPct(
            topAdv.share_percent
          )})`}
        />

        <Highlight
          title="Portal líder"
          value={topPortal.portal || "Sem dados"}
        />
      </section>

      <section style={{ display: "flex", gap: 30, marginTop: 30 }}>
        <Box title="Top Anunciantes Identificados">
          {(identifiedShare || []).slice(0, 5).map((item: any, i: number) => (
            <Bar key={i} label={item.advertiser} value={item.share_percent} />
          ))}
        </Box>

        <Box title="Top Portais">
          {(data.portal_ranking || []).slice(0, 5).map((item: any, i: number) => (
            <Bar key={i} label={item.portal} value={item.share_percent} />
          ))}
        </Box>
      </section>

      <section style={{ display: "flex", gap: 30, marginTop: 30 }}>
        <Box title="Insights">
          {(data.market_analysis?.insights || []).map((item: string, i: number) => (
            <p key={i}>• {item}</p>
          ))}
        </Box>

        <Box title="Oportunidades">
          {(data.market_analysis?.opportunities || []).map(
            (item: string, i: number) => <p key={i}>• {item}</p>
          )}
        </Box>
      </section>

      {data.comparative_alerts?.length > 0 && (
        <section
          style={{
            marginTop: 30,
            padding: 20,
            background: "#fff3cd",
            borderLeft: "5px solid #c52625",
            borderRadius: 6,
          }}
        >
          <h3>Alertas Inteligentes</h3>

          {data.comparative_alerts.map((item: string, i: number) => (
            <p key={i}>• {item}</p>
          ))}
        </section>
      )}

      {data.market_analysis?.alerts?.length > 0 && (
        <section
          style={{
            marginTop: 30,
            padding: 20,
            background: "#ffe5e5",
            borderLeft: "5px solid red",
          }}
        >
          <h3>⚠ Alertas</h3>

          {data.market_analysis.alerts.map((item: string, i: number) => (
            <p key={i}>• {item}</p>
          ))}
        </section>
      )}

      {timelineAnalysis?.has_comparison && (
        <Box title="Tendências Competitivas">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 20,
              marginBottom: 24,
            }}
          >
            <TrendCard
              title="Variação de investimento"
              value={formatSignedBRL(investmentDelta)}
            />

            <TrendCard
              title="Variação do share líder"
              value={formatSignedPp(shareDelta)}
            />

            <TrendCard title="Líder atual" value={currentLeader} />
          </div>

          <div style={{ display: "flex", gap: 30 }}>
            <div style={{ flex: 1 }}>
              <h4>Leitura temporal</h4>

              {trendInsights.slice(0, 4).map((item: string, i: number) => (
                <p key={i}>• {item}</p>
              ))}
            </div>

            <div style={{ flex: 1 }}>
              <h4>Implicação estratégica</h4>

              {strategicNote.map((item: string, i: number) => (
                <p key={i}>• {item}</p>
              ))}
            </div>
          </div>
        </Box>
      )}

      <Box title="Histórico de Evidências Monitoradas">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, alignItems: "flex-start" }}>
          <p style={{ color: "#666", marginTop: 0, maxWidth: 820 }}>
            Esta seção separa checking publicitário, inteligência de mercado e
            candidatos a notícia. Nenhum item detectado precisa ser descartado:
            cada registro recebe uma finalidade e um nível de evidência.
          </p>
          <a href="/evidencias" style={{ background: "#b00020", color: "#fff", borderRadius: 10, padding: "10px 14px", textDecoration: "none", fontWeight: "bold", whiteSpace: "nowrap" }}>
            Abrir tela filtrável
          </a>
        </div>

        {evidences.length > 0 && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
              gap: 12,
              marginBottom: 18,
            }}
          >
            <EvidenceStat label="Auditáveis" value={evidenceStats.Auditável} />
            <EvidenceStat label="Parciais" value={evidenceStats.Parcial} />
            <EvidenceStat label="Em revisão" value={evidenceStats.Revisão} />
            <EvidenceStat label="Notícias" value={evidenceStats["Notícia candidata"]} />
            <EvidenceStat label="Mercado" value={evidenceStats.Mercado} />
            <EvidenceStat label="Rejeitados p/ checking" value={evidenceStats.Rejeitado} />
          </div>
        )}

        {evidences.length === 0 && (
          <p>Nenhuma evidência monitorada encontrada.</p>
        )}

        {evidences.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 14,
              }}
            >
              <thead>
                <tr>
                  <th style={thStyle}>Data/Hora</th>
                  <th style={thStyle}>Anunciante</th>
                  <th style={thStyle}>Portal</th>
                  <th style={thStyle}>Formato</th>
                  <th style={thStyle}>Finalidade</th>
                  <th style={thStyle}>Score pub.</th>
                  <th style={thStyle}>Score notícia</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Evidência preservada</th>
                  <th style={thStyle}>Imagem detectada</th>
                  <th style={thStyle}>Página original</th>
                </tr>
              </thead>

              <tbody>
                {evidences.slice(0, 20).map((item: any, index: number) => {
                  const preservedEvidenceUrl = getPreservedEvidenceUrl(item);
                  const detectedImageUrl = getDetectedImageUrl(item);
                  const evidenceStatus = getEvidenceStatus(item);

                  return (
                    <tr key={item.id || index}>
                      <td style={tdStyle}>{formatDate(item.created_at)}</td>

                      <td style={tdStyle}>
                        <strong>
                          {item.advertiser_name || "Não identificado"}
                        </strong>
                      </td>

                      <td style={tdStyle}>{item.source_name || "Web aberto"}</td>

                      <td style={tdStyle}>{formatBannerSize(item)}</td>

                      <td style={tdStyle}>{getContentTypeLabel(item)}</td>

                      <td style={tdStyle}>
                        {item.publicity_score !== null &&
                        item.publicity_score !== undefined
                          ? `${item.publicity_score}`
                          : item.classification_score !== null &&
                            item.classification_score !== undefined
                          ? `${item.classification_score}`
                          : "N/D"}
                      </td>

                      <td style={tdStyle}>
                        {item.news_score !== null && item.news_score !== undefined
                          ? `${item.news_score}`
                          : "N/D"}
                      </td>

                      <td style={tdStyle}>
                        <span style={evidenceStatusStyle(evidenceStatus)}>
                          {evidenceStatus}
                        </span>
                      </td>

                      <td style={tdStyle}>
                        {preservedEvidenceUrl ? (
                          <a
                            href={preservedEvidenceUrl}
                            target="_blank"
                            rel="noreferrer"
                            style={{ color: "#c52625", fontWeight: "bold" }}
                          >
                            Ver evidência
                          </a>
                        ) : (
                          <span style={{ color: "#999" }}>
                            Sem evidência preservada
                          </span>
                        )}
                      </td>

                      <td style={tdStyle}>
                        {detectedImageUrl ? (
                          <a
                            href={detectedImageUrl}
                            target="_blank"
                            rel="noreferrer"
                            style={{ color: "#555", fontWeight: "bold" }}
                          >
                            Ver imagem
                          </a>
                        ) : (
                          "N/D"
                        )}
                      </td>

                      <td style={tdStyle}>
                        {item.page_url ? (
                          <a
                            href={item.page_url}
                            target="_blank"
                            rel="noreferrer"
                            style={{ color: "#555", fontWeight: "bold" }}
                          >
                            Página original
                          </a>
                        ) : (
                          "N/D"
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Box>

      <Box title="Histórico Temporal">
        {timelineAnalysis?.insights?.length > 0 && (
          <div
            style={{
              marginBottom: 20,
              padding: 16,
              background: "#f8f9fb",
              borderLeft: "5px solid #c52625",
              borderRadius: 6,
            }}
          >
            <strong>Evolução Temporal Inteligente</strong>

            {timelineAnalysis.insights.map((item: string, i: number) => (
              <p key={i}>• {item}</p>
            ))}
          </div>
        )}

        {timeline.length === 0 && <p>Sem histórico suficiente ainda.</p>}

        {timeline.length > 0 && (
          <div
            style={{
              width: "100%",
              height: 320,
              background: "#fff",
              borderRadius: 16,
              padding: 16,
              marginBottom: 24,
              boxSizing: "border-box",
            }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />

                <Tooltip
                  labelFormatter={(_, payload: any) => {
                    const original = payload?.[0]?.payload?.created_at;
                    return formatDate(original);
                  }}
                  formatter={(value: any, name: string) => {
                    if (name === "investment") {
                      return [formatBRL(value), "Investimento"];
                    }

                    if (name === "leaderShare") {
                      return [formatPct(value), "Share do líder"];
                    }

                    return [value, name];
                  }}
                />

                <Legend verticalAlign="top" height={36} />

                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="investment"
                  name="Investimento"
                  stroke="#c52625"
                  strokeWidth={3}
                  dot={{ r: 4 }}
                />

                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="leaderShare"
                  name="Share do líder"
                  stroke="#333333"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {timeline.slice(-8).map((point: any, i: number) => (
          <div key={i} style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 12, color: "#666" }}>
              {formatDate(point.created_at)}
            </div>

            <div style={{ fontWeight: "bold" }}>
              {point.top_advertiser || "Sem líder"} —{" "}
              {formatPct(point.top_advertiser_share)}
            </div>

            <div style={{ background: "#eee", height: 8, marginTop: 4 }}>
              <div
                style={{
                  width: `${point.top_advertiser_share || 0}%`,
                  background: "#c52625",
                  height: "100%",
                }}
              />
            </div>

            <small>
              Investimento: {formatBRL(point.total_investment)} · Anúncios:{" "}
              {point.total_banners}
            </small>
          </div>
        ))}
      </Box>

      <div style={{ marginTop: 40, display: "flex", flexWrap: "wrap", gap: 12 }}>
        <button
          onClick={() => downloadWithAuth(`${API}/intel/report/pptx/${projectId}${reportQuery}`, `intel_${projectId}.pptx`).catch((err) => setError(err instanceof Error ? err.message : "Erro ao gerar PPTX."))}
          style={{
            padding: "14px 25px",
            background: "#c52625",
            color: "#fff",
            border: "none",
            fontSize: 16,
            cursor: "pointer",
            borderRadius: 4,
          }}
        >
          Gerar PPTX Completo
        </button>
        <button
          onClick={() => downloadWithAuth(`${API}/intel/report/pdf/${projectId}${reportQuery}`, `intel_${projectId}.pdf`).catch((err) => setError(err instanceof Error ? err.message : "Erro ao gerar PDF."))}
          style={{
            padding: "14px 25px",
            background: "#303846",
            color: "#fff",
            border: "none",
            fontSize: 16,
            cursor: "pointer",
            borderRadius: 4,
          }}
        >
          Gerar PDF Executivo
        </button>
        <button
          onClick={() => downloadWithAuth(`${API}/reports/project/pptx/${projectId}${completeReportQuery}`, `relatorio_completo_${projectId}.pptx`).catch((err) => setError(err instanceof Error ? err.message : "Erro ao gerar relatório completo PPTX."))}
          style={{
            padding: "14px 25px",
            background: "#b00020",
            color: "#fff",
            border: "none",
            fontSize: 16,
            cursor: "pointer",
            borderRadius: 4,
            fontWeight: "bold",
          }}
        >
          Gerar Relatório Completo PPTX
        </button>
        <button
          onClick={() => downloadWithAuth(`${API}/reports/project/pdf/${projectId}${completeReportQuery}`, `relatorio_completo_${projectId}.pdf`).catch((err) => setError(err instanceof Error ? err.message : "Erro ao gerar relatório completo PDF."))}
          style={{
            padding: "14px 25px",
            background: "#111827",
            color: "#fff",
            border: "none",
            fontSize: 16,
            cursor: "pointer",
            borderRadius: 4,
            fontWeight: "bold",
          }}
        >
          Gerar Relatório Completo PDF
        </button>
        <button
          onClick={() => downloadWithAuth(`${API}/reports/project/pdf/${projectId}?analysis_mode=checking_auditable`, `checking_auditavel_${projectId}.pdf`).catch((err) => setError(err instanceof Error ? err.message : "Erro ao gerar PDF de checking."))}
          style={{
            padding: "14px 25px",
            background: "#198754",
            color: "#fff",
            border: "none",
            fontSize: 16,
            cursor: "pointer",
            borderRadius: 4,
            fontWeight: "bold",
          }}
        >
          PDF Checking Auditável
        </button>
        <a
          href={`/intel/comparativo?project_id=${encodeURIComponent(projectId)}`}
          target="_self"
          rel="noreferrer"
        >
          <button
            style={{
              padding: "14px 25px",
              background: "#f1f3f8",
              color: "#303846",
              border: "1px solid #d8dde8",
              fontSize: 16,
              cursor: "pointer",
              borderRadius: 4,
              fontWeight: "bold",
            }}
          >
            Abrir Intel Comparativo
          </button>
        </a>
      </div>
    </main>
    </AppShell>
  );
}

function Card({ title, value }: any) {
  return (
    <div
      style={{
        background: "#fff",
        padding: 20,
        borderRadius: 6,
        boxShadow: "0 2px 5px rgba(0,0,0,0.05)",
      }}
    >
      <div style={{ fontSize: 13, color: "#777" }}>{title}</div>
      <div style={{ fontSize: 22, fontWeight: "bold" }}>{value}</div>
    </div>
  );
}

function TrendCard({ title, value }: any) {
  return (
    <div
      style={{
        background: "#f8f9fb",
        padding: 18,
        borderRadius: 10,
        borderLeft: "5px solid #c52625",
        boxShadow: "0 2px 5px rgba(0,0,0,0.05)",
      }}
    >
      <div style={{ fontSize: 13, color: "#777", marginBottom: 8 }}>
        {title}
      </div>

      <div style={{ fontSize: 20, fontWeight: "bold", color: "#222" }}>
        {value}
      </div>
    </div>
  );
}

function EvidenceStat({ label, value }: any) {
  return (
    <div
      style={{
        background: "#f8f9fb",
        padding: 14,
        borderRadius: 8,
        borderLeft: "4px solid #c52625",
      }}
    >
      <div style={{ fontSize: 12, color: "#777" }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: "bold" }}>{value}</div>
    </div>
  );
}

function Highlight({ title, value }: any) {
  return (
    <div
      style={{
        background: "#fff",
        padding: 20,
        flex: 1,
        borderLeft: "5px solid #c52625",
      }}
    >
      <div style={{ fontSize: 13, color: "#777" }}>{title}</div>
      <div style={{ fontSize: 18, fontWeight: "bold" }}>{value}</div>
    </div>
  );
}

function Box({ title, children }: any) {
  return (
    <div
      style={{
        background: "#fff",
        padding: 20,
        flex: 1,
        borderRadius: 6,
        marginTop: 30,
      }}
    >
      <h3>{title}</h3>
      {children}
    </div>
  );
}

function Bar({ label, value }: any) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12 }}>{label}</div>

      <div style={{ background: "#eee", height: 10 }}>
        <div
          style={{
            width: `${value || 0}%`,
            background: "#c52625",
            height: "100%",
          }}
        />
      </div>

      <small>{formatPct(value)}</small>
    </div>
  );
}

const thStyle = {
  textAlign: "left" as const,
  padding: "10px",
  borderBottom: "2px solid #ddd",
  color: "#555",
};

const tdStyle = {
  padding: "10px",
  borderBottom: "1px solid #eee",
  verticalAlign: "top" as const,
};

const selectStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: 10,
  border: "1px solid #d1d5db",
  background: "#fff",
  color: "#111827",
  WebkitTextFillColor: "#111827",
  colorScheme: "light",
  appearance: "auto",
};
