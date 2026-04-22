import { apiGet } from "../lib/api";
import { MonitoredItem, BannerItem } from "../lib/types";
import AppShell from "../components/AppShell";
import MediaCharts from "../components/MediaCharts";

const PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

function countBy(values: string[]) {
  const counts: Record<string, number> = {};
  for (const value of values) {
    counts[value] = (counts[value] || 0) + 1;
  }
  return Object.entries(counts).sort((a, b) => b[1] - a[1]);
}

function getTopTerms(items: MonitoredItem[]) {
  const terms: string[] = [];
  for (const item of items) {
    for (const term of item.matched_terms?.terms || []) {
      terms.push(term);
    }
  }
  return countBy(terms).slice(0, 6);
}

function getTopEditorialSources(items: MonitoredItem[]) {
  return countBy(items.map((item) => item.source_name || "Desconhecido")).slice(0, 6);
}

function getTopAdvertisers(banners: BannerItem[]) {
  return countBy(banners.map((banner) => banner.advertiser_name || "Nao identificado")).slice(0, 6);
}

function getTopBannerSources(banners: BannerItem[]) {
  return countBy(banners.map((banner) => banner.source_name || "Web aberto")).slice(0, 6);
}

function getTopFormats(banners: BannerItem[]) {
  return countBy(banners.map((banner) => `${banner.width || 0}x${banner.height || 0}`)).slice(0, 6);
}

function formatDate(dateString?: string | null) {
  if (!dateString) return "Sem data";
  return new Date(dateString).toLocaleString("pt-BR");
}

function toChartData(items: [string, number][]) {
  return items.map(([name, value]) => ({ name, value }));
}

function MetricCard({
  title,
  value,
  hint,
}: {
  title: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div style={metricCardStyle}>
      <div style={{ fontSize: 13, color: "#6a6f7a", marginBottom: 10, fontWeight: 600 }}>{title}</div>
      <div style={{ fontSize: 34, fontWeight: 800, color: "#b00020", lineHeight: 1 }}>{value}</div>
      {hint ? <div style={{ fontSize: 13, color: "#7c8088", marginTop: 10 }}>{hint}</div> : null}
    </div>
  );
}

function ActionButton({
  href,
  label,
  background,
}: {
  href: string;
  label: string;
  background: string;
}) {
  return (
    <a
      href={href}
      target={href.startsWith("http") ? "_blank" : undefined}
      style={{
        background,
        color: "#fff",
        padding: "12px 18px",
        borderRadius: 10,
        textDecoration: "none",
        fontWeight: 700,
        fontSize: 14,
        display: "inline-block",
        boxShadow: "0 6px 14px rgba(0,0,0,0.12)",
      }}
    >
      {label}
    </a>
  );
}

export default async function ExecutiveDashboardPage() {
  let items: MonitoredItem[] = [];
  let banners: BannerItem[] = [];

  try {
    [items, banners] = await Promise.all([
      apiGet<MonitoredItem[]>(`/items/${PROJECT_ID}`),
      apiGet<BannerItem[]>(`/banners/${PROJECT_ID}`),
    ]);
  } catch {
    return (
      <AppShell
        title="Painel executivo PRO"
        subtitle="Visao consolidada do monitoramento editorial e publicitario"
      >
        <div style={errorBoxStyle}>
          Erro ao carregar os dados do painel executivo.
        </div>
      </AppShell>
    );
  }

  const totalItems = items.length;
  const totalTerms = items.reduce(
    (acc, item) => acc + (item.matched_terms?.terms?.length || 0),
    0
  );
  const totalInvestment = banners.reduce(
    (acc, b) => acc + (b.estimated_value || 0),
    0
  );
  const totalBanners = banners.length;
  const identifiedAdvertisers = banners.filter((banner) => banner.advertiser_name).length;

  const topTerms = getTopTerms(items);
  const topEditorialSources = getTopEditorialSources(items);
  const topAdvertisers = getTopAdvertisers(banners);
  const topBannerSources = getTopBannerSources(banners);
  const topFormats = getTopFormats(banners);

  const editorialSourcesChart = toChartData(topEditorialSources);
  const bannerSourcesChart = toChartData(topBannerSources);
  const advertisersChart = toChartData(topAdvertisers);
  const termsChart = toChartData(topTerms);
  const formatsChart = toChartData(topFormats);

  const latestItems = items.slice(0, 5);
  const latestBanners = banners.slice(0, 5);

  return (
    <AppShell
      title="Painel executivo PRO"
      subtitle="TV Fiscal WebMonitor - visao central de monitoramento editorial, clipping e publicidade digital"
    >
      <section style={heroStyle}>
        <div>
          <div style={heroEyebrowStyle}>TV Fiscal Intelligence Center</div>
          <h2 style={heroTitleStyle}>Monitoramento digital unificado</h2>
          <p style={heroTextStyle}>
            Acompanhe menções editoriais, evidências, banners capturados, OCR de peças e relatórios executivos em uma única visão.
          </p>
        </div>

        <div style={heroBadgeBoxStyle}>
          <div style={heroBadgeStyle}>
            <div style={{ fontSize: 12, opacity: 0.85 }}>Projeto ativo</div>
            <div style={{ fontSize: 16, fontWeight: 800 }}>TV Fiscal WebMonitor</div>
          </div>
        </div>
      </section>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 28 }}>
        <ActionButton href="/items" label="Abrir módulo de matérias" background="#b00020" />
        <ActionButton href="/banners" label="Abrir módulo de banners" background="#1f4e79" />
        <ActionButton
          href={`http://localhost:8000/items/report-pdf/${PROJECT_ID}`}
          label="PDF de matérias"
          background="#198754"
        />
        <ActionButton
          href={`http://localhost:8000/banners/report-pdf/${PROJECT_ID}`}
          label="PDF de banners"
          background="#198754"
        />
        <ActionButton href="http://localhost:8000/docs" label="Swagger / API" background="#333" />
      </div>

      <div style={metricsGridStyle}>
        <MetricCard
          title="Matérias monitoradas"
          value={totalItems}
          hint="Ocorrências editoriais detectadas"
        />
        <MetricCard
          title="Termos detectados"
          value={totalTerms}
          hint="Soma de termos encontrados nas matérias"
        />
        <MetricCard
          title="Banners capturados"
          value={totalBanners}
          hint="Peças publicitárias identificadas"
        />
        <MetricCard
          title="Anunciantes identificados"
          value={identifiedAdvertisers}
          hint="Banners com anunciante reconhecido"
        />
        <MetricCard
          title="Investimento estimado"
          value={`R$ ${totalInvestment.toLocaleString("pt-BR")}`}
          hint="Estimativa baseada em formatos detectados"
        />
      </div>

      <MediaCharts
        editorialSources={editorialSourcesChart}
        bannerSources={bannerSourcesChart}
        advertisers={advertisersChart}
        terms={termsChart}
        formats={formatsChart}
      />

      <div style={twoColGridStyle}>
        <section style={panelStyle}>
          <div style={{ marginBottom: 16 }}>
            <h2 style={panelTitleStyle}>Últimas matérias monitoradas</h2>
            <p style={panelSubtitleStyle}>Atualizações editoriais mais recentes do projeto</p>
          </div>

          {latestItems.length === 0 ? (
            <p style={{ color: "#666" }}>Nenhuma matéria encontrada.</p>
          ) : (
            <div style={{ display: "grid", gap: 14 }}>
              {latestItems.map((item, index) => (
                <div key={index} style={listCardStyle}>
                  <strong style={{ display: "block", marginBottom: 8, color: "#b00020" }}>
                    {item.title}
                  </strong>

                  <div style={smallInfoStyle}>
                    <strong>Origem:</strong> {item.source_name}
                  </div>

                  <div style={smallInfoStyle}>
                    <strong>Coletado em:</strong> {formatDate(item.created_at)}
                  </div>

                  <div style={smallInfoStyle}>
                    <strong>Termos:</strong> {item.matched_terms?.terms?.join(", ") || "Nenhum"}
                  </div>

                  <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 10 }}>
                    <a href={item.url} target="_blank" style={linkStyle}>
                      Abrir matéria
                    </a>
                    {item.evidence_html_url ? (
                      <a href={item.evidence_html_url} target="_blank" style={linkStyle}>
                        Evidência HTML
                      </a>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section style={panelStyle}>
          <div style={{ marginBottom: 16 }}>
            <h2 style={panelTitleStyle}>Últimos banners capturados</h2>
            <p style={panelSubtitleStyle}>Peças publicitárias mais recentes monitoradas</p>
          </div>

          {latestBanners.length === 0 ? (
            <p style={{ color: "#666" }}>Nenhum banner encontrado.</p>
          ) : (
            <div style={{ display: "grid", gap: 14 }}>
              {latestBanners.map((banner, index) => (
                <div key={index} style={listCardStyle}>
                  <strong style={{ display: "block", marginBottom: 8, color: "#1f4e79" }}>
                    {banner.advertiser_name || "Nao identificado"}
                  </strong>

                  <div style={smallInfoStyle}>
                    <strong>Origem:</strong> {banner.source_name || "Web aberto"}
                  </div>

                  <div style={smallInfoStyle}>
                    <strong>Formato:</strong> {banner.width || 0} x {banner.height || 0}
                  </div>

                  <div style={smallInfoStyle}>
                    <strong>Coletado em:</strong> {formatDate(banner.created_at)}
                  </div>

                  <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 10 }}>
                    {banner.screenshot_banner_url ? (
                      <a href={banner.screenshot_banner_url} target="_blank" style={linkStyle}>
                        Abrir banner
                      </a>
                    ) : null}
                    {banner.page_url ? (
                      <a href={banner.page_url} target="_blank" style={linkStyle}>
                        Página de origem
                      </a>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}

const heroStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1.4fr 0.6fr",
  gap: 20,
  background: "linear-gradient(135deg, #7a0015 0%, #b00020 70%, #d1243f 100%)",
  color: "#fff",
  borderRadius: 18,
  padding: 24,
  marginBottom: 28,
  boxShadow: "0 10px 26px rgba(122,0,21,0.22)",
};

const heroEyebrowStyle: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 700,
  letterSpacing: 1,
  textTransform: "uppercase",
  opacity: 0.9,
  marginBottom: 10,
};

const heroTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 30,
  fontWeight: 800,
};

const heroTextStyle: React.CSSProperties = {
  marginTop: 12,
  marginBottom: 0,
  maxWidth: 720,
  lineHeight: 1.6,
  fontSize: 15,
  opacity: 0.95,
};

const heroBadgeBoxStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "flex-end",
};

const heroBadgeStyle: React.CSSProperties = {
  background: "rgba(255,255,255,0.14)",
  border: "1px solid rgba(255,255,255,0.25)",
  borderRadius: 14,
  padding: "16px 18px",
  minWidth: 220,
};

const metricsGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(4, 1fr)",
  gap: 18,
  marginBottom: 28,
};

const twoColGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: 24,
  marginTop: 28,
};

const metricCardStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 16,
  padding: 22,
  boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
  border: "1px solid #eef1f5",
};

const panelStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 16,
  padding: 22,
  boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
  border: "1px solid #eef1f5",
};

const panelTitleStyle: React.CSSProperties = {
  margin: 0,
  color: "#b00020",
  fontSize: 20,
};

const panelSubtitleStyle: React.CSSProperties = {
  margin: "8px 0 0 0",
  color: "#6b7280",
  fontSize: 14,
};

const listCardStyle: React.CSSProperties = {
  padding: 14,
  border: "1px solid #eceff3",
  borderRadius: 12,
  background: "#fafbfd",
};

const smallInfoStyle: React.CSSProperties = {
  fontSize: 14,
  marginBottom: 6,
  color: "#333",
};

const linkStyle: React.CSSProperties = {
  color: "#0056b3",
  textDecoration: "none",
  fontSize: 14,
  fontWeight: "bold",
};

const errorBoxStyle: React.CSSProperties = {
  background: "#fff4f4",
  border: "1px solid #f1c2c2",
  color: "#8a1f1f",
  padding: 18,
  borderRadius: 12,
};