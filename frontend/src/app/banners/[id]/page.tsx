"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { adminFetch, API_BASE } from "../../../lib/apiClient";

type AnyObj = Record<string, any>;

function toText(value: unknown) {
  if (typeof value === "string") return value.trim();
  if (typeof value === "number") return String(value);
  return "";
}

function toNumber(value: unknown) {
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

function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function formatDateTime(value: string) {
  if (!value) return "-";

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(parsed);
}

function normalizeConfidence(value: string) {
  const raw = (value || "").trim().toLowerCase();

  if (["alta", "high"].includes(raw)) return "alta";
  if (["media", "média", "medium"].includes(raw)) return "media";
  if (["baixa", "low"].includes(raw)) return "baixa";

  return raw || "não informado";
}

function normalizeClassification(value: string) {
  const raw = (value || "").trim().toLowerCase();

  if (!raw) return "Não classificado";
  if (raw === "publicidade") return "Publicidade";
  if (raw === "editorial") return "Editorial";
  if (raw === "indefinido") return "Indefinido";

  return value.trim();
}

export default function BannerDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();

  const bannerId = Array.isArray(params?.id) ? params.id[0] : params?.id || "";
  const projectId = searchParams.get("project_id") || "";

  const DETAIL_URL = `${API_BASE}/banners/item/${bannerId}`;

  const [rawData, setRawData] = useState<AnyObj | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadDetail() {
      try {
        setLoading(true);
        setError(null);

        const response = await adminFetch(DETAIL_URL, {
          method: "GET",
          cache: "no-store",
          headers: {
            accept: "application/json",
          },
        });

        if (!response.ok) {
          throw new Error(`Falha ao carregar detalhe (${response.status})`);
        }

        const json = await response.json();

        if (active) {
          if (json?.error) {
            setError(json.error);
            setRawData(null);
          } else {
            setRawData(json);
          }
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Erro ao carregar detalhe da evidência."
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    if (bannerId) {
      loadDetail();
    } else {
      setLoading(false);
      setError("ID da evidência não informado.");
    }

    return () => {
      active = false;
    };
  }, [DETAIL_URL, bannerId]);

  const detail = useMemo(() => {
    const data = rawData || {};

    return {
      id: toText(data.id),
      projectId: toText(data.project_id),
      advertiser: toText(data.advertiser_name) || "Nao identificado",
      portal: toText(data.source_name) || "Desconhecido",
      pageUrl: toText(data.page_url),
      imageUrl: toText(data.image_url),
      evidenceHtmlUrl: toText(data.evidence_html_url),
      screenshotPageUrl: toText(data.screenshot_page_url),
      screenshotBannerUrl: toText(data.screenshot_banner_url),
      ocrText: toText(data.ocr_text),
      classification: normalizeClassification(toText(data.classification)),
      classificationScore: toNumber(data.classification_score),
      classificationReason: toText(data.classification_reason) || "-",
      confidence: normalizeConfidence(toText(data.detection_confidence)),
      confidenceEvidence: toText(data.detection_evidence) || "-",
      createdAt: toText(data.created_at),
      value: toNumber(data.estimated_value),
      width: toNumber(data.width),
      height: toNumber(data.height),
      normalizedWidth: toNumber(data.normalized_width),
      normalizedHeight: toNumber(data.normalized_height),
      posX: toNumber(data.pos_x),
      posY: toNumber(data.pos_y),
      altText: toText(data.alt_text),
    };
  }, [rawData]);

  const backToBanners = projectId
    ? `/banners?project_id=${encodeURIComponent(projectId)}`
    : "/banners";

  const backToIntel = projectId
    ? `/intel?project_id=${encodeURIComponent(projectId)}`
    : "/intel";

  return (
    <main className="detail-page">
      <div className="detail-container">
        <section className="hero">
          <div>
            <div className="eyebrow">TV Fiscal WebMonitor</div>
            <h1>Detalhe da evidência</h1>
            <p>
              Visualização completa da peça monitorada, com dados técnicos,
              confiança, classificação e material de prova.
            </p>
          </div>

          <div className="hero-actions">
            <Link href={backToBanners} className="hero-btn">
              Voltar para banners
            </Link>
            <Link href={backToIntel} className="hero-btn">
              Abrir Intel
            </Link>
          </div>
        </section>

        {loading && <div className="info-box">Carregando detalhe da evidência...</div>}
        {!loading && error && <div className="error-box">{error}</div>}

        {!loading && !error && rawData && (
          <>
            <section className="grid-2">
              <div className="card">
                <h2>Banner capturado</h2>

                {detail.screenshotBannerUrl ? (
                  <a
                    href={detail.screenshotBannerUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="image-link"
                  >
                    <img
                      src={detail.screenshotBannerUrl}
                      alt={detail.advertiser}
                      className="main-image"
                    />
                  </a>
                ) : (
                  <div className="image-placeholder">Sem imagem do banner</div>
                )}
              </div>

              <div className="card">
                <h2>Página capturada</h2>

                {detail.screenshotPageUrl ? (
                  <a
                    href={detail.screenshotPageUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="image-link"
                  >
                    <img
                      src={detail.screenshotPageUrl}
                      alt={detail.portal}
                      className="main-image"
                    />
                  </a>
                ) : (
                  <div className="image-placeholder">Sem screenshot da página</div>
                )}
              </div>
            </section>

            <section className="kpis">
              <div className="card kpi-card">
                <div className="kpi-label">Anunciante</div>
                <div className="kpi-value small">{detail.advertiser}</div>
              </div>

              <div className="card kpi-card">
                <div className="kpi-label">Portal</div>
                <div className="kpi-value small">{detail.portal}</div>
              </div>

              <div className="card kpi-card">
                <div className="kpi-label">Valor estimado</div>
                <div className="kpi-value red">{formatCurrency(detail.value)}</div>
              </div>

              <div className="card kpi-card">
                <div className="kpi-label">Data/hora</div>
                <div className="kpi-value small">{formatDateTime(detail.createdAt)}</div>
              </div>
            </section>

            <section className="grid-2">
              <div className="card">
                <h2>Inteligência</h2>

                <div className="detail-list">
                  <div className="detail-row">
                    <span className="detail-label">Classificação</span>
                    <span className="detail-value">{detail.classification}</span>
                  </div>

                  <div className="detail-row">
                    <span className="detail-label">Score de classificação</span>
                    <span className="detail-value">{detail.classificationScore}</span>
                  </div>

                  <div className="detail-row">
                    <span className="detail-label">Motivo da classificação</span>
                    <span className="detail-value break">{detail.classificationReason}</span>
                  </div>

                  <div className="detail-row">
                    <span className="detail-label">Confiança</span>
                    <span className={`badge ${
                      detail.confidence === "alta"
                        ? "badge-high"
                        : detail.confidence === "media"
                        ? "badge-medium"
                        : detail.confidence === "baixa"
                        ? "badge-low"
                        : "badge-neutral"
                    }`}>
                      {detail.confidence}
                    </span>
                  </div>

                  <div className="detail-row">
                    <span className="detail-label">Evidência da confiança</span>
                    <span className="detail-value break">{detail.confidenceEvidence}</span>
                  </div>
                </div>
              </div>

              <div className="card">
                <h2>Dados técnicos</h2>

                <div className="detail-list">
                  <div className="detail-row">
                    <span className="detail-label">Dimensões</span>
                    <span className="detail-value">
                      {detail.width} × {detail.height}
                    </span>
                  </div>

                  <div className="detail-row">
                    <span className="detail-label">Dimensões normalizadas</span>
                    <span className="detail-value">
                      {detail.normalizedWidth} × {detail.normalizedHeight}
                    </span>
                  </div>

                  <div className="detail-row">
                    <span className="detail-label">Posição X</span>
                    <span className="detail-value">{detail.posX}</span>
                  </div>

                  <div className="detail-row">
                    <span className="detail-label">Posição Y</span>
                    <span className="detail-value">{detail.posY}</span>
                  </div>

                  <div className="detail-row">
                    <span className="detail-label">Alt text</span>
                    <span className="detail-value break">{detail.altText || "-"}</span>
                  </div>

                  <div className="detail-row">
                    <span className="detail-label">Project ID</span>
                    <span className="detail-value break">{detail.projectId}</span>
                  </div>
                </div>
              </div>
            </section>

            <section className="grid-2">
              <div className="card">
                <h2>OCR / texto extraído</h2>
                <div className="text-box">{detail.ocrText || "Nenhum texto extraído."}</div>
              </div>

              <div className="card">
                <h2>Links úteis</h2>

                <div className="links-col">
                  {detail.evidenceHtmlUrl ? (
                    <a
                      href={detail.evidenceHtmlUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="action-link"
                    >
                      Abrir evidência HTML
                    </a>
                  ) : null}

                  {detail.pageUrl ? (
                    <a
                      href={detail.pageUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="action-link"
                    >
                      Abrir página original
                    </a>
                  ) : null}

                  {detail.imageUrl ? (
                    <a
                      href={detail.imageUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="action-link"
                    >
                      Abrir imagem original
                    </a>
                  ) : null}

                  {detail.screenshotBannerUrl ? (
                    <a
                      href={detail.screenshotBannerUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="action-link"
                    >
                      Abrir screenshot do banner
                    </a>
                  ) : null}

                  {detail.screenshotPageUrl ? (
                    <a
                      href={detail.screenshotPageUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="action-link"
                    >
                      Abrir screenshot da página
                    </a>
                  ) : null}

                  {!detail.evidenceHtmlUrl &&
                    !detail.pageUrl &&
                    !detail.imageUrl &&
                    !detail.screenshotBannerUrl &&
                    !detail.screenshotPageUrl && (
                      <div className="muted">Nenhum link disponível.</div>
                    )}
                </div>
              </div>
            </section>
          </>
        )}
      </div>

      <style jsx>{`
        .detail-page {
          min-height: 100vh;
          background: #f6f7fb;
          color: #1f2937;
        }

        .detail-container {
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

        .eyebrow {
          font-size: 12px;
          letter-spacing: 0.18em;
          text-transform: uppercase;
          font-weight: 700;
          opacity: 0.9;
        }

        h1 {
          font-size: 42px;
          line-height: 1.05;
          margin: 10px 0 0;
          font-weight: 800;
        }

        .hero p {
          margin: 14px 0 0;
          font-size: 18px;
          max-width: 760px;
          color: rgba(255, 255, 255, 0.92);
        }

        .hero-actions {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
        }

        .hero-btn {
          border: 0;
          background: #ffffff;
          color: #991b1b;
          font-weight: 700;
          font-size: 14px;
          border-radius: 14px;
          padding: 14px 18px;
          text-decoration: none;
          display: inline-flex;
          align-items: center;
          justify-content: center;
        }

        .info-box,
        .error-box,
        .card {
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 22px;
          box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
        }

        .info-box,
        .error-box {
          padding: 18px 20px;
          margin-bottom: 20px;
        }

        .error-box {
          background: #fef2f2;
          border-color: #fecaca;
          color: #b91c1c;
        }

        .card {
          padding: 22px;
        }

        .grid-2 {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
          margin-bottom: 20px;
        }

        .kpis {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 16px;
          margin-bottom: 20px;
        }

        .kpi-card {
          min-height: 118px;
        }

        .kpi-label {
          font-size: 14px;
          color: #6b7280;
        }

        .kpi-value {
          margin-top: 14px;
          font-size: 36px;
          line-height: 1.1;
          font-weight: 800;
          color: #0f172a;
        }

        .kpi-value.small {
          font-size: 24px;
        }

        .kpi-value.red {
          color: #c02626;
        }

        h2 {
          margin: 0 0 16px;
          font-size: 24px;
          color: #111827;
        }

        .image-link {
          display: block;
          border-radius: 16px;
          overflow: hidden;
          border: 1px solid #e5e7eb;
          background: #f9fafb;
        }

        .main-image {
          width: 100%;
          max-height: 480px;
          object-fit: contain;
          display: block;
          background: #f9fafb;
        }

        .image-placeholder {
          min-height: 260px;
          border: 1px dashed #d1d5db;
          border-radius: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #9ca3af;
          background: #f9fafb;
        }

        .detail-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .detail-row {
          display: flex;
          justify-content: space-between;
          gap: 16px;
          align-items: flex-start;
          padding: 14px 16px;
          border: 1px solid #eef0f4;
          border-radius: 14px;
          background: #f9fafb;
        }

        .detail-label {
          font-size: 13px;
          font-weight: 700;
          color: #6b7280;
          min-width: 180px;
        }

        .detail-value {
          font-size: 14px;
          color: #111827;
          text-align: right;
          font-weight: 600;
        }

        .detail-value.break {
          text-align: left;
          word-break: break-word;
          width: 100%;
        }

        .badge {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: 6px 10px;
          border-radius: 999px;
          font-size: 12px;
          font-weight: 700;
          white-space: nowrap;
        }

        .badge-high {
          background: #ecfdf5;
          color: #047857;
          border: 1px solid #a7f3d0;
        }

        .badge-medium {
          background: #fffbeb;
          color: #b45309;
          border: 1px solid #fde68a;
        }

        .badge-low {
          background: #fef2f2;
          color: #b91c1c;
          border: 1px solid #fecaca;
        }

        .badge-neutral {
          background: #f3f4f6;
          color: #374151;
          border: 1px solid #d1d5db;
        }

        .text-box {
          min-height: 180px;
          border: 1px solid #eef0f4;
          border-radius: 16px;
          background: #f9fafb;
          padding: 16px;
          white-space: pre-wrap;
          line-height: 1.6;
          color: #374151;
        }

        .links-col {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .action-link {
          display: inline-flex;
          width: fit-content;
          text-decoration: none;
          color: #991b1b;
          font-weight: 700;
          padding: 12px 14px;
          border: 1px solid #e5e7eb;
          border-radius: 14px;
          background: #fff;
        }

        .muted {
          color: #9ca3af;
        }

        @media (max-width: 1100px) {
          .hero {
            flex-direction: column;
            align-items: flex-start;
          }

          .grid-2,
          .kpis {
            grid-template-columns: 1fr 1fr;
          }
        }

        @media (max-width: 760px) {
          .detail-container {
            padding: 16px;
          }

          .grid-2,
          .kpis {
            grid-template-columns: 1fr;
          }

          h1 {
            font-size: 34px;
          }

          .hero p {
            font-size: 15px;
          }

          .detail-row {
            flex-direction: column;
          }

          .detail-value {
            text-align: left;
          }
        }
      `}</style>
    </main>
  );
}
