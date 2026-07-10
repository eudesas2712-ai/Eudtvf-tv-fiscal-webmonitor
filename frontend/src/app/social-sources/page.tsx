"use client";

import React, { useEffect, useState } from "react";
import AppShell from "../../components/AppShell";
import { adminFetch, API_BASE } from "../../lib/apiClient";

const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

const SOCIAL_PLATFORMS = [
  { value: "youtube", label: "YouTube" },
  { value: "instagram", label: "Instagram" },
  { value: "facebook", label: "Facebook" },
  { value: "x", label: "X / Twitter" },
  { value: "tiktok", label: "TikTok" },
  { value: "linkedin", label: "LinkedIn" },
];

function platformLabel(value: string) {
  return SOCIAL_PLATFORMS.find((platform) => platform.value === value)?.label || value || "Social";
}


type SocialSource = {
  id: string;
  platform: string;
  name: string;
  source_type: string;
  query?: string;
  active: boolean;
  created_at?: string;
};

export default function SocialSourcesPage() {
  const [sources, setSources] = useState<SocialSource[]>([]);
  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const [platform, setPlatform] = useState("youtube");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function loadSources() {
    const res = await adminFetch(`${API_BASE}/social/sources/${DEFAULT_PROJECT_ID}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const payload = await res.json();
    setSources(payload.items || []);
  }

  useEffect(() => {
    loadSources().catch((error) => setMessage(`Erro ao carregar fontes sociais: ${error}`));
  }, []);

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
          platform,
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
      await loadSources();
    } catch (error) {
      setMessage(`Erro ao cadastrar fonte: ${error}`);
    } finally {
      setBusy(false);
    }
  }

  async function toggleSource(sourceId: string, active: boolean) {
    setBusy(true);
    setMessage("");

    try {
      const res = await adminFetch(`${API_BASE}/social/sources/${sourceId}/toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active }),
      });

      const payload = await res.json();
      setMessage(payload.message || "Fonte social atualizada.");
      await loadSources();
    } catch (error) {
      setMessage(`Erro ao atualizar fonte social: ${error}`);
    } finally {
      setBusy(false);
    }
  }

  async function collectSource(source: SocialSource) {
    setBusy(true);
    setMessage("");

    const sourcePlatform = source.platform || "youtube";
    const label = platformLabel(sourcePlatform);

    try {
      if (!["youtube", "x"].includes(sourcePlatform)) {
        setMessage(`Coleta manual para ${label} ainda não implementada. A fonte foi mantida cadastrada para ativação do conector na próxima etapa.`);
        return;
      }

      const params = new URLSearchParams();
      params.set("source_id", source.id);
      params.set("max_results", sourcePlatform === "x" ? "10" : "15");

      const endpoint = sourcePlatform === "x" ? "x" : "youtube";

      const res = await adminFetch(`${API_BASE}/social/${endpoint}/collect/${DEFAULT_PROJECT_ID}?${params.toString()}`, {
        method: "POST",
      });

      const payload = await res.json();
      setMessage(payload.message || `Coleta ${label} finalizada.`);
      await loadSources();
    } catch (error) {
      setMessage(`Erro na coleta ${label}: ${error}`);
    } finally {
      setBusy(false);
    }
  }

  const activeCount = sources.filter((source) => source.active).length;
  const inactiveCount = sources.length - activeCount;

  return (
    <AppShell title="Gestão de Fontes Sociais" subtitle="Cadastro, ativação e controle das fontes sociais do WebMonitor">
      <section style={heroStyle}>
        <div>
          <div style={kickerStyle}>TV FISCAL WEBMONITOR · SOCIAL SOURCES</div>
          <h2 style={titleStyle}>Fontes sociais monitoradas</h2>
          <p style={textStyle}>
            Controle separado das fontes sociais usadas pela coleta automática e manual. YouTube já opera via cron; X / Twitter está preparado para ativação com token; demais plataformas ficam cadastradas para os próximos conectores.
          </p>
        </div>
        <div style={statsGridStyle}>
          <Card label="Fontes totais" value={sources.length} />
          <Card label="Ativas" value={activeCount} />
          <Card label="Inativas" value={inactiveCount} />
        </div>
      </section>

      {message ? <div style={messageStyle}>{message}</div> : null}

      <section style={panelStyle}>
        <h3 style={panelTitleStyle}>Cadastrar nova fonte social</h3>
        <form onSubmit={createSource} style={{ display: "grid", gap: 12 }}>
            <select style={inputStyle} value={platform} onChange={(e) => setPlatform(e.target.value)}>
              {SOCIAL_PLATFORMS.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          <input style={inputStyle} placeholder="Nome da fonte. Ex.: São João Juazeiro" value={name} onChange={(e) => setName(e.target.value)} required />
          <input style={inputStyle} placeholder="Termo de busca. Ex.: Juazeiro Bahia" value={query} onChange={(e) => setQuery(e.target.value)} />
          <button style={buttonStyle} disabled={busy}>{busy ? "Processando..." : "Cadastrar fonte ativa"}</button>
        </form>
      </section>

      <section style={panelStyle}>
        <h3 style={panelTitleStyle}>Fontes cadastradas</h3>
        <div style={listStyle}>
          {sources.length === 0 ? (
            <p style={emptyStyle}>Nenhuma fonte social cadastrada.</p>
          ) : sources.map((source) => (
            <div key={source.id} style={rowStyle}>
              <div>
                <strong>{source.name}</strong>
                <div style={mutedStyle}>{platformLabel(source.platform)} · {source.source_type} · {source.query || "sem query"}</div>
                <div style={source.active ? activeBadgeStyle : inactiveBadgeStyle}>
                  {source.active ? "Ativa" : "Inativa"}
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button style={smallButtonStyle} disabled={busy || !source.active} onClick={() => collectSource(source)}>
                  Coletar
                </button>
                <button style={smallButtonStyle} disabled={busy} onClick={() => toggleSource(source.id, !source.active)}>
                  {source.active ? "Desativar" : "Ativar"}
                </button>
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

const heroStyle: React.CSSProperties = { background: "linear-gradient(135deg,#7c1027,#d62b44)", color: "#fff", borderRadius: 24, padding: 28, display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: 24, marginBottom: 22 };
const kickerStyle: React.CSSProperties = { fontSize: 12, fontWeight: 900, letterSpacing: 1.2, opacity: 0.9 };
const titleStyle: React.CSSProperties = { fontSize: 32, margin: "10px 0" };
const textStyle: React.CSSProperties = { fontSize: 15, lineHeight: 1.6, maxWidth: 760 };
const statsGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 };
const cardStyle: React.CSSProperties = { background: "rgba(255,255,255,0.14)", border: "1px solid rgba(255,255,255,0.25)", borderRadius: 16, padding: 16, display: "grid", gap: 6 };
const panelStyle: React.CSSProperties = { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 20, padding: 20, boxShadow: "0 10px 24px rgba(15,23,42,0.06)", marginBottom: 18 };
const panelTitleStyle: React.CSSProperties = { margin: 0, fontSize: 20, color: "#111827" };
const inputStyle: React.CSSProperties = { border: "1px solid #d1d5db", borderRadius: 12, padding: "12px 14px", fontSize: 14 };
const buttonStyle: React.CSSProperties = { border: 0, background: "#b00020", color: "#fff", borderRadius: 12, padding: "12px 16px", fontWeight: 800, cursor: "pointer" };
const smallButtonStyle: React.CSSProperties = { border: "1px solid #b00020", background: "#fff", color: "#b00020", borderRadius: 10, padding: "9px 12px", fontWeight: 800, cursor: "pointer" };
const listStyle: React.CSSProperties = { display: "grid", gap: 12, marginTop: 14 };
const rowStyle: React.CSSProperties = { display: "flex", justifyContent: "space-between", gap: 14, alignItems: "center", border: "1px solid #e5e7eb", borderRadius: 14, padding: 14 };
const mutedStyle: React.CSSProperties = { color: "#6b7280", fontSize: 13, marginTop: 4 };
const emptyStyle: React.CSSProperties = { color: "#6b7280", margin: 0 };
const messageStyle: React.CSSProperties = { background: "#ecfdf5", border: "1px solid #bbf7d0", color: "#166534", padding: 12, borderRadius: 14, marginBottom: 18 };
const activeBadgeStyle: React.CSSProperties = { marginTop: 8, display: "inline-block", padding: "4px 8px", borderRadius: 999, background: "#dcfce7", color: "#166534", fontSize: 12, fontWeight: 800 };
const inactiveBadgeStyle: React.CSSProperties = { marginTop: 8, display: "inline-block", padding: "4px 8px", borderRadius: 999, background: "#fee2e2", color: "#991b1b", fontSize: 12, fontWeight: 800 };
