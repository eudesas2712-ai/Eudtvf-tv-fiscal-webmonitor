"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";
import { adminJson, API_BASE } from "../../../lib/apiClient";

const API = API_BASE;

const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

type AdvertiserRow = {
  advertiser: string;
  items: number;
  investment: number;
  share: number;
  auditables?: number;
};

type AlertsPayload = {
  summary?: {
    project_id: string;
    pending_identification?: number;
    pending_identification_rate?: number;
    pending_identification_investment?: number;
    low_confidence_rate?: number;
    auditables?: number;
    market_items?: number;
    generated_at?: string;
  };
  market?: {
    top_advertisers?: AdvertiserRow[];
    confidence?: Record<string, number>;
  };
};

function brl(value?: number) {
  return `R$ ${Number(value || 0).toLocaleString("pt-BR")}`;
}

export default function BrandQualificationPage() {
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);
  const [data, setData] = useState<AlertsPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load(customProjectId = projectId) {
    setLoading(true);
    setError("");

    try {
      const payload = await adminJson<AlertsPayload>(`/alerts/summary/${customProjectId}`, {
        bearer: false,
        admin: true,
        json: true,
      });

      setData(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar qualificação de marcas.");
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

  const advertisers = useMemo(() => data?.market?.top_advertisers || [], [data]);

  return (
    <AppShell
      title="Qualificação de marcas"
      subtitle="Triagem operacional de anunciantes, pendências de identificação, baixa confiança e evidências auditáveis."
    >
      <section style={heroStyle}>
        <div>
          <div style={eyebrowStyle}>TV Fiscal WebMonitor · Brand Intelligence</div>
          <h2 style={{ margin: "8px 0 10px", fontSize: 32 }}>
            Qualificação comercial e revisão de marcas
          </h2>
          <p style={{ margin: 0, maxWidth: 860, lineHeight: 1.65 }}>
            Esta área consolida pendências de identificação, marcas com baixa confiança e anunciantes que exigem revisão manual.
          </p>
        </div>

        <div style={{ display: "grid", gap: 10, minWidth: 360 }}>
          <input
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            style={inputStyle}
            placeholder="Project ID"
          />
          <button onClick={() => load()} style={primaryButtonStyle}>
            {loading ? "Atualizando..." : "Atualizar qualificação"}
          </button>
        </div>
      </section>

      {error ? <div style={errorStyle}>{error}</div> : null}

      <section style={kpiGridStyle}>
        <Kpi
          label="Pendentes ID"
          value={data?.summary?.pending_identification || 0}
          hint={`${data?.summary?.pending_identification_rate || 0}% do recorte`}
        />
        <Kpi
          label="Invest. pendente"
          value={brl(data?.summary?.pending_identification_investment)}
          hint="valor estimado sem marca validada"
        />
        <Kpi
          label="Baixa confiança"
          value={`${data?.summary?.low_confidence_rate || 0}%`}
          hint="exige revisão operacional"
        />
        <Kpi
          label="Auditáveis"
          value={data?.summary?.auditables || 0}
          hint="evidências com lastro"
        />
      </section>

      <section style={panelStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <div>
            <h3 style={{ marginTop: 0 }}>Anunciantes detectados</h3>
            <p style={mutedStyle}>
              Use esta lista para priorizar a revisão de marcas e reduzir registros como “Não identificado”.
            </p>
          </div>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-start" }}>
            <a href={`/evidencias?project_id=${encodeURIComponent(projectId)}`} style={linkButtonStyle}>
              Abrir evidências
            </a>
            <a href={`/alerts?project_id=${encodeURIComponent(projectId)}`} style={secondaryButtonStyle}>
              Abrir alertas
            </a>
            <a href={`/intel?project_id=${encodeURIComponent(projectId)}`} style={secondaryButtonStyle}>
              Abrir Intel
            </a>
          </div>
        </div>

        <div style={{ overflowX: "auto", marginTop: 18 }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Marca / anunciante</th>
                <th style={thStyle}>Itens</th>
                <th style={thStyle}>Investimento</th>
                <th style={thStyle}>Share</th>
                <th style={thStyle}>Auditáveis</th>
                <th style={thStyle}>Prioridade</th>
              </tr>
            </thead>
            <tbody>
              {advertisers.length ? advertisers.map((row) => {
                const pending = row.advertiser.toLowerCase().includes("nao identificado") ||
                  row.advertiser.toLowerCase().includes("não identificado");

                return (
                  <tr key={row.advertiser}>
                    <td style={tdStyle}>
                      <strong>{row.advertiser}</strong>
                      {pending ? <div style={warningTextStyle}>Revisar identificação</div> : null}
                    </td>
                    <td style={tdStyle}>{row.items}</td>
                    <td style={tdStyle}>{brl(row.investment)}</td>
                    <td style={tdStyle}>{row.share}%</td>
                    <td style={tdStyle}>{row.auditables || 0}</td>
                    <td style={tdStyle}>
                      <span style={pending ? dangerBadgeStyle : okBadgeStyle}>
                        {pending ? "Alta" : "Normal"}
                      </span>
                    </td>
                  </tr>
                );
              }) : (
                <tr>
                  <td style={tdStyle} colSpan={6}>Nenhum anunciante retornado no recorte atual.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>Resumo técnico</h3>
        <p style={mutedStyle}>
          Página criada como módulo administrativo de validação pós-restore. Ela utiliza o endpoint de alertas já validado para exibir pendências de identificação e leitura inicial de qualificação de marcas.
        </p>
        <p style={mutedStyle}>
          Próxima evolução recomendada: criar endpoints próprios para aprovar marca, corrigir anunciante identificado e registrar histórico de revisão manual.
        </p>
      </section>
    </AppShell>
  );
}

function Kpi({ label, value, hint }: { label: string; value: string | number; hint: string }) {
  return (
    <div style={kpiStyle}>
      <div style={{ fontSize: 12, color: "#667085", fontWeight: 900, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 900, color: "#101828", marginTop: 6 }}>{value}</div>
      <div style={{ fontSize: 12, color: "#98a2b3", marginTop: 4 }}>{hint}</div>
    </div>
  );
}

const heroStyle: React.CSSProperties = {
  background: "linear-gradient(135deg,#111827 0%,#7a0015 100%)",
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

const eyebrowStyle: React.CSSProperties = {
  color: "#fda4af",
  fontSize: 12,
  fontWeight: 900,
  letterSpacing: 1.5,
  textTransform: "uppercase",
};

const inputStyle: React.CSSProperties = {
  padding: "12px 14px",
  borderRadius: 10,
  border: "1px solid rgba(255,255,255,.35)",
  background: "#fff",
  color: "#101828",
  fontWeight: 700,
};

const primaryButtonStyle: React.CSSProperties = {
  background: "#b00020",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  padding: "12px 16px",
  fontWeight: 900,
  cursor: "pointer",
};

const secondaryButtonStyle: React.CSSProperties = {
  background: "#1f2937",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  padding: "11px 14px",
  fontWeight: 900,
  cursor: "pointer",
  textDecoration: "none",
};

const linkButtonStyle: React.CSSProperties = {
  ...secondaryButtonStyle,
  background: "#b00020",
};

const kpiGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(4,minmax(160px,1fr))",
  gap: 14,
  marginBottom: 22,
};

const kpiStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 18,
  padding: 18,
  border: "1px solid #eaecf0",
  boxShadow: "0 10px 25px rgba(16,24,40,.06)",
};

const panelStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 20,
  padding: 22,
  border: "1px solid #eaecf0",
  boxShadow: "0 10px 30px rgba(16,24,40,.06)",
  marginBottom: 22,
};

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 13,
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "10px 8px",
  background: "#101828",
  color: "#fff",
  fontSize: 12,
};

const tdStyle: React.CSSProperties = {
  padding: "10px 8px",
  borderBottom: "1px solid #eaecf0",
  verticalAlign: "top",
};

const mutedStyle: React.CSSProperties = {
  color: "#667085",
  lineHeight: 1.55,
};

const errorStyle: React.CSSProperties = {
  background: "#fee2e2",
  color: "#991b1b",
  padding: 14,
  borderRadius: 12,
  marginBottom: 16,
  fontWeight: 800,
};

const dangerBadgeStyle: React.CSSProperties = {
  background: "#fee2e2",
  color: "#991b1b",
  borderRadius: 999,
  padding: "5px 9px",
  fontSize: 12,
  fontWeight: 900,
};

const okBadgeStyle: React.CSSProperties = {
  background: "#dcfce7",
  color: "#166534",
  borderRadius: 999,
  padding: "5px 9px",
  fontSize: 12,
  fontWeight: 900,
};

const warningTextStyle: React.CSSProperties = {
  color: "#b42318",
  fontSize: 12,
  fontWeight: 800,
  marginTop: 4,
};
