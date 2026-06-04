"use client";

import React, { useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";
import { getAuthUser } from "../../../lib/auth";
import { adminJson } from "../../../lib/apiClient";

const API =
  (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_API_BASE ||
    "http://localhost:8000"
  ).replace(/\/$/, "");

const ADMIN_TOKEN_KEY = "tvfiscal_admin_token";
const DEFAULT_ADMIN_TOKEN = "tvfiscal-admin-2026";

function getAdminHeaders(includeContentType = true): Record<string, string> {
  const adminToken =
    typeof window !== "undefined"
      ? localStorage.getItem(ADMIN_TOKEN_KEY) || DEFAULT_ADMIN_TOKEN
      : DEFAULT_ADMIN_TOKEN;

  return {
    ...(includeContentType ? { "Content-Type": "application/json" } : {}),
    "X-Admin-Token": adminToken,
  };
}

type Role = { id: string; label: string; modules: string[] };
type User = {
  id: string;
  name: string;
  email: string;
  role: string;
  role_label?: string;
  active: boolean;
  project_ids: string[];
  allowed_modules: string[];
  last_login_at?: string | null;
  created_at?: string | null;
};
type Project = { id: string; name: string; client_name?: string | null; active: boolean };
type AuditItem = { id: string; user_email?: string | null; user_name?: string | null; action: string; status: string; ip_address?: string | null; detail?: string | null; created_at?: string | null };

type EditForm = {
  name: string;
  email: string;
  role: string;
  active: boolean;
  project_ids: string[];
  allowed_modules: string[];
};

function cardStyle(extra: React.CSSProperties = {}): React.CSSProperties {
  return { background: "#fff", borderRadius: 16, padding: 20, boxShadow: "0 4px 14px rgba(0,0,0,0.08)", ...extra };
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  try { return new Date(value).toLocaleString("pt-BR"); } catch { return value; }
}

function userToEditForm(user: User): EditForm {
  return {
    name: user.name || "",
    email: user.email || "",
    role: user.role || "cliente",
    active: Boolean(user.active),
    project_ids: Array.isArray(user.project_ids) ? user.project_ids : [],
    allowed_modules: Array.isArray(user.allowed_modules) ? user.allowed_modules : [],
  };
}

export default function UsersAdminPage() {
  const currentUser = getAuthUser();
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [audit, setAudit] = useState<AuditItem[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [editForm, setEditForm] = useState<EditForm | null>(null);

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "cliente",
    active: true,
    project_ids: [] as string[],
    allowed_modules: [] as string[],
  });

  const selectedUser = useMemo(() => users.find((user) => user.id === selectedUserId) || null, [selectedUserId, users]);

  async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
    return adminJson<T>(path, {
      ...options,
      bearer: false,
      admin: true,
      json: true,
    });
  }

  async function load() {
    setLoading(true);
    setMessage("");
    try {
      const [roleData, userData, projectData, auditData] = await Promise.all([
        api("/auth/roles"),
        api("/auth/users"),
        api("/auth/projects-summary"),
        api("/auth/audit?limit=50"),
      ]);
      setRoles(roleData.roles || []);
      setUsers(userData.items || []);
      setProjects(projectData.items || []);
      setAudit(auditData.items || []);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao carregar usuários.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (selectedUser) setEditForm(userToEditForm(selectedUser));
    else setEditForm(null);
  }, [selectedUser]);

  function toggleCreateProject(projectId: string) {
    setForm((old) => {
      const exists = old.project_ids.includes(projectId);
      return { ...old, project_ids: exists ? old.project_ids.filter((id) => id !== projectId) : [...old.project_ids, projectId] };
    });
  }

  function toggleEditProject(projectId: string) {
    setEditForm((old) => {
      if (!old) return old;
      const exists = old.project_ids.includes(projectId);
      return { ...old, project_ids: exists ? old.project_ids.filter((id) => id !== projectId) : [...old.project_ids, projectId] };
    });
  }

  function defaultModulesForRole(roleId: string) {
    return roles.find((role) => role.id === roleId)?.modules || [];
  }

  function toggleCreateModule(moduleId: string) {
    setForm((old) => {
      const exists = old.allowed_modules.includes(moduleId);
      return { ...old, allowed_modules: exists ? old.allowed_modules.filter((id) => id !== moduleId) : [...old.allowed_modules, moduleId] };
    });
  }

  function toggleEditModule(moduleId: string) {
    setEditForm((old) => {
      if (!old) return old;
      const exists = old.allowed_modules.includes(moduleId);
      return { ...old, allowed_modules: exists ? old.allowed_modules.filter((id) => id !== moduleId) : [...old.allowed_modules, moduleId] };
    });
  }

  function selectForEdit(user: User) {
    setSelectedUserId(user.id);
    setEditForm(userToEditForm(user));
    setNewPassword("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function createUser(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage("Criando usuário...");
    try {
      const user = await api("/auth/users", { method: "POST", body: JSON.stringify(form) });
      setMessage(`Usuário criado: ${user.email}`);
      setForm({ name: "", email: "", password: "", role: "cliente", active: true, project_ids: [], allowed_modules: [] });
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao criar usuário.");
    } finally {
      setLoading(false);
    }
  }

  async function saveEdit() {
    if (!selectedUser || !editForm) return;
    setLoading(true);
    setMessage("Salvando edição do usuário...");
    try {
      const user = await api(`/auth/users/${selectedUser.id}`, { method: "PUT", body: JSON.stringify(editForm) });
      setMessage(`Usuário editado: ${user.email}`);
      await load();
      setSelectedUserId(user.id);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao editar usuário.");
    } finally {
      setLoading(false);
    }
  }

  async function toggleActive(user: User) {
    setLoading(true);
    setMessage(user.active ? "Desativando usuário..." : "Reativando usuário...");
    try {
      const updated = await api(`/auth/users/${user.id}`, { method: "PUT", body: JSON.stringify({ active: !user.active }) });
      setMessage(`${updated.active ? "Usuário reativado" : "Usuário desativado"}: ${updated.email}`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao atualizar status do usuário.");
    } finally {
      setLoading(false);
    }
  }

  async function deactivate(user: User) {
    if (!confirm(`Desativar acesso de ${user.email}? O histórico será preservado.`)) return;
    setLoading(true);
    setMessage("Desativando usuário...");
    try {
      await api(`/auth/users/${user.id}`, { method: "DELETE" });
      setMessage(`Usuário desativado: ${user.email}`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao desativar usuário.");
    } finally {
      setLoading(false);
    }
  }

  async function purge(user: User) {
    if (!confirm(`Excluir definitivamente ${user.email}? Use apenas para cadastro errado. Esta ação remove o usuário da lista, mas a auditoria histórica permanece.`)) return;
    setLoading(true);
    setMessage("Excluindo usuário...");
    try {
      await api(`/auth/users/${user.id}/purge`, { method: "DELETE" });
      setMessage(`Usuário excluído definitivamente: ${user.email}`);
      if (selectedUserId === user.id) {
        setSelectedUserId("");
        setEditForm(null);
      }
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao excluir usuário.");
    } finally {
      setLoading(false);
    }
  }

  async function resetPassword() {
    if (!selectedUser || !newPassword) return;
    setLoading(true);
    setMessage("Redefinindo senha...");
    try {
      await api(`/auth/users/${selectedUser.id}/reset-password`, { method: "POST", body: JSON.stringify({ password: newPassword }) });
      setNewPassword("");
      setMessage(`Senha redefinida para ${selectedUser.email}`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao redefinir senha.");
    } finally {
      setLoading(false);
    }
  }

  const activeUsers = users.filter((u) => u.active).length;
  const externalUsers = users.filter((u) => u.role === "cliente").length;
  const adminUsers = users.filter((u) => u.role === "admin").length;

  return (
    <AppShell title="Usuários e Perfis" subtitle="Gestão de acesso, edição de usuários, redefinição de senha, exclusão controlada e auditoria.">
      {currentUser?.role !== "admin" && (
        <div style={cardStyle({ border: "1px solid #FDA29B", background: "#FEF3F2", color: "#B42318", marginBottom: 18 })}>
          Esta área é restrita ao perfil Administrador.
        </div>
      )}

      <section style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 18 }}>
        <Kpi title="Usuários" value={users.length} hint="cadastrados" />
        <Kpi title="Ativos" value={activeUsers} hint="com acesso" />
        <Kpi title="Admins" value={adminUsers} hint="acesso total" />
        <Kpi title="Clientes" value={externalUsers} hint="perfil externo" />
      </section>

      {message && <div style={{ ...cardStyle({ marginBottom: 18 }), color: message.includes("Erro") ? "#B42318" : "#027A48" }}>{message}</div>}

      <section style={{ display: "grid", gridTemplateColumns: "1.05fr 1.15fr", gap: 18, alignItems: "start" }}>
        <div style={cardStyle()}>
          <h2 style={{ marginTop: 0, color: "#101828" }}>Cadastrar usuário</h2>
          <form onSubmit={createUser} style={{ display: "grid", gap: 12 }}>
            <input placeholder="Nome" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required style={inputStyle} />
            <input placeholder="E-mail" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required style={inputStyle} />
            <input placeholder="Senha inicial" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required style={inputStyle} />
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value, allowed_modules: defaultModulesForRole(e.target.value) })} style={inputStyle}>
              {roles.map((role) => <option key={role.id} value={role.id}>{role.label}</option>)}
            </select>
            <label style={checkLabel}>
              <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
              Usuário ativo
            </label>
            <ProjectChecklist projects={projects} selected={form.project_ids} onToggle={toggleCreateProject} />
            <ModuleChecklist roles={roles} selected={form.allowed_modules.length ? form.allowed_modules : defaultModulesForRole(form.role)} onToggle={toggleCreateModule} onReset={() => setForm({ ...form, allowed_modules: defaultModulesForRole(form.role) })} />
            <button disabled={loading} style={buttonStyle}>{loading ? "Aguarde..." : "Criar usuário"}</button>
          </form>
        </div>

        <div style={cardStyle()}>
          <h2 style={{ marginTop: 0, color: "#101828" }}>Editar usuário / redefinir senha</h2>
          <p style={{ color: "#667085", fontSize: 13, marginTop: -6 }}>Selecione um usuário ou clique em “Editar” na tabela abaixo.</p>
          <select value={selectedUserId} onChange={(e) => setSelectedUserId(e.target.value)} style={inputStyle}>
            <option value="">Selecione um usuário</option>
            {users.map((user) => <option key={user.id} value={user.id}>{user.name} · {user.email}</option>)}
          </select>

          {selectedUser && editForm && (
            <div style={{ marginTop: 14, display: "grid", gap: 12 }}>
              <div style={{ background: "#F9FAFB", padding: 12, borderRadius: 12 }}>
                <strong>{selectedUser.name}</strong><br />
                <span style={{ color: "#667085", fontSize: 13 }}>{selectedUser.email}</span><br />
                <span style={{ color: selectedUser.active ? "#027A48" : "#B42318", fontSize: 13, fontWeight: 800 }}>{selectedUser.active ? "Ativo" : "Inativo"}</span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <input placeholder="Nome" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} style={inputStyle} />
                <input placeholder="E-mail" type="email" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} style={inputStyle} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 10, alignItems: "center" }}>
                <select value={editForm.role} onChange={(e) => setEditForm({ ...editForm, role: e.target.value, allowed_modules: defaultModulesForRole(e.target.value) })} style={inputStyle}>
                  {roles.map((role) => <option key={role.id} value={role.id}>{role.label}</option>)}
                </select>
                <label style={checkLabel}>
                  <input type="checkbox" checked={editForm.active} onChange={(e) => setEditForm({ ...editForm, active: e.target.checked })} />
                  Ativo
                </label>
              </div>

              <ProjectChecklist projects={projects} selected={editForm.project_ids} onToggle={toggleEditProject} />
              <ModuleChecklist roles={roles} selected={editForm.allowed_modules.length ? editForm.allowed_modules : defaultModulesForRole(editForm.role)} onToggle={toggleEditModule} onReset={() => setEditForm({ ...editForm, allowed_modules: defaultModulesForRole(editForm.role) })} />

              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <button onClick={saveEdit} disabled={loading} style={buttonStyle}>Salvar alterações</button>
                <button onClick={() => toggleActive(selectedUser)} disabled={loading} style={secondaryButtonStyle}>{selectedUser.active ? "Desativar usuário" : "Reativar usuário"}</button>
                <button onClick={() => purge(selectedUser)} disabled={loading || selectedUser.id === currentUser?.id} style={dangerButtonStyle}>Excluir definitivo</button>
              </div>

              <div style={{ background: "#FFFAEB", border: "1px solid #FEDF89", borderRadius: 12, padding: 12 }}>
                <strong style={{ color: "#93370D" }}>Redefinir senha</strong>
                <p style={{ color: "#93370D", fontSize: 12, margin: "4px 0 10px" }}>Use quando o usuário esquecer a senha ou quando for necessário entregar uma senha temporária.</p>
                <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8 }}>
                  <input placeholder="Nova senha" type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} style={inputStyle} />
                  <button onClick={resetPassword} disabled={!newPassword || loading} style={buttonStyle}>Redefinir senha</button>
                </div>
              </div>

              <div style={{ fontSize: 12, color: "#667085" }}>
                Último login: {formatDate(selectedUser.last_login_at)}<br />
                Criado em: {formatDate(selectedUser.created_at)}
              </div>
            </div>
          )}
        </div>
      </section>

      <section style={{ ...cardStyle({ marginTop: 18 }) }}>
        <h2 style={{ marginTop: 0 }}>Usuários cadastrados</h2>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#F2F4F7", color: "#344054", textAlign: "left" }}>
                <th style={th}>Nome</th><th style={th}>E-mail</th><th style={th}>Perfil</th><th style={th}>Projetos</th><th style={th}>Status</th><th style={th}>Último login</th><th style={th}>Ações</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} style={{ borderBottom: "1px solid #EAECF0" }}>
                  <td style={td}>{user.name}</td>
                  <td style={td}>{user.email}</td>
                  <td style={td}>{user.role_label || user.role}</td>
                  <td style={td}>{user.project_ids?.length ? user.project_ids.length : "Todos/sem restrição"}</td>
                  <td style={td}><span style={{ color: user.active ? "#027A48" : "#B42318", fontWeight: 800 }}>{user.active ? "Ativo" : "Inativo"}</span></td>
                  <td style={td}>{formatDate(user.last_login_at)}</td>
                  <td style={td}>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      <button onClick={() => selectForEdit(user)} style={smallButtonStyle}>Editar</button>
                      <button onClick={() => { selectForEdit(user); setTimeout(() => window.scrollTo({ top: 0, behavior: "smooth" }), 20); }} style={smallButtonStyle}>Senha</button>
                      <button onClick={() => toggleActive(user)} style={smallSecondaryButtonStyle}>{user.active ? "Desativar" : "Reativar"}</button>
                      <button onClick={() => purge(user)} disabled={user.id === currentUser?.id} style={smallDangerButtonStyle}>Excluir</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p style={{ color: "#667085", fontSize: 12 }}>Recomendação: use “Desativar” para preservar histórico operacional. Use “Excluir” apenas para cadastro criado errado.</p>
      </section>

      <section style={{ ...cardStyle({ marginTop: 18 }) }}>
        <h2 style={{ marginTop: 0 }}>Auditoria de acesso</h2>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr style={{ background: "#F2F4F7", textAlign: "left" }}><th style={th}>Data</th><th style={th}>Usuário</th><th style={th}>Ação</th><th style={th}>Status</th><th style={th}>IP</th><th style={th}>Detalhe</th></tr></thead>
            <tbody>
              {audit.map((item) => (
                <tr key={item.id} style={{ borderBottom: "1px solid #EAECF0" }}>
                  <td style={td}>{formatDate(item.created_at)}</td>
                  <td style={td}>{item.user_email || item.user_name || "—"}</td>
                  <td style={td}>{item.action}</td>
                  <td style={td}>{item.status}</td>
                  <td style={td}>{item.ip_address || "—"}</td>
                  <td style={td}>{item.detail || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}

function ProjectChecklist({ projects, selected, onToggle }: { projects: Project[]; selected: string[]; onToggle: (id: string) => void }) {
  return (
    <div style={{ background: "#F9FAFB", borderRadius: 12, padding: 12 }}>
      <strong style={{ color: "#344054" }}>Projetos liberados</strong>
      <p style={{ margin: "4px 0 10px", color: "#667085", fontSize: 12 }}>Para admin/gestor, deixar vazio permite visão ampla. Para cliente externo, selecione apenas os projetos permitidos.</p>
      <div style={{ display: "grid", gap: 8, maxHeight: 160, overflow: "auto" }}>
        {projects.map((project) => (
          <label key={project.id} style={{ display: "flex", gap: 8, fontSize: 12, color: "#344054" }}>
            <input type="checkbox" checked={selected.includes(project.id)} onChange={() => onToggle(project.id)} />
            {project.name} {project.client_name ? `· ${project.client_name}` : ""}
          </label>
        ))}
      </div>
    </div>
  );
}

function ModuleChecklist({ roles, selected, onToggle, onReset }: { roles: Role[]; selected: string[]; onToggle: (id: string) => void; onReset: () => void }) {
  const moduleMap = new Map<string, string>();
  roles.forEach((role) => (role.modules || []).forEach((moduleId) => {
    if (!moduleMap.has(moduleId)) moduleMap.set(moduleId, moduleId);
  }));
  const modules = Array.from(moduleMap.keys()).sort((a, b) => a.localeCompare(b));
  return (
    <div style={{ background: "#F9FAFB", borderRadius: 12, padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <strong style={{ color: "#344054" }}>Módulos liberados</strong>
        <button type="button" onClick={onReset} style={smallSecondaryButtonStyle}>Usar padrão do perfil</button>
      </div>
      <p style={{ margin: "4px 0 10px", color: "#667085", fontSize: 12 }}>A V42 aplica essa permissão também no backend. Para Administrador, “*” libera tudo.</p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8, maxHeight: 190, overflow: "auto" }}>
        {modules.map((moduleId) => (
          <label key={moduleId} style={{ display: "flex", gap: 8, fontSize: 12, color: "#344054" }}>
            <input type="checkbox" checked={selected.includes(moduleId)} onChange={() => onToggle(moduleId)} />
            {moduleId}
          </label>
        ))}
      </div>
    </div>
  );
}

function Kpi({ title, value, hint }: { title: string; value: number; hint: string }) {
  return (
    <div style={cardStyle()}>
      <div style={{ color: "#667085", fontSize: 12, fontWeight: 800, textTransform: "uppercase" }}>{title}</div>
      <div style={{ color: "#101828", fontSize: 30, fontWeight: 900, marginTop: 8 }}>{value}</div>
      <div style={{ color: "#667085", fontSize: 12 }}>{hint}</div>
    </div>
  );
}

const inputStyle: React.CSSProperties = { minHeight: 42, border: "1px solid #D0D5DD", borderRadius: 10, padding: "0 12px", fontSize: 14, background: "#fff" };
const checkLabel: React.CSSProperties = { display: "flex", gap: 8, alignItems: "center", color: "#344054", fontSize: 13 };
const buttonStyle: React.CSSProperties = { border: 0, borderRadius: 10, padding: "10px 14px", background: "#b00020", color: "#fff", fontWeight: 900, cursor: "pointer" };
const secondaryButtonStyle: React.CSSProperties = { border: "1px solid #D0D5DD", borderRadius: 10, padding: "10px 14px", background: "#fff", color: "#344054", fontWeight: 800, cursor: "pointer" };
const dangerButtonStyle: React.CSSProperties = { border: 0, borderRadius: 10, padding: "10px 14px", background: "#B42318", color: "#fff", fontWeight: 800, cursor: "pointer" };
const smallButtonStyle: React.CSSProperties = { border: "1px solid #B00020", borderRadius: 8, padding: "6px 9px", background: "#fff", color: "#B00020", fontWeight: 800, cursor: "pointer", fontSize: 12 };
const smallSecondaryButtonStyle: React.CSSProperties = { border: "1px solid #D0D5DD", borderRadius: 8, padding: "6px 9px", background: "#fff", color: "#344054", fontWeight: 800, cursor: "pointer", fontSize: 12 };
const smallDangerButtonStyle: React.CSSProperties = { border: 0, borderRadius: 8, padding: "6px 9px", background: "#B42318", color: "#fff", fontWeight: 800, cursor: "pointer", fontSize: 12 };
const th: React.CSSProperties = { padding: 10, borderBottom: "1px solid #D0D5DD" };
const td: React.CSSProperties = { padding: 10, verticalAlign: "top" };
