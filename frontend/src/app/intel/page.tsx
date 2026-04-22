"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

type AnyObj = Record<string, any>;

type ProjectOption = {
  project_id: string;
  label: string;
};

type AdvertiserItem = {
  id: string;
  name: string;
  ads: number;
  value: number;
  share: number;
  confidence: string;
  avgVisibilityScore: number;
  dominanceScore: number;
};

type PublisherItem = {
  id: string;
  name: string;
  ads: number;
  value: number;
  share: number;
  avgVisibilityScore: number;
};

type ConfidenceItem = {
  id: string;
  label: string;
  count: number;
  value: number;
};

type VisibilityItem = {
  id: string;
  advertiser: string;
  portal: string;
  value: number;
  visibilityScore: number;
};

type IntelSummary = {
  totalAds: number;
  totalInvestment: number;
  advertisersCount: number;
  publishersCount: number;
  advertisers: AdvertiserItem[];
  publishers: PublisherItem[];
  confidence: ConfidenceItem[];
  biggestAdvertiser: AdvertiserItem | null;
  biggestPublisher: PublisherItem | null;
  strategicAlerts: string[];
  topVisibilityItems: VisibilityItem[];
};

const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

function toNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;

  if (typeof value === "string") {
    const cleaned = value
      .replace(/R\$/g, "")
      .replace(/\s/g, "")
      .replace(/\./g, "")
      .replace(",", ".");
    const parsed = Number(cleaned);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  return 0;
}

function toText(value: unknown): string {
  if (typeof value === "string") return value.trim();
  if (typeof value === "number") return String(value);
  return "";
}

function firstNumber(obj: AnyObj, keys: string[], fallback = 0): number {
  for (const key of keys) {
    if (key in obj) {
      const val = toNumber(obj[key]);
      if (Number.isFinite(val)) return val;
    }
  }
  return fallback;
}

function firstText(obj: AnyObj, keys: string[], fallback = ""): string {
  for (const key of keys) {
    if (key in obj) {
      const val = toText(obj[key]);
      if (val) return val;
    }
  }
  return fallback;
}

function firstArray(obj: AnyObj, keys: string[]): AnyObj[] {
  for (const key of keys) {
    if (Array.isArray(obj[key])) return obj[key];
  }
  return [];
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function formatInt(value: number) {
  return new Intl.NumberFormat("pt-BR").format(value || 0);
}

function normalizeAdvertisers(data: AnyObj): AdvertiserItem[] {
  const raw = firstArray(data, [
    "share_of_voice",
    "top_advertisers",
    "advertisers",
    "anunciantes",
    "advertiser_ranking",
  ]);

  return raw.map((item: AnyObj, index: number) => {
    const name = firstText(
      item,
      ["name", "advertiser", "anunciante", "brand", "label"],
      "Não identificado"
    );

    const ads = firstNumber(item, [
      "total_banners",
      "banners",
      "ads",
      "anuncios",
      "count",
      "total_ads",
    ]);

    const value = firstNumber(item, [
      "estimated_value",
      "investment",
      "value",
      "valor",
      "estimated_investment",
      "revenue",
    ]);

    const share = firstNumber(item, [
      "share_percent",
      "share",
      "share_of_voice",
      "percent",
      "percentage",
      "percentual",
    ]);

    const confidence = firstText(
      item,
      ["confidence", "confianca", "quality", "qualidade"],
      "não informado"
    );

    return {
      id: `${index}-${name}`,
      name,
      ads,
      value,
      share,
      confidence: confidence.toLowerCase(),
      avgVisibilityScore: firstNumber(item, ["avg_visibility_score"], 0),
      dominanceScore: firstNumber(item, ["dominance_score"], 0),
    };
  });
}

function normalizePublishers(data: AnyObj): PublisherItem[] {
  const raw = firstArray(data, [
    "top_publishers",
    "publishers",
    "portais",
    "portal_share",
    "share_by_portal",
    "portal_distribution",
    "top_portals",
    "portal_ranking",
    "publisher_ranking",
    "sites",
    "domains",
  ]);

  return raw.map((item: AnyObj, index: number) => {
    const name = firstText(
      item,
      ["name", "portal", "publisher", "site", "domain", "label"],
      "Portal não informado"
    );

    const ads = firstNumber(item, [
      "total_banners",
      "banners",
      "ads",
      "anuncios",
      "count",
      "total_ads",
    ]);

    const value = firstNumber(item, [
      "estimated_value",
      "revenue",
      "value",
      "valor",
      "estimated_revenue",
      "investment",
    ]);

    const share = firstNumber(item, [
      "share_percent",
      "share",
      "percent",
      "percentage",
      "percentual",
    ]);

    return {
      id: `${index}-${name}`,
      name,
      ads,
      value,
      share,
      avgVisibilityScore: firstNumber(item, ["avg_visibility_score"], 0),
    };
  });
}

function groupConfidenceFromAdvertisers(
  advertisers: Array<{
    confidence: string;
    ads: number;
    value: number;
  }>
): ConfidenceItem[] {
  const map = new Map<string, { label: string; count: number; value: number }>();

  for (const item of advertisers) {
    const raw = (item.confidence || "não informado").toLowerCase();
    const label =
      raw === "high"
        ? "alta"
        : raw === "medium"
        ? "media"
        : raw === "low"
        ? "baixa"
        : raw;

    if (!map.has(label)) {
      map.set(label, { label, count: 0, value: 0 });
    }

    const current = map.get(label)!;
    current.count += item.ads || 0;
    current.value += item.value || 0;
  }

  return Array.from(map.values())
    .map((item, index) => ({
      id: `${index}-${item.label}`,
      label: item.label,
      count: item.count,
      value: item.value,
    }))
    .sort((a, b) => b.count - a.count);
}

function normalizeConfidence(data: AnyObj, advertisers: AdvertiserItem[]): ConfidenceItem[] {
  const raw = firstArray(data, [
    "confidence_breakdown",
    "confidence_distribution",
    "recognition_quality",
    "quality_breakdown",
    "identification_confidence",
    "confidence_summary",
    "confidence",
  ]);

  if (raw.length > 0) {
    return raw.map((item: AnyObj, index: number) => ({
      id: `${index}-${firstText(
        item,
        ["label", "confidence", "confianca", "quality", "name"],
        "não informado"
      )}`,
      label: firstText(
        item,
        ["label", "confidence", "confianca", "quality", "name"],
        "não informado"
      ),
      count: firstNumber(item, [
        "count",
        "total_banners",
        "banners",
        "ads",
        "anuncios",
      ]),
      value: firstNumber(item, ["estimated_value", "investment", "value", "valor"]),
    }));
  }

  return groupConfidenceFromAdvertisers(advertisers);
}

function normalizeSummary(data: AnyObj): IntelSummary {
  const advertisersBase = normalizeAdvertisers(data);
  const publishersBase = normalizePublishers(data);

  const totalAdsFromRoot = firstNumber(data, [
    "total_banners",
    "total_ads",
    "total_anuncios",
    "anuncios_monitorados",
  ]);

  const advertisersCountFromRoot = firstNumber(data, [
    "advertisers_count",
    "anunciantes_count",
    "anunciantes",
  ]);

  const publishersCountFromRoot = firstNumber(data, [
    "publishers_count",
    "portais_count",
    "portais",
  ]);

  const totalInvestmentFromRoot = firstNumber(data, [
    "estimated_total_value",
    "estimated_value",
    "investment_total",
    "total_investment",
    "investimento_estimado",
    "valor_total_estimado",
  ]);

  const advertisersValueSum = advertisersBase.reduce((sum, item) => sum + (item.value || 0), 0);
  const publishersValueSum = publishersBase.reduce((sum, item) => sum + (item.value || 0), 0);
  const advertisersAdsSum = advertisersBase.reduce((sum, item) => sum + (item.ads || 0), 0);
  const publishersAdsSum = publishersBase.reduce((sum, item) => sum + (item.ads || 0), 0);

  const totalAds = totalAdsFromRoot || advertisersAdsSum || publishersAdsSum || 0;
  const totalInvestment =
    totalInvestmentFromRoot || advertisersValueSum || publishersValueSum || 0;
  const advertisersCount = advertisersCountFromRoot || advertisersBase.length || 0;
  const publishersCount = publishersCountFromRoot || publishersBase.length || 0;

  const advertisers = advertisersBase.map((item) => {
    const computedShare =
      item.share ||
      (totalInvestment > 0
        ? (item.value / totalInvestment) * 100
        : totalAds > 0
        ? (item.ads / totalAds) * 100
        : 0);

    return {
      ...item,
      share: computedShare,
    };
  });

  const publishers = publishersBase.map((item) => {
    const computedShare =
      item.share ||
      (totalInvestment > 0
        ? (item.value / totalInvestment) * 100
        : totalAds > 0
        ? (item.ads / totalAds) * 100
        : 0);

    return {
      ...item,
      share: computedShare,
    };
  });

  const confidence = normalizeConfidence(data, advertisers);

  const biggestAdvertiser = advertisers.length
    ? [...advertisers].sort((a, b) => b.value - a.value || b.ads - a.ads)[0]
    : null;

  const biggestPublisher = publishers.length
    ? [...publishers].sort((a, b) => b.value - a.value || b.ads - a.ads)[0]
    : null;

  return {
    totalAds,
    totalInvestment,
    advertisersCount,
    publishersCount,
    advertisers,
    publishers,
    confidence,
    biggestAdvertiser,
    biggestPublisher,
    strategicAlerts: Array.isArray(data.strategic_alerts) ? data.strategic_alerts : [],
    topVisibilityItems: Array.isArray(data.top_visibility_items)
      ? data.top_visibility_items.map((item: AnyObj, index: number) => ({
          id: firstText(item, ["id"], `${index}`),
          advertiser: firstText(item, ["advertiser"], "Nao identificado"),
          portal: firstText(item, ["portal"], "Desconhecido"),
          value: firstNumber(item, ["investment", "value", "estimated_value"], 0),
          visibilityScore: firstNumber(item, ["visibility_score"], 0),
        }))
      : [],
  };
}

export default function IntelPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = searchParams.get("project_id") || DEFAULT_PROJECT_ID;

  const PROJECT_OPTIONS_URL = `${API_BASE}/projects/projects/intel-options/`;
  const PDF_REPORT_URL = `${API_BASE}/intel/report/pdf/${projectId}`;
  const INTEL_DATA_URL = `${API_BASE}/intel/summary/${projectId}`;
  const PPTX_REPORT_URL = `${API_BASE}/intel/report/pptx/${projectId}`;

  const [projectOptions, setProjectOptions] = useState<ProjectOption[]>([]);
  const [projectInput, setProjectInput] = useState(projectId);
  const [rawData, setRawData] = useState<AnyObj | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const effectiveProjectOptions = useMemo(() => {
    const active =
      projectId && !projectOptions.some((option) => option.project_id === projectId)
        ? [{ project_id: projectId, label: projectId }]
        : [];

    return [...active, ...projectOptions];
  }, [projectId, projectOptions]);

  useEffect(() => {
    let active = true;

    async function loadProjectOptions() {
      try {
        const response = await fetch(PROJECT_OPTIONS_URL, {
          method: "GET",
          cache: "no-store",
          headers: { accept: "application/json" },
        });

        if (!response.ok) return;

        const json = await response.json();

        if (active && Array.isArray(json)) {
          setProjectOptions(json);
        }
      } catch {
        // silencioso
      }
    }

    loadProjectOptions();

    return () => {
      active = false;
    };
  }, [PROJECT_OPTIONS_URL]);

  useEffect(() => {
    setProjectInput(projectId);
  }, [projectId]);

  function handleProjectSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();

    const nextProjectId = projectInput.trim();
    if (!nextProjectId) return;

    router.push(`/intel?project_id=${encodeURIComponent(nextProjectId)}`);
  }

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(INTEL_DATA_URL, {
          method: "GET",
          cache: "no-store",
          headers: { accept: "application/json" },
        });

        if (!response.ok) {
          throw new Error(`Falha ao carregar Intel (${response.status})`);
        }

        const json = await response.json();

        if (active) {
          setRawData(json);
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Erro ao carregar dados do Intel."
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      active = false;
    };
  }, [INTEL_DATA_URL]);

  const intel = useMemo(() => normalizeSummary(rawData || {}), [rawData]);

  const identificationHealth = useMemo(() => {
    const unidentified = intel.advertisers.find((item) =>
      item.name.toLowerCase().includes("nao identificado")
    );

    const lowConfidence = intel.confidence.find(
      (item) => item.label.toLowerCase() === "baixa"
    );

    const unidentifiedShare = unidentified?.share || 0;
    const lowConfidenceShare =
      intel.totalAds > 0 && lowConfidence
        ? (lowConfidence.count / intel.totalAds) * 100
        : 0;

    const identifiedShare = Math.max(0, 100 - unidentifiedShare);
    const confidentShare = Math.max(0, 100 - lowConfidenceShare);

    return {
      identifiedShare,
      unidentifiedShare,
      confidentShare,
      lowConfidenceShare,
    };
  }, [intel]);

  const identificationStatus =
    identificationHealth.identifiedShare >= 70
      ? "Saudável"
      : identificationHealth.identifiedShare >= 50
      ? "Atenção"
      : "Crítico";

  const recognitionStatus =
    identificationHealth.confidentShare >= 70
      ? "Saudável"
      : identificationHealth.confidentShare >= 50
      ? "Atenção"
      : "Crítico";

  const executiveSummary = useMemo(() => {
    const insights: string[] = [];

    const naoIdentificado = intel.advertisers.find((a) =>
      a.name.toLowerCase().includes("nao identificado")
    );
    const shareNaoIdentificado = naoIdentificado?.share || 0;

    const portalLider = intel.publishers?.[0];
    const confiancaBaixa =
      intel.totalAds > 0
        ? ((intel.confidence.find((c) => c.label.toLowerCase() === "baixa")?.count || 0) /
            intel.totalAds) *
          100
        : 0;

    // 1. Diagnóstico de risco
    if (shareNaoIdentificado > 40) {
      insights.push(
        `Alta dependência de inventário não identificado (${shareNaoIdentificado.toFixed(
          2
        )}%), comprometendo a precisão da leitura competitiva e reduzindo a rastreabilidade dos investimentos.`
      );
    }

    if (confiancaBaixa > 5) {
      insights.push(
        `Volume relevante de registros com baixa confiança (${confiancaBaixa.toFixed(
          2
        )}%), indicando necessidade de ajuste no reconhecimento ou enriquecimento de dados.`
      );
    }

    // 2. Concentração de mídia
    if (portalLider?.share > 18) {
      insights.push(
        `Concentração de veiculação no portal ${portalLider.name}, responsável por ${portalLider.share.toFixed(
          2
        )}% do inventário monitorado, sugerindo possível dependência de canal.`
      );
    }

    // 3. Oportunidades
    if (shareNaoIdentificado > 30) {
      insights.push(
        `Oportunidade clara de qualificação comercial: ${shareNaoIdentificado.toFixed(
          2
        )}% do inventário pode ser convertido em inteligência acionável com enriquecimento de identificação.`
      );
    }

    if (intel.advertisersCount < 20) {
      insights.push(
        `Baixa diversidade de anunciantes (${intel.advertisersCount}), indicando espaço para expansão de mercado e prospecção ativa.`
      );
    }

    // 4. Recomendação executiva
    insights.push(
      "Recomendação: priorizar estratégias de identificação de inventário, diversificação de portais e análise de concentração para aumentar eficiência e inteligência competitiva."
    );

    return insights;
  }, [intel]); 

  const marketOpportunities = useMemo(() => {
    const list: string[] = [];

    const unidentified = intel.advertisers.find((a) =>
      a.name.toLowerCase().includes("nao identificado")
    );

    if (unidentified && unidentified.share > 30) {
      list.push("Oportunidade de qualificação de inventário não identificado.");
    }

    const highVisibilityPortal = [...intel.publishers].sort(
      (a, b) => (b.avgVisibilityScore || 0) - (a.avgVisibilityScore || 0)
    )[0];

    if (highVisibilityPortal && highVisibilityPortal.share < 10) {
      list.push(
        `Portal com alta visibilidade (${highVisibilityPortal.name}) pouco explorado comercialmente.`
      );
    }

    if (intel.advertisers.length < 10) {
      list.push("Espaço para entrada de novos anunciantes no ecossistema monitorado.");
    }

    return list;
  }, [intel]);

  const riskAnalysis = useMemo(() => {
    let score = 0;

    if (intel.advertisers.length < 8) score += 2;
    if (intel.publishers.length < 5) score += 2;

    const unidentified = intel.advertisers.find((a) =>
      a.name.toLowerCase().includes("nao identificado")
    );

    if (unidentified && unidentified.share > 50) score += 3;

    if (score >= 5) return "Alto risco de concentração";
    if (score >= 3) return "Risco moderado";
    return "Ambiente saudável";
  }, [intel]);

  const executiveAlerts = useMemo(() => {
    const alerts: string[] = [];

    if (intel.biggestAdvertiser?.name?.toLowerCase().includes("nao identificado")) {
      alerts.push(
        `Alta participação de anúncios não identificados: ${intel.biggestAdvertiser.share.toFixed(
          2
        )}% do share total.`
      );
    }

    const lowConfidence = intel.confidence.find(
      (item) => item.label.toLowerCase() === "baixa"
    );

    if (lowConfidence && intel.totalAds > 0) {
      const lowShare = (lowConfidence.count / intel.totalAds) * 100;
      if (lowShare >= 40) {
        alerts.push(
          `Predominância de baixa confiança no reconhecimento: ${lowConfidence.count} banners (${lowShare.toFixed(
            2
          )}%).`
        );
      }
    }

    if (intel.biggestPublisher && intel.publishers.length > 0) {
      alerts.push(
        `Portal com maior concentração atual: ${intel.biggestPublisher.name}, com ${intel.biggestPublisher.share.toFixed(
          2
        )}% de share.`
      );
    }

    const backendAlerts = Array.isArray(intel.strategicAlerts)
      ? intel.strategicAlerts
      : [];

    return [...alerts, ...backendAlerts];
  }, [intel]);

  const executiveInsights = useMemo(() => {
    const insights: string[] = [];

    if (intel.biggestAdvertiser) {
      insights.push(
        `${intel.biggestAdvertiser.name} lidera a presença publicitária com ${intel.biggestAdvertiser.share.toFixed(
          2
        )}% de share e investimento estimado de ${formatCurrency(
          intel.biggestAdvertiser.value
        )}.`
      );
    }

    if (intel.biggestPublisher) {
      insights.push(
        `${intel.biggestPublisher.name} é o portal líder, com receita estimada de ${formatCurrency(
          intel.biggestPublisher.value
        )} e ${formatInt(intel.biggestPublisher.ads)} banners monitorados.`
      );
    }

    const topConfidence = intel.confidence.length
      ? [...intel.confidence].sort((a, b) => b.count - a.count)[0]
      : null;

    if (topConfidence) {
      insights.push(
        `A confiança predominante do reconhecimento é "${topConfidence.label}", com ${formatInt(
          topConfidence.count
        )} banners e ${formatCurrency(topConfidence.value)} em investimento associado.`
      );
    }

    if (intel.advertisersCount > 0 && intel.publishersCount > 0) {
      insights.push(
        `O painel consolida ${formatInt(intel.advertisersCount)} anunciantes distribuídos em ${formatInt(
          intel.publishersCount
        )} portais monitorados.`
      );
    }

    return insights;
  }, [intel]);

  const hasIntelData =
    intel.totalAds > 0 ||
    intel.advertisers.length > 0 ||
    intel.publishers.length > 0 ||
    intel.confidence.length > 0;

  const semDados =
    !loading &&
    !error &&
    intel.totalAds === 0 &&
    intel.advertisers.length === 0 &&
    intel.publishers.length === 0 &&
    intel.confidence.length === 0;

  return (
    <main className="intel-page">
      <div className="intel-container">
        <section className="hero">
          <div>
            <div className="hero-brand">
              <div className="hero-logo-frame">
                <img
                  src="/logo-tv-fiscal-clean.png"
                  alt="TV Fiscal"
                  className="hero-logo"
                />
              </div>

              <div className="eyebrow">TV Fiscal WebMonitor</div>
            </div>

            <h1>Inteligência de Mercado</h1>
            <p>
              Painel executivo de presença publicitária digital por anunciante,
              portal, qualidade da identificação e inteligência estratégica.
            </p>
          </div>

          <div className="hero-side">
            <form onSubmit={handleProjectSubmit} style={{ width: "100%" }}>
              <div
                style={{
                  display: "flex",
                  gap: "10px",
                  flexWrap: "wrap",
                  marginBottom: "12px",
                  width: "100%",
                }}
              >
                <select
                  value={projectInput || projectId}
                  onChange={(e) => setProjectInput(e.target.value)}
                  style={{
                    flex: "1 1 320px",
                    minWidth: "280px",
                    height: "48px",
                    padding: "0 14px",
                    borderRadius: "14px",
                    border: "1px solid rgba(255,255,255,0.35)",
                    background: "rgba(255,255,255,0.95)",
                    color: "#111827",
                    fontSize: "14px",
                    outline: "none",
                  }}
                >
                  {effectiveProjectOptions.length === 0 ? (
                    <option value="">Selecione um projeto</option>
                  ) : null}

                  {effectiveProjectOptions.map((option) => (
                    <option key={option.project_id} value={option.project_id}>
                      {option.label || option.project_id}
                    </option>
                  ))}
                </select>

                <button type="submit" className="report-btn">
                  Abrir projeto
                </button>
              </div>

              <div className="project-line">Projeto ativo: {projectId}</div>
            </form>

            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              <a
                href={PDF_REPORT_URL}
                target="_blank"
                rel="noreferrer"
                className="report-btn"
              >
                Gerar Relatório PDF
              </a>

              <a
                href={PPTX_REPORT_URL}
                target="_blank"
                rel="noreferrer"
                className="report-btn"
              >
                Exportar PowerPoint
              </a>
            </div>

            <div className="summary-box">
              <div className="summary-label">Resumo do cenário</div>
              <div className="summary-value">
                {formatInt(intel.totalAds)} anúncios monitorados
              </div>
            </div>
          </div>
        </section>

        {loading && (
          <div className="info-box">Carregando dados do painel Intel...</div>
        )}

        {semDados && (
          <div className="error-box">
            Nenhum dado encontrado para o projeto informado: <b>{projectId}</b>
          </div>
        )}

        {!loading && error && <div className="error-box">{error}</div>}

        {!loading && !error && !hasIntelData && !semDados && (
          <div className="info-box">
            Nenhum dado encontrado para o projeto selecionado.
          </div>
        )}

        {!loading && !error && hasIntelData && (
          <>
            <section className="card insights-card">
              <h2 className="accent">Leitura Executiva</h2>

              <div className="insights-list">
                {executiveSummary.map((msg, i) => (
                  <div key={i} className="alert-item">
                    {msg}
                  </div>
                ))}
              </div>
            </section>

            <section className="kpis">
              <div className="card kpi-card">
                <div className="kpi-label">Investimento Total</div>
                <div className="kpi-value kpi-red">
                  {formatCurrency(intel.totalInvestment)}
                </div>
              </div>

              <div className="card kpi-card">
                <div className="kpi-label">Total de Anúncios</div>
                <div className="kpi-value">{formatInt(intel.totalAds)}</div>
              </div>

              <div className="card kpi-card">
                <div className="kpi-label">Anunciantes</div>
                <div className="kpi-value">{formatInt(intel.advertisersCount)}</div>
              </div>

              <div className="card kpi-card">
                <div className="kpi-label">Portais</div>
                <div className="kpi-value">{formatInt(intel.publishersCount)}</div>
              </div>
            </section>

            <section className="highlights">
              <div className="card">
                <div className="section-label">Maior anunciante</div>
                <div className="highlight-title">
                  {intel.biggestAdvertiser?.name || "Não identificado"}
                </div>
                <div className="highlight-meta">
                  Share:{" "}
                  {intel.biggestAdvertiser
                    ? `${intel.biggestAdvertiser.share.toFixed(1)}%`
                    : "-"}{" "}
                  | Confiança: {intel.biggestAdvertiser?.confidence || "-"}
                </div>
              </div>

              <div className="card">
                <div className="section-label">Portal líder</div>
                <div className="highlight-title">
                  {intel.biggestPublisher?.name || "Não informado"}
                </div>
                <div className="highlight-meta">
                  Receita estimada:{" "}
                  {intel.biggestPublisher
                    ? formatCurrency(intel.biggestPublisher.value)
                    : formatCurrency(0)}
                </div>
              </div>
            </section>

            <section className="card">
              <h2>Oportunidades de Mercado</h2>

              {marketOpportunities.length === 0 ? (
                <div className="empty">Nenhuma oportunidade relevante identificada.</div>
              ) : (
                <div className="list">
                  {marketOpportunities.map((item, i) => (
                    <div key={i} className="list-item">
                      <div>
                        <div className="item-title">Oportunidade</div>
                        <div className="item-sub">{item}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="card" style={{ marginBottom: 20 }}>
              <h2>Análise de Risco</h2>
              <div className="highlight-title">{riskAnalysis}</div>
            </section>

            <section className="charts-row">
              <div className="card">
                <h2>Share por anunciante</h2>

                {intel.advertisers.length === 0 ? (
                  <div className="empty">Nenhum dado disponível.</div>
                ) : (
                  <div className="bar-list">
                    {intel.advertisers.slice(0, 5).map((item) => (
                      <div key={item.id} className="bar-row">
                        <div className="bar-header">
                          <span className="bar-label">{item.name}</span>
                          <span className="bar-number">{item.share.toFixed(2)}%</span>
                        </div>

                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{ width: `${Math.min(item.share, 100)}%` }}
                          />
                        </div>

                        <div className="bar-subline">
                          {formatInt(item.ads)} banners · {formatCurrency(item.value)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="card">
                <h2>Share por portal</h2>

                {intel.publishers.length === 0 ? (
                  <div className="empty">Nenhum dado disponível.</div>
                ) : (
                  <div className="bar-list">
                    {intel.publishers.slice(0, 5).map((item) => (
                      <div key={item.id} className="bar-row">
                        <div className="bar-header">
                          <span className="bar-label">{item.name}</span>
                          <span className="bar-number">{item.share.toFixed(2)}%</span>
                        </div>

                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{ width: `${Math.min(item.share, 100)}%` }}
                          />
                        </div>

                        <div className="bar-subline">
                          {formatInt(item.ads)} banners · {formatCurrency(item.value)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className="card insights-card">
              <h2>Insights automáticos</h2>

              {executiveInsights.length === 0 ? (
                <div className="empty">Nenhum insight disponível.</div>
              ) : (
                <div className="insights-list">
                  {executiveInsights.map((item, index) => (
                    <div key={index} className="insight-item">
                      {item}
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="card insights-card">
              <h2 className="accent">Alertas estratégicos</h2>

              {executiveAlerts.length === 0 ? (
                <div className="empty">Nenhum alerta crítico no momento.</div>
              ) : (
                <div className="insights-list">
                  {executiveAlerts.map((item, index) => (
                    <div key={index} className="alert-item">
                      {item}
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="grid-2">
              <div className="card">
                <h2>Dominância de mercado</h2>

                {intel.advertisers.length === 0 ? (
                  <div className="empty">Nenhum dado disponível.</div>
                ) : (
                  <div className="list">
                    {[...intel.advertisers]
                      .sort((a, b) => (b.dominanceScore || 0) - (a.dominanceScore || 0))
                      .slice(0, 5)
                      .map((item, index) => (
                        <div key={item.id} className="list-item">
                          <div>
                            <div className="item-title">
                              {index + 1}. {item.name}
                            </div>
                            <div className="item-sub">
                              Share: {item.share.toFixed(2)}% · Visibilidade média:{" "}
                              {(item.avgVisibilityScore || 0).toFixed(2)}
                            </div>
                          </div>

                          <div className="item-right">
                            <div className="item-share">
                              {(item.dominanceScore || 0).toFixed(2)}
                            </div>
                            <div className="item-value">Score de dominância</div>
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>

              <div className="card">
                <h2>Top peças por visibilidade</h2>

                {intel.topVisibilityItems.length === 0 ? (
                  <div className="empty">Nenhum dado disponível.</div>
                ) : (
                  <div className="list">
                    {intel.topVisibilityItems.slice(0, 5).map((item, index) => (
                      <div key={item.id} className="list-item">
                        <div>
                          <div className="item-title">
                            {index + 1}. {item.advertiser}
                          </div>
                          <div className="item-sub">{item.portal}</div>
                        </div>

                        <div className="item-right">
                          <div className="item-share">
                            {item.visibilityScore.toFixed(2)}
                          </div>
                          <div className="item-value">{formatCurrency(item.value)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className="health-grid">
              <div className="card health-card">
                <div className="health-topline">
                  <div className="health-label">Taxa de identificação</div>
                  <div
                    className={`health-badge ${
                      identificationStatus === "Saudável"
                        ? "health-ok"
                        : identificationStatus === "Atenção"
                        ? "health-warn"
                        : "health-critical"
                    }`}
                  >
                    {identificationStatus}
                  </div>
                </div>

                <div className="health-value">
                  {identificationHealth.identifiedShare.toFixed(2)}%
                </div>
                <div className="health-sub">
                  Não identificados: {identificationHealth.unidentifiedShare.toFixed(2)}%
                </div>
              </div>

              <div className="card health-card">
                <div className="health-topline">
                  <div className="health-label">Qualidade do reconhecimento</div>
                  <div
                    className={`health-badge ${
                      recognitionStatus === "Saudável"
                        ? "health-ok"
                        : recognitionStatus === "Atenção"
                        ? "health-warn"
                        : "health-critical"
                    }`}
                  >
                    {recognitionStatus}
                  </div>
                </div>

                <div className="health-value">
                  {identificationHealth.confidentShare.toFixed(2)}%
                </div>
                <div className="health-sub">
                  Baixa confiança: {identificationHealth.lowConfidenceShare.toFixed(2)}%
                </div>
              </div>
            </section>

            <section className="grid-3">
              <div className="card">
                <h2>Top anunciantes</h2>

                {intel.advertisers.length === 0 ? (
                  <div className="empty">Nenhum dado disponível.</div>
                ) : (
                  <div className="list">
                    {intel.advertisers.slice(0, 10).map((item, index) => (
                      <div key={item.id} className="list-item">
                        <div>
                          <div className="item-title">
                            {index + 1}. {item.name}
                          </div>
                          <div className="item-sub">Banners: {formatInt(item.ads)}</div>
                          <div className="item-sub">
                            Confiança: {item.confidence || "não informado"}
                          </div>
                        </div>

                        <div className="item-right">
                          <div className="item-share">{item.share.toFixed(2)}%</div>
                          <div className="item-value">{formatCurrency(item.value)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="card">
                <h2>Top portais</h2>

                {intel.publishers.length === 0 ? (
                  <div className="empty">Nenhum dado disponível.</div>
                ) : (
                  <div className="list">
                    {intel.publishers.slice(0, 10).map((item, index) => (
                      <div key={item.id} className="list-item">
                        <div>
                          <div className="item-title">
                            {index + 1}. {item.name}
                          </div>
                          <div className="item-sub">Banners: {formatInt(item.ads)}</div>
                          <div className="item-sub">
                            Visibilidade média: {(item.avgVisibilityScore || 0).toFixed(2)}
                          </div>
                        </div>

                        <div className="item-right">
                          <div className="item-share">{item.share.toFixed(2)}%</div>
                          <div className="item-value">{formatCurrency(item.value)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="card">
                <h2 className="accent">Confiança da Identificação</h2>

                {intel.confidence.length === 0 ? (
                  <div className="empty">Nenhum dado disponível.</div>
                ) : (
                  <div className="list">
                    {intel.confidence.map((item) => (
                      <div key={item.id} className="list-item">
                        <div>
                          <div className="item-title">{item.label}</div>
                          <div className="item-sub">
                            Banners: {formatInt(item.count)}
                          </div>
                        </div>

                        <div className="item-right">
                          <div className="item-value">{formatCurrency(item.value)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          </>
        )}
      </div>

      <style jsx>{`
        .intel-page {
          min-height: 100vh;
          background: #f6f7fb;
          color: #1f2937;
        }

        .intel-container {
          max-width: 1280px;
          margin: 0 auto;
          padding: 24px;
        }

        .hero {
          display: flex;
          justify-content: space-between;
          gap: 24px;
          align-items: flex-end;
          background: linear-gradient(135deg, #7a1118 0%, #b91c1c 45%, #d93636 100%);
          color: #fff;
          border-radius: 28px;
          padding: 32px;
          box-shadow: 0 10px 30px rgba(153, 27, 27, 0.18);
          margin-bottom: 24px;
        }

        .hero-brand {
          display: flex;
          align-items: center;
          gap: 16px;
          margin-bottom: 12px;
        }

        .hero-logo-frame {
          width: 86px;
          height: 86px;
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.1);
          padding: 6px;
          box-sizing: border-box;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .hero-logo {
          width: 100%;
          height: 100%;
          object-fit: contain;
          object-position: center;
          display: block;
        }

        .eyebrow {
          font-size: 12px;
          letter-spacing: 0.18em;
          text-transform: uppercase;
          font-weight: 700;
          opacity: 0.9;
          margin-bottom: 0;
        }

        h1 {
          font-size: 48px;
          line-height: 1.05;
          margin: 0;
          font-weight: 800;
        }

        .hero p {
          margin: 14px 0 0;
          font-size: 18px;
          max-width: 760px;
          color: rgba(255, 255, 255, 0.92);
        }

        .hero-side {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 14px;
          min-width: 300px;
          width: 100%;
          max-width: 680px;
        }

        .project-line {
          margin-bottom: 12px;
          font-size: 13px;
          font-weight: 600;
          color: rgba(255, 255, 255, 0.92);
        }

        .report-btn {
          border: 0;
          background: #ffffff;
          color: #991b1b;
          font-weight: 700;
          font-size: 15px;
          border-radius: 14px;
          padding: 14px 20px;
          cursor: pointer;
          box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          justify-content: center;
        }

        .summary-box {
          background: rgba(255, 255, 255, 0.14);
          border-radius: 18px;
          padding: 18px 20px;
          min-width: 320px;
          width: 100%;
          backdrop-filter: blur(6px);
        }

        .summary-label {
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.12em;
          color: rgba(255, 255, 255, 0.82);
        }

        .summary-value {
          margin-top: 8px;
          font-size: 20px;
          font-weight: 800;
        }

        .info-box,
        .error-box {
          border-radius: 18px;
          padding: 18px 20px;
          margin-bottom: 20px;
          background: #fff;
          border: 1px solid #e5e7eb;
        }

        .error-box {
          background: #fef2f2;
          border-color: #fecaca;
          color: #b91c1c;
        }

        .kpis {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 16px;
          margin-bottom: 20px;
        }

        .highlights {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
          margin-bottom: 20px;
        }

        .charts-row,
        .health-grid,
        .grid-2 {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
          margin-bottom: 20px;
        }

        .grid-3 {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 16px;
        }

        .card {
          background: #fff;
          border: 1px solid #e8e8ee;
          border-radius: 22px;
          padding: 22px;
          box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
        }

        .kpi-card {
          min-height: 120px;
        }

        .kpi-label,
        .section-label,
        .health-label {
          font-size: 14px;
          color: #6b7280;
        }

        .kpi-value {
          margin-top: 14px;
          font-size: 44px;
          line-height: 1;
          font-weight: 800;
          color: #0f172a;
        }

        .kpi-red {
          color: #c02626;
        }

        .highlight-title {
          margin-top: 10px;
          font-size: 22px;
          font-weight: 800;
          color: #111827;
        }

        .highlight-meta {
          margin-top: 8px;
          font-size: 14px;
          color: #6b7280;
        }

        h2 {
          margin: 0 0 16px;
          font-size: 26px;
          color: #111827;
        }

        .accent {
          color: #b91c1c;
        }

        .list,
        .bar-list,
        .insights-list {
          display: flex;
          flex-direction: column;
        }

        .list {
          gap: 12px;
        }

        .bar-list,
        .insights-list {
          gap: 14px;
        }

        .bar-row {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .bar-header {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          align-items: center;
        }

        .bar-label {
          font-size: 14px;
          font-weight: 700;
          color: #111827;
        }

        .bar-number {
          font-size: 13px;
          font-weight: 700;
          color: #6b7280;
        }

        .bar-track {
          width: 100%;
          height: 12px;
          border-radius: 999px;
          background: #eef0f4;
          overflow: hidden;
        }

        .bar-fill {
          height: 100%;
          border-radius: 999px;
          background: linear-gradient(90deg, #c52625 0%, #db3b38 100%);
        }

        .bar-subline,
        .health-sub,
        .item-sub {
          font-size: 13px;
          color: #6b7280;
        }

        .list-item {
          display: flex;
          justify-content: space-between;
          gap: 16px;
          align-items: flex-start;
          padding: 16px;
          background: #f9fafb;
          border: 1px solid #eef0f4;
          border-radius: 16px;
        }

        .item-title {
          font-size: 16px;
          font-weight: 700;
          color: #111827;
        }

        .item-right {
          text-align: right;
          min-width: 130px;
        }

        .item-share {
          font-size: 16px;
          font-weight: 800;
          color: #111827;
        }

        .item-value {
          font-size: 14px;
          color: #6b7280;
          margin-top: 4px;
          font-weight: 600;
        }

        .insights-card {
          margin-bottom: 20px;
        }

        .insight-item {
          padding: 14px 16px;
          border: 1px solid #eef0f4;
          border-radius: 14px;
          background: #f9fafb;
          font-size: 14px;
          line-height: 1.6;
          color: #374151;
        }

        .alert-item {
          padding: 14px 16px;
          border: 1px solid #fecaca;
          border-radius: 14px;
          background: #fef2f2;
          font-size: 14px;
          line-height: 1.6;
          color: #991b1b;
          font-weight: 600;
        }

        .health-card {
          border: 1px solid #e5e7eb;
        }

        .health-value {
          margin-top: 10px;
          font-size: 34px;
          line-height: 1;
          font-weight: 800;
          color: #111827;
        }

        .health-topline {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          align-items: center;
        }

        .health-badge {
          padding: 6px 10px;
          border-radius: 999px;
          font-size: 12px;
          font-weight: 700;
        }

        .health-ok {
          background: #ecfdf5;
          color: #047857;
          border: 1px solid #a7f3d0;
        }

        .health-warn {
          background: #fffbeb;
          color: #b45309;
          border: 1px solid #fde68a;
        }

        .health-critical {
          background: #fef2f2;
          color: #b91c1c;
          border: 1px solid #fecaca;
        }

        .empty {
          font-size: 14px;
          color: #6b7280;
        }

        @media (max-width: 1100px) {
          .kpis,
          .grid-3,
          .highlights,
          .charts-row,
          .health-grid,
          .grid-2 {
            grid-template-columns: 1fr 1fr;
          }

          .hero {
            flex-direction: column;
            align-items: flex-start;
          }

          .hero-side {
            align-items: flex-start;
            width: 100%;
            max-width: 100%;
          }
        }

        @media (max-width: 760px) {
          .intel-container {
            padding: 16px;
          }

          .kpis,
          .grid-3,
          .highlights,
          .charts-row,
          .health-grid,
          .grid-2 {
            grid-template-columns: 1fr;
          }

          h1 {
            font-size: 34px;
          }

          .hero p {
            font-size: 15px;
          }

          .summary-box {
            min-width: 0;
            width: 100%;
          }
        }

        @media print {
          .report-btn {
            display: none !important;
          }

          .intel-page {
            background: #ffffff !important;
          }

          .intel-container {
            max-width: 100% !important;
            padding: 0 !important;
          }

          .card,
          .hero {
            box-shadow: none !important;
          }
        }
      `}</style>
    </main>
  );
}