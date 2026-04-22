import { apiGet } from "../../lib/api";
import { MonitoredItem } from "../../lib/types";
import AppShell from "../../components/AppShell";

const PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

function formatDate(dateString?: string | null) {
  if (!dateString) return "Sem data";
  return new Date(dateString).toLocaleString("pt-BR");
}

export default async function ItemsPage() {
  let items: MonitoredItem[] = [];

  try {
    items = await apiGet<MonitoredItem[]>(`/items/${PROJECT_ID}`);
  } catch (error) {
    return (
      <AppShell
        title="Dashboard de matérias"
        subtitle="Monitoramento editorial digital com filtros e relatórios"
      >
        <p>Erro ao carregar as matérias monitoradas.</p>
      </AppShell>
    );
  }

  return (
    <AppShell
      title="Dashboard de matérias"
      subtitle="Monitoramento editorial digital com filtros e relatórios"
    >
      <div style={{ marginBottom: 20 }}>
        <strong>Total de matérias monitoradas:</strong> {items.length}
      </div>

      <div style={{ display: "grid", gap: 16 }}>
        {items.map((item, index) => (
          <div key={index} style={cardStyle}>
            <h3 style={titleStyle}>{item.title}</h3>

            <div style={infoRow}>
              <strong>Origem:</strong> {item.source_name}
            </div>

            <div style={infoRow}>
              <strong>Data:</strong> {formatDate(item.created_at)}
            </div>

            <div style={infoRow}>
              <strong>Termos detectados:</strong>{" "}
              {item.matched_terms?.terms?.join(", ") || "Nenhum"}
            </div>

            <div style={{ marginTop: 10 }}>
              <a href={item.url} target="_blank" style={linkStyle}>
                Abrir matéria original
              </a>
            </div>

            {item.evidence_html_url && (
              <div style={{ marginTop: 8 }}>
                <a href={item.evidence_html_url} target="_blank" style={linkStyle}>
                  Abrir evidência HTML
                </a>
              </div>
            )}
          </div>
        ))}
      </div>
    </AppShell>
  );
}

const cardStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: 12,
  padding: 20,
  boxShadow: "0 2px 10px rgba(0,0,0,0.08)",
  borderLeft: "5px solid #b00020",
};

const titleStyle: React.CSSProperties = {
  marginTop: 0,
  color: "#b00020",
};

const infoRow: React.CSSProperties = {
  fontSize: 14,
  marginTop: 6,
};

const linkStyle: React.CSSProperties = {
  color: "#0056b3",
  textDecoration: "none",
  fontWeight: "bold",
  fontSize: 14,
};