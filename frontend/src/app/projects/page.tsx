"use client";

import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import AppShell from "../../components/AppShell";
import { adminJson, API_BASE, ADMIN_TOKEN_KEY, DEFAULT_ADMIN_TOKEN } from "../../lib/apiClient";

const API = API_BASE;
const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

type Segment = { id: string; name: string; active?: boolean };
type Portal = { id: string; name: string; base_url: string; category?: string | null; active?: boolean };
type Advertiser = { id: string; name: string; segment_id?: string | null; segment_name?: string | null; role?: string };
type Project = {
  id: string;
  name: string;
  client_name?: string | null;
  segment_id?: string | null;
  segment_name?: string | null;
  description?: string | null;
  active?: boolean;
  monitor_publicity?: boolean;
  monitor_editorial?: boolean;
  monitor_market?: boolean;
  monitor_checking?: boolean;
  portals_count?: number;
  advertisers_count?: number;
  created_at?: string | null;
};

type ProjectConfig = {
  project: Project;
  portals: Portal[];
  advertisers: Advertiser[];
};

type ProjectForm = {
  name: string;
  client_name: string;
  segment_id: string;
  description: string;
  active: boolean;
  monitor_publicity: boolean;
  monitor_editorial: boolean;
  monitor_market: boolean;
  monitor_checking: boolean;
};

const blankForm: ProjectForm = {
  name: "",
  client_name: "",
  segment_id: "",
  description: "",
  active: true,
  monitor_publicity: true,
  monitor_editorial: true,
  monitor_market: true,
  monitor_checking: true,
};

function projectToForm(project?: Project | null): ProjectForm {
  if (!project) return blankForm;
  return {
    name: project.name || "",
    client_name: project.client_name || "",
    segment_id: project.segment_id || "",
    description: project.description || "",
    active: project.active !== false,
    monitor_publicity: project.monitor_publicity !== false,
    monitor_editorial: project.monitor_editorial !== false,
    monitor_market: project.monitor_market !== false,
    monitor_checking: project.monitor_checking !== false,
  };
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  const d = new Date(value.endsWith("Z") ? value : `${value}Z`);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString("pt-BR");
}

function projectUrl(path: string, projectId: string) {
  return `${path}?project_id=${encodeURIComponent(projectId)}`;
}

function projectReportUrl(kind: "pdf" | "pptx", projectId: string, analysisMode: string) {
  const params = new URLSearchParams();
  params.set("analysis_mode", analysisMode || "market_wide");
  return `${API}/reports/project/${kind}/${projectId}?${params.toString()}`;
}

export default function ProjectsPage() {
  const [token, setToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [portals, setPortals] = useState<Portal[]>([]);
  const [advertisers, setAdvertisers] = useState<Advertiser[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState(DEFAULT_PROJECT_ID);
  const [config, setConfig] = useState<ProjectConfig | null>(null);
  const [form, setForm] = useState<ProjectForm>(blankForm);
  const [selectedPortal, setSelectedPortal] = useState("");
  const [selectedAdvertiser, setSelectedAdvertiser] = useState("");
  const [selectedRole, setSelectedRole] = useState("monitorado");
  const [reportAnalysisMode, setReportAnalysisMode] = useState("market_wide");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const authenticated = Boolean(token);
  const activeProject = useMemo(() => projects.find((p) => p.id === selectedProjectId) || config?.project || null, [projects, selectedProjectId, config]);

  async function getJson<T>(path: string): Promise<T> {
    return adminJson<T>(path, {
      bearer: false,
      admin: true,
      json: true,
    });
  }

  async function sendJson<T>(path: string, method: "POST" | "PUT", body: unknown): Promise<T> {
    return adminJson<T>(path, {
      method,
      body: JSON.stringify(body),
      bearer: false,
      admin: true,
      json: true,
    });
  }

  async function loadAll(projectId = selectedProjectId) {
    try {
      setLoading(true);
      setError("");
      const [projectsJson, segmentsJson, portalsJson, advertisersJson] = await Promise.all([
        getJson<Project[]>("/registry/projects"),
        getJson<Segment[]>("/registry/segments"),
        getJson<Portal[]>("/registry/portals"),
        getJson<Advertiser[]>("/registry/advertisers"),
      ]);

      const nextProjects = Array.isArray(projectsJson) ? projectsJson : [];
      const preferredProjectId = nextProjects.some((p) => p.id === projectId)
        ? projectId
        : nextProjects[0]?.id || projectId || DEFAULT_PROJECT_ID;

      const configJson = await getJson<ProjectConfig>(`/registry/projects/${preferredProjectId}/config`);

      setProjects(nextProjects);
      setSegments(Array.isArray(segmentsJson) ? segmentsJson : []);
      setPortals(Array.isArray(portalsJson) ? portalsJson : []);
      setAdvertisers(Array.isArray(advertisersJson) ? advertisersJson : []);
      setSelectedProjectId(preferredProjectId);
      setConfig(configJson);
      setForm(projectToForm(configJson.project));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar projetos.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const saved = localStorage.getItem(ADMIN_TOKEN_KEY) || "";
    setToken(saved);
    setTokenInput(saved);
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function chooseProject(projectId: string) {
    setSelectedProjectId(projectId);
    await loadAll(projectId);
  }

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

  async function createProject() {
    try {
      setError("");
      const created = await sendJson<Project>("/registry/projects", "POST", {
        ...form,
        segment_id: form.segment_id || null,
      });
      setMessage("Projeto criado.");
      await loadAll(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar projeto.");
    }
  }

  async function updateProject() {
    if (!selectedProjectId) return;
    try {
      setError("");
      await sendJson<Project>(`/registry/projects/${selectedProjectId}`, "PUT", {
        ...form,
        segment_id: form.segment_id || null,
      });
      setMessage("Projeto atualizado.");
      await loadAll(selectedProjectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao atualizar projeto.");
    }
  }

  async function bootstrapPortals() {
    if (!selectedProjectId) return;
    try {
      setError("");
      await sendJson(`/registry/projects/${selectedProjectId}/bootstrap-portals`, "POST", {});
      setMessage("Portais padrão vinculados ao projeto.");
      await loadAll(selectedProjectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao vincular portais padrão.");
    }
  }

  async function attachPortal(active = true, portalId = selectedPortal) {
    if (!selectedProjectId || !portalId) return;
    try {
      setError("");
      await sendJson(`/registry/projects/${selectedProjectId}/portals`, "POST", {
        portal_id: portalId,
        active,
      });
      setMessage(active ? "Portal vinculado ao projeto." : "Portal removido do projeto.");
      setSelectedPortal("");
      await loadAll(selectedProjectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao atualizar portal do projeto.");
    }
  }

  async function attachAdvertiser(active = true, advertiserId = selectedAdvertiser) {
    if (!selectedProjectId || !advertiserId) return;
    try {
      setError("");
      await sendJson(`/registry/projects/${selectedProjectId}/advertisers`, "POST", {
        advertiser_id: advertiserId,
        role: selectedRole,
        active,
      });
      setMessage(active ? "Anunciante vinculado ao projeto." : "Anunciante removido do projeto.");
      setSelectedAdvertiser("");
      await loadAll(selectedProjectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao atualizar anunciante do projeto.");
    }
  }

  const availablePortals = useMemo(() => {
    const linked = new Set((config?.portals || []).map((p) => p.id));
    return portals.filter((p) => !linked.has(p.id));
  }, [portals, config]);

  const availableAdvertisers = useMemo(() => {
    const linked = new Set((config?.advertisers || []).map((a) => a.id));
    const bySegment = form.segment_id ? advertisers.filter((a) => !a.segment_id || a.segment_id === form.segment_id) : advertisers;
    return bySegment.filter((a) => !linked.has(a.id));
  }, [advertisers, config, form.segment_id]);

  const totals = useMemo(() => ({
    projects: projects.length,
    active: projects.filter((p) => p.active !== false).length,
    portals: config?.portals?.length || 0,
    advertisers: config?.advertisers?.length || 0,
  }), [projects, config]);

  return (
    <AppShell
      title="Projetos monitorados"
      subtitle="Central multi-projeto para checking individual, inteligência de mercado e comparativos por segmento."
    >
      <section style={heroStyle}>
        <div>
          <div style={eyebrowStyle}>TV Fiscal WebMonitor</div>
          <h2 style={{ margin: "6px 0 8px", fontSize: 30 }}>Gestão operacional de projetos</h2>
          <p style={{ margin: 0, lineHeight: 1.6, maxWidth: 880 }}>
            Crie projetos por cliente, segmento ou campanha, vincule portais e anunciantes e abra Intel, Evidências e Comparativo já no contexto correto.
          </p>
        </div>
        <div style={{ minWidth: 330, display: "grid", gap: 10 }}>
          <input value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} placeholder="Token administrativo" style={inputStyle} />
          <div style={{ display: "flex", gap: 10 }}>
            <button type="button" onClick={login} style={primaryButtonStyle}>Usar token</button>
            {authenticated ? <button type="button" onClick={logout} style={secondaryButtonStyle}>Sair</button> : null}
          </div>
        </div>
      </section>

      {message ? <div style={successStyle}>{message}</div> : null}
      {error ? <div style={errorStyle}>{error}</div> : null}

      <section style={statsGridStyle}>
        <Stat title="Projetos" value={totals.projects} hint="Cadastrados" />
        <Stat title="Ativos" value={totals.active} hint="Aptos ao scheduler" />
        <Stat title="Portais vinculados" value={totals.portals} hint="Projeto selecionado" />
        <Stat title="Anunciantes" value={totals.advertisers} hint="Projeto selecionado" />
      </section>

      <section style={toolbarStyle}>
        <select value={selectedProjectId} onChange={(e) => chooseProject(e.target.value)} style={inputStyle}>
          {projects.length === 0 ? <option value={selectedProjectId}>Projeto ativo atual</option> : null}
          {projects.map((project) => (
            <option key={project.id} value={project.id}>{project.name} {project.client_name ? `· ${project.client_name}` : ""}</option>
          ))}
        </select>
        <button type="button" onClick={() => loadAll(selectedProjectId)} style={secondaryButtonStyle}>Atualizar</button>
        <button type="button" disabled={!authenticated} onClick={bootstrapPortals} style={primaryButtonStyle}>Criar/vincular portais padrão</button>
        <a href={projectUrl("/intel", selectedProjectId)} style={linkButtonStyle}>Abrir Intel</a>
        <a href={projectUrl("/evidencias", selectedProjectId)} style={linkButtonStyle}>Abrir Evidências</a>
        <a href={projectUrl("/intel/comparativo", selectedProjectId)} style={linkButtonStyle}>Abrir Comparativo</a>
        <select value={reportAnalysisMode} onChange={(e) => setReportAnalysisMode(e.target.value)} style={{ ...inputStyle, maxWidth: 260 }}>
          <option value="market_wide">Relatório: Mercado amplo</option>
          <option value="preserved_evidence">Relatório: Evidência preservada</option>
          <option value="classified_ads">Relatório: Publicidade classificada</option>
          <option value="checking_auditable">Relatório: Checking auditável</option>
        </select>
        <a href={projectReportUrl("pptx", selectedProjectId, reportAnalysisMode)} target="_blank" rel="noreferrer" style={{ ...linkButtonStyle, background: "#b00020" }}>Gerar Relatório Completo PPTX</a>
        <a href={projectReportUrl("pdf", selectedProjectId, reportAnalysisMode)} target="_blank" rel="noreferrer" style={{ ...linkButtonStyle, background: "#303846" }}>Gerar Relatório Completo PDF</a>
      </section>

      {loading ? <section style={panelStyle}>Carregando projetos...</section> : null}

      <section style={layoutGridStyle}>
        <div style={panelStyle}>
          <h3 style={panelTitleStyle}>Criar/editar projeto</h3>
          <label style={labelStyle}>Nome do projeto
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Ex.: Saúde PB — Unimed x Hapvida" style={inputStyle} />
          </label>
          <label style={labelStyle}>Cliente contratante
            <input value={form.client_name} onChange={(e) => setForm({ ...form, client_name: e.target.value })} placeholder="Ex.: Unimed João Pessoa" style={inputStyle} />
          </label>
          <label style={labelStyle}>Segmento principal
            <select value={form.segment_id} onChange={(e) => setForm({ ...form, segment_id: e.target.value })} style={inputStyle}>
              <option value="">Sem segmento definido</option>
              {segments.map((segment) => <option key={segment.id} value={segment.id}>{segment.name}</option>)}
            </select>
          </label>
          <label style={labelStyle}>Descrição
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Objetivo, período, observações comerciais..." style={textareaStyle} />
          </label>

          <div style={checksGridStyle}>
            <Check label="Projeto ativo" checked={form.active} onChange={(value) => setForm({ ...form, active: value })} />
            <Check label="Checking" checked={form.monitor_checking} onChange={(value) => setForm({ ...form, monitor_checking: value })} />
            <Check label="Publicidade" checked={form.monitor_publicity} onChange={(value) => setForm({ ...form, monitor_publicity: value })} />
            <Check label="Mercado" checked={form.monitor_market} onChange={(value) => setForm({ ...form, monitor_market: value })} />
            <Check label="Editorial" checked={form.monitor_editorial} onChange={(value) => setForm({ ...form, monitor_editorial: value })} />
          </div>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 16 }}>
            <button type="button" disabled={!authenticated || !form.name.trim()} onClick={createProject} style={primaryButtonStyle}>Criar novo projeto</button>
            <button type="button" disabled={!authenticated || !selectedProjectId || !form.name.trim()} onClick={updateProject} style={secondaryButtonStyle}>Salvar alterações</button>
          </div>
        </div>

        <div style={panelStyle}>
          <h3 style={panelTitleStyle}>Projeto selecionado</h3>
          {activeProject ? (
            <div>
              <div style={projectHeaderStyle}>
                <div>
                  <div style={badgeStyle}>{activeProject.active === false ? "Inativo" : "Ativo"}</div>
                  <h2 style={{ margin: "10px 0 4px" }}>{activeProject.name}</h2>
                  <div style={mutedStyle}>{activeProject.client_name || "Cliente não definido"}</div>
                </div>
              </div>
              <Info label="Project ID" value={activeProject.id} />
              <Info label="Segmento" value={activeProject.segment_name || "Não definido"} />
              <Info label="Criado em" value={formatDate(activeProject.created_at)} />
              <p style={{ color: "#596172", lineHeight: 1.55 }}>{activeProject.description || "Sem descrição."}</p>
            </div>
          ) : (
            <p>Nenhum projeto selecionado.</p>
          )}
        </div>
      </section>

      <section style={layoutGridStyle}>
        <div style={panelStyle}>
          <h3 style={panelTitleStyle}>Portais do projeto</h3>
          <div style={rowStyle}>
            <select value={selectedPortal} onChange={(e) => setSelectedPortal(e.target.value)} style={inputStyle}>
              <option value="">Selecionar portal</option>
              {availablePortals.map((portal) => <option key={portal.id} value={portal.id}>{portal.name} · {portal.base_url}</option>)}
            </select>
            <button type="button" disabled={!authenticated || !selectedPortal} onClick={() => attachPortal(true)} style={primaryButtonStyle}>Vincular</button>
          </div>
          <div style={listStyle}>
            {(config?.portals || []).length === 0 ? <div style={emptyStyle}>Nenhum portal vinculado.</div> : null}
            {(config?.portals || []).map((portal) => (
              <div key={portal.id} style={listItemStyle}>
                <div>
                  <strong>{portal.name}</strong>
                  <div style={mutedSmallStyle}>{portal.base_url}</div>
                </div>
                <button type="button" disabled={!authenticated} onClick={() => attachPortal(false, portal.id)} style={dangerButtonStyle}>Remover</button>
              </div>
            ))}
          </div>
        </div>

        <div style={panelStyle}>
          <h3 style={panelTitleStyle}>Anunciantes do projeto</h3>
          <div style={rowStyle}>
            <select value={selectedAdvertiser} onChange={(e) => setSelectedAdvertiser(e.target.value)} style={inputStyle}>
              <option value="">Selecionar anunciante</option>
              {availableAdvertisers.map((advertiser) => <option key={advertiser.id} value={advertiser.id}>{advertiser.name}{advertiser.segment_name ? ` · ${advertiser.segment_name}` : ""}</option>)}
            </select>
            <select value={selectedRole} onChange={(e) => setSelectedRole(e.target.value)} style={{ ...inputStyle, maxWidth: 180 }}>
              <option value="cliente">Cliente</option>
              <option value="concorrente">Concorrente</option>
              <option value="monitorado">Monitorado</option>
            </select>
            <button type="button" disabled={!authenticated || !selectedAdvertiser} onClick={() => attachAdvertiser(true)} style={primaryButtonStyle}>Vincular</button>
          </div>
          <div style={listStyle}>
            {(config?.advertisers || []).length === 0 ? <div style={emptyStyle}>Nenhum anunciante vinculado.</div> : null}
            {(config?.advertisers || []).map((advertiser) => (
              <div key={advertiser.id} style={listItemStyle}>
                <div>
                  <strong>{advertiser.name}</strong>
                  <div style={mutedSmallStyle}>{advertiser.segment_name || "Sem segmento"} · {advertiser.role || "monitorado"}</div>
                </div>
                <button type="button" disabled={!authenticated} onClick={() => attachAdvertiser(false, advertiser.id)} style={dangerButtonStyle}>Remover</button>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={panelTitleStyle}>Lista de projetos</h3>
        <div style={cardsGridStyle}>
          {projects.map((project) => (
            <article key={project.id} style={{ ...cardStyle, borderColor: project.id === selectedProjectId ? "#b00020" : "#e7eaf0" }}>
              <div style={badgeStyle}>{project.active === false ? "Inativo" : "Ativo"}</div>
              <h3 style={{ margin: "10px 0 6px" }}>{project.name}</h3>
              <div style={mutedSmallStyle}>{project.client_name || "Cliente não definido"}</div>
              <div style={mutedSmallStyle}>{project.segment_name || "Sem segmento"}</div>
              <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
                <span style={pillStyle}>{project.portals_count || 0} portais</span>
                <span style={pillStyle}>{project.advertisers_count || 0} anunciantes</span>
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
                <button type="button" onClick={() => chooseProject(project.id)} style={secondaryButtonStyle}>Editar</button>
                <a href={projectUrl("/intel", project.id)} style={miniLinkStyle}>Intel</a>
                <a href={projectUrl("/evidencias", project.id)} style={miniLinkStyle}>Evidências</a>
                <a href={projectUrl("/intel/comparativo", project.id)} style={miniLinkStyle}>Comparativo</a>
                <a href={projectReportUrl("pptx", project.id, reportAnalysisMode)} target="_blank" rel="noreferrer" style={{ ...miniLinkStyle, background: "#b00020", color: "#fff", borderColor: "#b00020" }}>PPTX completo</a>
                <a href={projectReportUrl("pdf", project.id, reportAnalysisMode)} target="_blank" rel="noreferrer" style={{ ...miniLinkStyle, background: "#303846", color: "#fff", borderColor: "#303846" }}>PDF completo</a>
              </div>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}

function Stat({ title, value, hint }: { title: string; value: string | number; hint?: string }) {
  return <div style={statCardStyle}><div style={mutedSmallStyle}>{title}</div><div style={statValueStyle}>{value}</div>{hint ? <div style={mutedSmallStyle}>{hint}</div> : null}</div>;
}

function Info({ label, value }: { label: string; value: string }) {
  return <div style={infoStyle}><div style={mutedSmallStyle}>{label}</div><strong style={{ wordBreak: "break-word" }}>{value}</strong></div>;
}

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <label style={checkStyle}><input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} /> {label}</label>;
}

const heroStyle: CSSProperties = { background: "linear-gradient(135deg,#6f0013,#b00020)", borderRadius: 24, padding: 26, color: "#fff", display: "flex", justifyContent: "space-between", gap: 20, marginBottom: 18 };
const eyebrowStyle: CSSProperties = { fontSize: 12, fontWeight: 900, textTransform: "uppercase", letterSpacing: ".16em", opacity: .85 };
const statsGridStyle: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(4,minmax(0,1fr))", gap: 14, marginBottom: 18 };
const statCardStyle: CSSProperties = { background: "#fff", borderRadius: 18, padding: 18, border: "1px solid #e7eaf0", boxShadow: "0 6px 18px rgba(15,23,42,.05)" };
const statValueStyle: CSSProperties = { fontSize: 34, fontWeight: 900, color: "#b00020", margin: "6px 0" };
const toolbarStyle: CSSProperties = { background: "#fff", borderRadius: 18, border: "1px solid #e7eaf0", padding: 16, display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 18 };
const layoutGridStyle: CSSProperties = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginBottom: 18 };
const panelStyle: CSSProperties = { background: "#fff", borderRadius: 20, padding: 20, border: "1px solid #e7eaf0", boxShadow: "0 6px 18px rgba(15,23,42,.05)", marginBottom: 18 };
const panelTitleStyle: CSSProperties = { margin: "0 0 14px", color: "#111827" };
const labelStyle: CSSProperties = { display: "grid", gap: 7, fontSize: 13, fontWeight: 800, color: "#374151", marginBottom: 12 };
const inputStyle: CSSProperties = { width: "100%", minHeight: 42, border: "1px solid #d8dde7", borderRadius: 12, padding: "10px 12px", background: "#fff", color: "#111827", WebkitTextFillColor: "#111827", colorScheme: "light", boxSizing: "border-box" };
const textareaStyle: CSSProperties = { ...inputStyle, minHeight: 96, resize: "vertical" };
const primaryButtonStyle: CSSProperties = { border: 0, borderRadius: 12, padding: "11px 14px", background: "#b00020", color: "#fff", fontWeight: 900, cursor: "pointer", textDecoration: "none" };
const secondaryButtonStyle: CSSProperties = { border: "1px solid #d8dde7", borderRadius: 12, padding: "11px 14px", background: "#fff", color: "#991b1b", fontWeight: 900, cursor: "pointer", textDecoration: "none" };
const dangerButtonStyle: CSSProperties = { ...secondaryButtonStyle, color: "#b00020", borderColor: "#fecaca", background: "#fff5f5" };
const linkButtonStyle: CSSProperties = { ...primaryButtonStyle, background: "#1f2937", display: "inline-flex", alignItems: "center" };
const miniLinkStyle: CSSProperties = { ...secondaryButtonStyle, padding: "8px 10px", fontSize: 12 };
const successStyle: CSSProperties = { background: "#ecfdf3", border: "1px solid #bbf7d0", color: "#166534", borderRadius: 14, padding: 12, marginBottom: 14, fontWeight: 800 };
const errorStyle: CSSProperties = { background: "#fff1f2", border: "1px solid #fecdd3", color: "#9f1239", borderRadius: 14, padding: 12, marginBottom: 14, fontWeight: 800 };
const checksGridStyle: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 8 };
const checkStyle: CSSProperties = { display: "flex", alignItems: "center", gap: 8, background: "#f8fafc", border: "1px solid #e7eaf0", borderRadius: 12, padding: "10px 12px", color: "#374151", fontWeight: 800 };
const projectHeaderStyle: CSSProperties = { background: "#f8fafc", border: "1px solid #e7eaf0", borderRadius: 16, padding: 16, marginBottom: 12 };
const badgeStyle: CSSProperties = { display: "inline-flex", padding: "5px 9px", borderRadius: 999, background: "#fef2f2", color: "#b00020", border: "1px solid #fecaca", fontSize: 12, fontWeight: 900 };
const mutedStyle: CSSProperties = { color: "#667085" };
const mutedSmallStyle: CSSProperties = { color: "#667085", fontSize: 12, lineHeight: 1.45 };
const infoStyle: CSSProperties = { background: "#fafafa", border: "1px solid #eef0f4", borderRadius: 12, padding: 12, marginBottom: 10 };
const rowStyle: CSSProperties = { display: "grid", gridTemplateColumns: "1fr auto auto", gap: 10, alignItems: "center", marginBottom: 14 };
const listStyle: CSSProperties = { display: "grid", gap: 10 };
const listItemStyle: CSSProperties = { border: "1px solid #e7eaf0", borderRadius: 14, padding: 12, display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" };
const emptyStyle: CSSProperties = { background: "#f8fafc", border: "1px dashed #d8dde7", borderRadius: 14, padding: 14, color: "#667085" };
const cardsGridStyle: CSSProperties = { display: "grid", gridTemplateColumns: "repeat(3,minmax(0,1fr))", gap: 14 };
const cardStyle: CSSProperties = { border: "1px solid #e7eaf0", borderRadius: 18, padding: 16, background: "#fff" };
const pillStyle: CSSProperties = { padding: "5px 8px", borderRadius: 999, background: "#f1f5f9", color: "#334155", fontSize: 12, fontWeight: 800 };
