"use client";

import { useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";
import { adminJson, API_BASE, ADMIN_TOKEN_KEY, DEFAULT_ADMIN_TOKEN } from "../../../lib/apiClient";

const API = API_BASE;
const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

type Segment = { id: string; name: string; description?: string; active?: boolean };
type Advertiser = { id: string; name: string; segment_id?: string | null; segment_name?: string | null; aliases?: string[]; role?: string };
type Portal = { id: string; name: string; base_url: string; category?: string; active?: boolean };

type ProjectConfig = {
  project: { id: string; name: string; description?: string | null };
  portals: Portal[];
  advertisers: Advertiser[];
};

const emptySegment = { name: "", description: "" };
const emptyAdvertiser = { name: "", legal_name: "", segment_id: "", advertiser_type: "anunciante", aliases: "" };
const emptyPortal = { name: "", base_url: "", category: "Portal de notícias", interval_minutes: "60" };

export default function AdminCadastrosPage() {
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [segments, setSegments] = useState<Segment[]>([]);
  const [advertisers, setAdvertisers] = useState<Advertiser[]>([]);
  const [portals, setPortals] = useState<Portal[]>([]);
  const [projectConfig, setProjectConfig] = useState<ProjectConfig | null>(null);
  const [segmentForm, setSegmentForm] = useState(emptySegment);
  const [advertiserForm, setAdvertiserForm] = useState(emptyAdvertiser);
  const [portalForm, setPortalForm] = useState(emptyPortal);
  const [selectedAdvertiser, setSelectedAdvertiser] = useState("");
  const [selectedPortal, setSelectedPortal] = useState("");
  const [selectedRole, setSelectedRole] = useState("monitorado");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const authenticated = Boolean(token);

  async function apiGet<T>(path: string): Promise<T> {
    return adminJson<T>(path, {
      bearer: false,
      admin: true,
      json: true,
    });
  }

  async function apiPost<T>(path: string, body: unknown): Promise<T> {
    return adminJson<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
      bearer: false,
      admin: true,
      json: true,
    });
  }

  async function loadAll() {
    try {
      setError("");
      const [segmentsJson, advertisersJson, portalsJson, projectJson] = await Promise.all([
        apiGet<Segment[]>("/registry/segments"),
        apiGet<Advertiser[]>("/registry/advertisers"),
        apiGet<Portal[]>("/registry/portals"),
        apiGet<ProjectConfig>(`/registry/projects/${DEFAULT_PROJECT_ID}/config`),
      ]);
      setSegments(segmentsJson);
      setAdvertisers(advertisersJson);
      setPortals(portalsJson);
      setProjectConfig(projectJson);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar cadastros.");
    }
  }

  useEffect(() => {
    const saved = localStorage.getItem(ADMIN_TOKEN_KEY) || "";
    setToken(saved);
    setTokenInput(saved);
    loadAll();
  }, []);

  function login() {
    const cleaned = tokenInput.trim();
    if (!cleaned) {
      setError("Informe o token administrativo.");
      return;
    }
    localStorage.setItem(ADMIN_TOKEN_KEY, cleaned);
    setToken(cleaned);
    setMessage("Token administrativo carregado.");
  }

  function logout() {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    setToken("");
    setTokenInput("");
  }

  async function bootstrapDefaults() {
    try {
      setError("");
      await apiPost("/registry/bootstrap-defaults", {});
      setMessage("Cadastros padrão criados/atualizados.");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar padrões.");
    }
  }

  async function bootstrapPortalsForProject() {
    try {
      setError("");
      await apiPost(`/registry/projects/${DEFAULT_PROJECT_ID}/bootstrap-portals`, {});
      setMessage("Portais padrão criados e vinculados ao projeto ativo.");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar/vincular portais padrão.");
    }
  }


  async function createSegment() {
    try {
      setError("");
      await apiPost("/registry/segments", segmentForm);
      setSegmentForm(emptySegment);
      setMessage("Segmento salvo.");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar segmento.");
    }
  }

  async function createAdvertiser() {
    try {
      setError("");
      await apiPost("/registry/advertisers", {
        ...advertiserForm,
        segment_id: advertiserForm.segment_id || null,
        aliases: advertiserForm.aliases.split(",").map((x) => x.trim()).filter(Boolean),
      });
      setAdvertiserForm(emptyAdvertiser);
      setMessage("Anunciante salvo.");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar anunciante.");
    }
  }

  async function createPortal() {
    try {
      setError("");
      await apiPost("/registry/portals", {
        ...portalForm,
        interval_minutes: Number(portalForm.interval_minutes || 60),
        monitor_publicity: true,
        monitor_editorial: true,
        active: true,
      });
      setPortalForm(emptyPortal);
      setMessage("Portal salvo.");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar portal.");
    }
  }

  async function attachAdvertiser() {
    if (!selectedAdvertiser) return;
    try {
      setError("");
      await apiPost(`/registry/projects/${DEFAULT_PROJECT_ID}/advertisers`, {
        advertiser_id: selectedAdvertiser,
        role: selectedRole,
        active: true,
      });
      setMessage("Anunciante vinculado ao projeto.");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao vincular anunciante.");
    }
  }

  async function attachPortal() {
    if (!selectedPortal) return;
    try {
      setError("");
      await apiPost(`/registry/projects/${DEFAULT_PROJECT_ID}/portals`, {
        portal_id: selectedPortal,
        active: true,
      });
      setMessage("Portal vinculado ao projeto.");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao vincular portal.");
    }
  }

  const advertisersBySegment = useMemo(() => {
    const grouped: Record<string, Advertiser[]> = {};
    for (const advertiser of advertisers) {
      const key = advertiser.segment_name || "Sem segmento";
      grouped[key] = grouped[key] || [];
      grouped[key].push(advertiser);
    }
    return grouped;
  }, [advertisers]);

  return (
    <AppShell
      title="Cadastros operacionais"
      subtitle="Projetos, portais, anunciantes/clientes, segmentos e vínculos para checking individual e inteligência competitiva."
    >
      <section style={heroStyle}>
        <div>
          <div style={eyebrowStyle}>Configuração do WebMonitor</div>
          <h2 style={{ margin: "6px 0 8px", fontSize: 30 }}>Base operacional de checking e Intel</h2>
          <p style={{ margin: 0, lineHeight: 1.6 }}>
            Cadastre segmentos como Saúde, Telecom ou Educação, vincule anunciantes concorrentes e selecione os portais monitorados por projeto.
          </p>
        </div>
        <div style={{ display: "grid", gap: 10, minWidth: 320 }}>
          <input value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} placeholder="Token administrativo" style={inputStyle} />
          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={login} style={primaryButtonStyle}>Usar token</button>
            {authenticated ? <button onClick={logout} style={secondaryButtonStyle}>Sair</button> : null}
          </div>
        </div>
      </section>

      {message ? <div style={successStyle}>{message}</div> : null}
      {error ? <div style={errorStyle}>{error}</div> : null}

      <section style={toolbarStyle}>
        <button disabled={!authenticated} onClick={bootstrapDefaults} style={primaryButtonStyle}>Criar padrões comerciais</button>
        <button disabled={!authenticated} onClick={bootstrapPortalsForProject} style={primaryButtonStyle}>Criar/vincular portais padrão</button>
        <button onClick={loadAll} style={secondaryButtonStyle}>Atualizar listas</button>
        <a href="/evidencias" style={linkButtonStyle}>Abrir evidências</a>
        <a href="/intel" style={linkButtonStyle}>Abrir Intel</a>
      </section>

      <section style={gridStyle}>
        <div style={panelStyle}>
          <h3>Segmentos</h3>
          <input value={segmentForm.name} onChange={(e) => setSegmentForm({ ...segmentForm, name: e.target.value })} placeholder="Ex.: Saúde" style={inputStyle} />
          <textarea value={segmentForm.description} onChange={(e) => setSegmentForm({ ...segmentForm, description: e.target.value })} placeholder="Descrição" style={textareaStyle} />
          <button disabled={!authenticated} onClick={createSegment} style={primaryButtonStyle}>Salvar segmento</button>
          <List items={segments.map((s) => `${s.name}${s.active === false ? " · inativo" : ""}`)} />
        </div>

        <div style={panelStyle}>
          <h3>Anunciantes/clientes</h3>
          <input value={advertiserForm.name} onChange={(e) => setAdvertiserForm({ ...advertiserForm, name: e.target.value })} placeholder="Ex.: Unimed" style={inputStyle} />
          <select value={advertiserForm.segment_id} onChange={(e) => setAdvertiserForm({ ...advertiserForm, segment_id: e.target.value })} style={inputStyle}>
            <option value="">Segmento</option>
            {segments.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <input value={advertiserForm.aliases} onChange={(e) => setAdvertiserForm({ ...advertiserForm, aliases: e.target.value })} placeholder="Aliases separados por vírgula" style={inputStyle} />
          <button disabled={!authenticated} onClick={createAdvertiser} style={primaryButtonStyle}>Salvar anunciante</button>
          <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
            {Object.entries(advertisersBySegment).map(([segment, rows]) => (
              <div key={segment} style={miniCardStyle}>
                <strong>{segment}</strong>
                <div style={mutedStyle}>{(rows as Advertiser[]).map((r) => r.name).join(", ")}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={panelStyle}>
          <h3>Portais/fontes</h3>
          <input value={portalForm.name} onChange={(e) => setPortalForm({ ...portalForm, name: e.target.value })} placeholder="Nome do portal" style={inputStyle} />
          <input value={portalForm.base_url} onChange={(e) => setPortalForm({ ...portalForm, base_url: e.target.value })} placeholder="https://www.portal.com.br" style={inputStyle} />
          <input value={portalForm.category} onChange={(e) => setPortalForm({ ...portalForm, category: e.target.value })} placeholder="Categoria" style={inputStyle} />
          <button disabled={!authenticated} onClick={createPortal} style={primaryButtonStyle}>Salvar portal</button>
          <List items={portals.map((p) => `${p.name} · ${p.base_url}`)} />
        </div>
      </section>

      <section style={panelStyle}>
        <h3>Projeto ativo · vínculos operacionais</h3>
        <p style={mutedStyle}>{projectConfig?.project.name || DEFAULT_PROJECT_ID}</p>
        <div style={linkGridStyle}>
          <div>
            <h4>Vincular anunciante ao projeto</h4>
            <select value={selectedAdvertiser} onChange={(e) => setSelectedAdvertiser(e.target.value)} style={inputStyle}>
              <option value="">Selecione</option>
              {advertisers.map((a) => <option key={a.id} value={a.id}>{a.name} {a.segment_name ? `· ${a.segment_name}` : ""}</option>)}
            </select>
            <select value={selectedRole} onChange={(e) => setSelectedRole(e.target.value)} style={inputStyle}>
              <option value="cliente">Cliente</option>
              <option value="concorrente">Concorrente</option>
              <option value="monitorado">Monitorado</option>
            </select>
            <button disabled={!authenticated} onClick={attachAdvertiser} style={primaryButtonStyle}>Vincular anunciante</button>
          </div>
          <div>
            <h4>Vincular portal ao projeto</h4>
            <select value={selectedPortal} onChange={(e) => setSelectedPortal(e.target.value)} style={inputStyle}>
              <option value="">Selecione</option>
              {portals.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <button disabled={!authenticated} onClick={attachPortal} style={primaryButtonStyle}>Vincular portal</button>
          </div>
        </div>

        <div style={configGridStyle}>
          <div style={miniCardStyle}>
            <strong>Anunciantes vinculados</strong>
            <List items={(projectConfig?.advertisers || []).map((a) => `${a.name} · ${a.segment_name || "sem segmento"} · ${a.role || "monitorado"}`)} />
          </div>
          <div style={miniCardStyle}>
            <strong>Portais vinculados</strong>
            <List items={(projectConfig?.portals || []).map((p) => `${p.name} · ${p.base_url}`)} />
          </div>
        </div>
      </section>
    </AppShell>
  );
}

function List({ items }: { items: string[] }) {
  if (!items.length) return <p style={mutedStyle}>Nenhum registro.</p>;
  return <ul style={{ margin: "12px 0 0", paddingLeft: 18 }}>{items.slice(0, 12).map((item) => <li key={item} style={{ marginBottom: 6 }}>{item}</li>)}</ul>;
}

const heroStyle: React.CSSProperties = { background: "linear-gradient(135deg,#7a1118,#c52625)", color: "#fff", borderRadius: 22, padding: 24, display: "flex", justifyContent: "space-between", gap: 24, alignItems: "center", marginBottom: 20 };
const eyebrowStyle: React.CSSProperties = { fontSize: 12, textTransform: "uppercase", letterSpacing: 1.4, fontWeight: 900, opacity: 0.9 };
const panelStyle: React.CSSProperties = { background: "#fff", border: "1px solid #e5e7eb", borderRadius: 18, padding: 20, boxShadow: "0 8px 22px rgba(15,23,42,0.06)", marginBottom: 20 };
const gridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(290px, 1fr))", gap: 18 };
const linkGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 18, marginTop: 16 };
const configGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 18, marginTop: 18 };
const toolbarStyle: React.CSSProperties = { display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 20 };
const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "11px 12px",
  borderRadius: 10,
  border: "1px solid #d1d5db",
  marginBottom: 10,
  boxSizing: "border-box",
  background: "#fff",
  color: "#111827",
  WebkitTextFillColor: "#111827",
  colorScheme: "light",
  appearance: "auto",
};
const textareaStyle: React.CSSProperties = { ...inputStyle, minHeight: 78 };
const primaryButtonStyle: React.CSSProperties = { background: "#b00020", color: "#fff", border: "none", borderRadius: 10, padding: "11px 14px", fontWeight: 800, cursor: "pointer" };
const secondaryButtonStyle: React.CSSProperties = { background: "#334155", color: "#fff", border: "none", borderRadius: 10, padding: "11px 14px", fontWeight: 800, cursor: "pointer" };
const linkButtonStyle: React.CSSProperties = { ...secondaryButtonStyle, textDecoration: "none", display: "inline-block" };
const miniCardStyle: React.CSSProperties = { background: "#f8fafc", border: "1px solid #e5e7eb", borderRadius: 14, padding: 12 };
const mutedStyle: React.CSSProperties = { color: "#6b7280", fontSize: 13, lineHeight: 1.5 };
const successStyle: React.CSSProperties = { background: "#dcfce7", color: "#166534", border: "1px solid #86efac", borderRadius: 12, padding: 12, marginBottom: 14 };
const errorStyle: React.CSSProperties = { background: "#fee2e2", color: "#991b1b", border: "1px solid #fecaca", borderRadius: 12, padding: 12, marginBottom: 14 };
