"use client";

import React, { useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";

const API = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";
const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";
const DEFAULT_TOKEN = "tvfiscal-admin-2026";

type Contact = {
  id: string;
  name: string;
  role?: string;
  email?: string;
  phone?: string;
  whatsapp?: string;
  channels: string[];
  priority?: string;
  active: boolean;
};

type Rule = {
  id: string;
  name: string;
  active: boolean;
  event_type: string;
  terms: string[];
  categories: string[];
  channels: string[];
  contact_ids: string[];
  severity_min: string;
  sentiment_filter?: string | null;
  cooldown_minutes: number;
  last_triggered_at?: string | null;
};

type Log = {
  id: string;
  created_at?: string;
  channel: string;
  status: string;
  severity?: string;
  category?: string;
  title?: string;
  message?: string;
  target_url?: string;
  provider?: string;
  provider_response?: string;
};

type Dashboard = {
  config: Record<string, unknown>;
  summary: {
    contacts: number;
    active_contacts: number;
    rules: number;
    active_rules: number;
    logs: number;
    sent: number;
    registered: number;
    dry_run: number;
    errors: number;
  };
  contacts: Contact[];
  rules: Rule[];
  logs: Log[];
  provider_profiles?: any;
  automation_runs?: any[];
  inbox_summary?: any;
};

function splitList(value: string) {
  return value.split(/[,;\n]/).map((x) => x.trim()).filter(Boolean);
}

function joinList(value?: string[]) {
  return (value || []).join(", ");
}

function fmtDate(value?: string | null) {
  if (!value) return "—";
  try {
    const text = String(value);
    const normalized = /[zZ]|[+-]\d{2}:?\d{2}$/.test(text) ? text : `${text}Z`;
    return new Date(normalized).toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
  } catch { return value; }
}

function logDate(log: Log) {
  return (log as any).created_at_display || fmtDate(log.created_at);
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    sent: "Enviado",
    registered: "Painel",
    dry_run: "Simulado",
    skipped: "Ignorado",
    error: "Erro",
  };
  return map[status] || status;
}

function channelLabel(channel: string) {
  const map: Record<string, string> = { painel: "Painel", sms: "SMS", email: "E-mail", whatsapp: "WhatsApp", webhook: "Webhook" };
  return map[channel] || channel;
}

export default function NotificationsAdminPage() {
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);
  const [token, setToken] = useState(DEFAULT_TOKEN);
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [contactForm, setContactForm] = useState({ name: "", role: "", email: "", phone: "", whatsapp: "", channels: "painel, sms, email", priority: "normal" });
  const [ruleForm, setRuleForm] = useState({
    name: "Menção crítica de marca/personalidade",
    event_type: "editorial_mention",
    terms: "",
    categories: "editorial",
    channels: "painel, sms, email",
    contact_ids: "",
    severity_min: "medio",
    sentiment_filter: "",
    cooldown_minutes: "60",
  });
  const [realEmailForm, setRealEmailForm] = useState({
    smtp_host: "",
    smtp_port: "587",
    smtp_use_tls: true,
    smtp_user: "",
    smtp_password: "",
    smtp_from: "",
    to: "",
    subject: "TV Fiscal - Teste real de alerta SMTP",
    message: "Teste real de envio pelo Motor de Notificações do TV Fiscal WebMonitor.",
  });

  const [smsForm, setSmsForm] = useState({
    provider: "webhook",
    webhook_url: "",
    account_sid: "",
    auth_token: "",
    from_number: "",
    api_token: "",
    from_name: "TVFiscal",
    access_token: "",
    to: "",
    title: "TV Fiscal - Teste real SMS",
    message: "Teste real de SMS pelo Motor de Notificações do TV Fiscal WebMonitor.",
  });

  const [whatsappForm, setWhatsappForm] = useState({
    provider: "webhook",
    webhook_url: "",
    api_token: "",
    from_number: "",
    access_token: "",
    phone_number_id: "",
    to: "",
    title: "TV Fiscal - Teste real WhatsApp",
    message: "Teste real de WhatsApp pelo Motor de Notificações do TV Fiscal WebMonitor.",
  });

  async function api(path: string, options: RequestInit = {}) {
    const headers: Record<string, string> = { "Content-Type": "application/json", "X-Admin-Token": token };
    const res = await fetch(`${API}${path}`, { ...options, headers: { ...headers, ...(options.headers || {}) }, cache: "no-store" });
    if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);
    return res.json();
  }

  async function load(customProjectId = projectId) {
    setLoading(true);
    setMessage("");
    try {
      const payload = await api(`/notifications/dashboard/${customProjectId}`);
      setData(payload);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao carregar notificações.");
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

  const contactOptions = useMemo(() => (data?.contacts || []).filter((c) => c.active), [data]);

  async function createContact() {
    const payload = { ...contactForm, channels: splitList(contactForm.channels), active: true };
    await api(`/notifications/contacts/${projectId}`, { method: "POST", body: JSON.stringify(payload) });
    setContactForm({ name: "", role: "", email: "", phone: "", whatsapp: "", channels: "painel, sms, email", priority: "normal" });
    setMessage("Contato salvo.");
    await load();
  }

  async function createRule() {
    const payload = {
      name: ruleForm.name,
      event_type: ruleForm.event_type,
      terms: splitList(ruleForm.terms),
      categories: splitList(ruleForm.categories),
      channels: splitList(ruleForm.channels),
      contact_ids: splitList(ruleForm.contact_ids),
      severity_min: ruleForm.severity_min,
      sentiment_filter: ruleForm.sentiment_filter || null,
      cooldown_minutes: Number(ruleForm.cooldown_minutes || 60),
      active: true,
    };
    await api(`/notifications/rules/${projectId}`, { method: "POST", body: JSON.stringify(payload) });
    setMessage("Regra salva.");
    await load();
  }

  async function bootstrapRules() {
    const payload = await api(`/notifications/bootstrap/${projectId}`, { method: "POST", body: JSON.stringify({}) });
    setMessage(`Regras padrão verificadas. Criadas: ${payload.created || 0}.`);
    await load();
  }

  async function evaluateNow() {
    const payload = await api(`/notifications/evaluate/${projectId}?source=manual_ui`, { method: "POST", body: JSON.stringify({}) });
    setMessage(`Avaliação concluída: ${payload.notifications || 0} notificação(ões) registrada(s).`);
    await load();
  }

  async function automationTest() {
    const payload = await api(`/notifications/automation-test/${projectId}?source=manual_v32&event_limit=120&window_minutes=180`, { method: "POST", body: JSON.stringify({}) });
    setMessage(`Automação executada: ${payload.notifications || 0} notificação(ões), ${payload.skipped_duplicates || 0} duplicidade(s) ignorada(s).`);
    await load();
  }

  async function cleanupDuplicates() {
    const payload = await api(`/notifications/cleanup/${projectId}`, { method: "POST", body: JSON.stringify({}) });
    setMessage(`Limpeza concluída: ${payload.contacts_deactivated || 0} contato(s) e ${payload.rules_deactivated || 0} regra(s) duplicada(s) desativada(s).`);
    await load();
  }

  async function testNotification(channel = "painel") {
    const first = contactOptions[0];
    const payload = await api(`/notifications/test/${projectId}`, {
      method: "POST",
      body: JSON.stringify({ contact_id: first?.id, channel, message: "Teste do Motor de Notificações TV Fiscal." }),
    });
    setMessage(`Teste ${channelLabel(channel)}: ${payload.log?.status || "registrado"}.`);
    await load();
  }

  async function testRealEmail() {
    const payload = await api(`/notifications/test-real-email/${projectId}`, {
      method: "POST",
      body: JSON.stringify({
        ...realEmailForm,
        smtp_port: Number(realEmailForm.smtp_port || 587),
      }),
    });
    setMessage(payload.message || `Teste real SMTP: ${payload.log?.status || "registrado"}.`);
    await load();
  }

  async function saveAutomaticSmtp() {
    const payload = await api(`/notifications/provider-settings/${projectId}/email-smtp`, {
      method: "POST",
      body: JSON.stringify({
        ...realEmailForm,
        smtp_port: Number(realEmailForm.smtp_port || 587),
        active: true,
      }),
    });
    setMessage(payload.message || "SMTP automático salvo.");
    await load();
  }

  async function disableAutomaticSmtp() {
    const payload = await api(`/notifications/provider-settings/${projectId}/email-smtp`, { method: "DELETE" });
    setMessage(payload.message || "SMTP automático desativado.");
    await load();
  }

  async function testAutomaticEmail() {
    const payload = await api(`/notifications/test-automatic-email/${projectId}`, {
      method: "POST",
      body: JSON.stringify({
        subject: "TV Fiscal - Teste automático por regra",
        message: "Teste real usando o mesmo perfil SMTP salvo para as regras automáticas do projeto.",
      }),
    });
    setMessage(payload.message || `Teste automático: ${payload.log?.status || "registrado"}.`);
    await load();
  }

  async function saveSmsProvider() {
    const payload = await api(`/notifications/provider-settings/${projectId}/sms`, {
      method: "POST",
      body: JSON.stringify({ ...smsForm, active: true }),
    });
    setMessage(payload.message || "Provedor SMS salvo.");
    await load();
  }

  async function disableSmsProvider() {
    const payload = await api(`/notifications/provider-settings/${projectId}/sms`, { method: "DELETE" });
    setMessage(payload.message || "Provedor SMS desativado.");
    await load();
  }

  async function testRealSms() {
    const payload = await api(`/notifications/test-real-sms/${projectId}`, {
      method: "POST",
      body: JSON.stringify(smsForm),
    });
    setMessage(payload.message || `Teste real SMS: ${payload.log?.status || "registrado"}.`);
    await load();
  }

  async function testAutomaticSms() {
    const payload = await api(`/notifications/test-automatic-sms/${projectId}`, {
      method: "POST",
      body: JSON.stringify({ title: "TV Fiscal - Teste automático SMS", message: "Teste usando o provedor SMS salvo para regras automáticas." }),
    });
    setMessage(payload.message || `Teste automático SMS: ${payload.log?.status || "registrado"}.`);
    await load();
  }

  async function saveWhatsappProvider() {
    const payload = await api(`/notifications/provider-settings/${projectId}/whatsapp`, {
      method: "POST",
      body: JSON.stringify({ ...whatsappForm, active: true }),
    });
    setMessage(payload.message || "Provedor WhatsApp salvo.");
    await load();
  }

  async function disableWhatsappProvider() {
    const payload = await api(`/notifications/provider-settings/${projectId}/whatsapp`, { method: "DELETE" });
    setMessage(payload.message || "Provedor WhatsApp desativado.");
    await load();
  }

  async function testRealWhatsapp() {
    const payload = await api(`/notifications/test-real-whatsapp/${projectId}`, {
      method: "POST",
      body: JSON.stringify(whatsappForm),
    });
    setMessage(payload.message || `Teste real WhatsApp: ${payload.log?.status || "registrado"}.`);
    await load();
  }

  async function testAutomaticWhatsapp() {
    const payload = await api(`/notifications/test-automatic-whatsapp/${projectId}`, {
      method: "POST",
      body: JSON.stringify({ title: "TV Fiscal - Teste automático WhatsApp", message: "Teste usando o provedor WhatsApp salvo para regras automáticas." }),
    });
    setMessage(payload.message || `Teste automático WhatsApp: ${payload.log?.status || "registrado"}.`);
    await load();
  }

  async function deactivateRule(ruleId: string) {
    await api(`/notifications/rules/${ruleId}`, { method: "DELETE" });
    setMessage("Regra desativada.");
    await load();
  }

  async function deactivateContact(contactId: string) {
    await api(`/notifications/contacts/${contactId}`, { method: "DELETE" });
    setMessage("Contato desativado.");
    await load();
  }

  function exportLogs() {
    window.open(`${API}/notifications/logs/${projectId}/export.csv`, "_blank");
  }

  return (
    <AppShell
      title="Motor de Notificações"
      subtitle="Alertas por projeto para SMS, e-mail, WhatsApp, painel interno e webhooks, com regras por marca, personalidade, sentimento e severidade."
    >
      <section style={heroStyle}>
        <div>
          <div style={eyebrowStyle}>NOTIFICATION ENGINE · TV FISCAL WEBMONITOR</div>
          <h2 style={{ margin: "8px 0 10px", fontSize: 32 }}>Alertas automáticos por menção, marca e risco</h2>
          <p style={{ margin: 0, maxWidth: 860, lineHeight: 1.65 }}>
            Cadastre contatos, defina regras por projeto e receba alertas quando uma personalidade, cliente, marca ou termo sensível aparecer em notícia, clipping editorial ou alerta executivo.
          </p>
        </div>
        <div style={{ display: "grid", gap: 10, minWidth: 380 }}>
          <input value={projectId} onChange={(e) => setProjectId(e.target.value)} style={inputStyle} />
          <input value={token} onChange={(e) => setToken(e.target.value)} style={inputStyle} type="password" />
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button style={primaryButtonStyle} onClick={() => load()}>{loading ? "Atualizando..." : "Atualizar"}</button>
            <button style={secondaryButtonStyle} onClick={bootstrapRules}>Criar regras padrão</button>
            <button style={secondaryButtonStyle} onClick={evaluateNow}>Avaliar agora</button>
            <button style={secondaryButtonStyle} onClick={automationTest}>Simular pós-coleta</button>
            <button style={secondaryButtonStyle} onClick={cleanupDuplicates}>Limpar duplicidades</button>
            <button style={secondaryButtonStyle} onClick={exportLogs}>Exportar logs</button>
            <a style={{ ...secondaryButtonStyle, textDecoration: "none" }} href={`/alerts/inbox?project_id=${projectId}`}>Abrir caixa</a>
          </div>
        </div>
      </section>

      {message ? <div style={messageStyle}>{message}</div> : null}

      <section style={kpiGridStyle}>
        <Kpi label="Contatos" value={data?.summary.active_contacts || 0} hint="ativos" />
        <Kpi label="Regras" value={data?.summary.active_rules || 0} hint="ativas" />
        <Kpi label="Logs" value={data?.summary.logs || 0} hint="recentes" />
        <Kpi label="Enviados" value={data?.summary.sent || 0} hint="provedor real" />
        <Kpi label="Painel" value={data?.summary.registered || 0} hint="internos" />
        <Kpi label="Simulados" value={data?.summary.dry_run || 0} hint="dry-run" />
        <Kpi label="Erros" value={data?.summary.errors || 0} hint="falhas" />
        <Kpi label="Alertas abertos" value={(data as any)?.inbox_summary?.open || 0} hint="caixa operacional" />
        <Kpi label="Dry-run" value={data?.config?.dry_run ? "Ativo" : "Off"} hint="configuração" />
      </section>

      <section style={panelStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div>
            <h3 style={{ margin: 0 }}>Status dos provedores</h3>
            <p style={{ margin: "6px 0 0", color: "#667085" }}>Validação das variáveis de ambiente para envio real. Enquanto o dry-run estiver ativo, todos os envios externos serão simulados.</p>
            <p style={{ margin: "6px 0 0", color: "#98a2b3", fontSize: 12 }}>Fuso do sistema: {(data?.config as any)?.timezone || "America/Sao_Paulo"} · Hora local do servidor: {(data?.config as any)?.server_time_display || "—"}</p>
          </div>
          <span style={{ ...badgeStyle, background: data?.config?.dry_run ? "#fff7ed" : "#ecfdf3", color: data?.config?.dry_run ? "#9a3412" : "#027a48" }}>
            {data?.config?.dry_run ? "Dry-run ativo" : "Envio real ativo"}
          </span>
        </div>
        <div style={providerGridStyle}>
          <ProviderCard name="SMS" info={(data?.config?.provider_status as any)?.sms} />
          <ProviderCard name="E-mail" info={(data?.config?.provider_status as any)?.email} />
          <ProviderCard name="WhatsApp" info={(data?.config?.provider_status as any)?.whatsapp} />
          <ProviderCard name="Webhook" info={(data?.config?.provider_status as any)?.webhook} />
        </div>
      </section>

      <section style={panelStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div>
            <h3 style={{ margin: 0 }}>Automação pós-coleta</h3>
            <p style={{ margin: "6px 0 0", color: "#667085", lineHeight: 1.55 }}>
              O motor avalia regras automaticamente após coleta editorial e após o scheduler/varredura de portais. A janela padrão usa eventos recentes para evitar disparo massivo de clipping antigo.
            </p>
            <p style={{ margin: "6px 0 0", color: "#98a2b3", fontSize: 12 }}>
              Editorial: {(data?.config as any)?.auto_after_editorial ? "ativo" : "inativo"} · Scheduler: {(data?.config as any)?.auto_after_scheduler ? "ativo" : "inativo"} · Janela: {(data?.config as any)?.auto_event_window_minutes || 180} min · Limite: {(data?.config as any)?.auto_event_limit || 120} eventos
            </p>
          </div>
          <button style={primaryButtonStyle} onClick={automationTest}>Testar fluxo automático</button>
        </div>
        <div style={{ overflowX: "auto", marginTop: 14 }}>
          <table style={tableStyle}>
            <thead><tr><th>Data</th><th>Origem</th><th>Status</th><th>Eventos</th><th>Notificações</th><th>Enviados</th><th>Duplicidades</th><th>Mensagem</th></tr></thead>
            <tbody>
              {(data?.automation_runs || []).map((run: any) => (
                <tr key={run.id}>
                  <td>{run.created_at_display || run.created_at || "—"}</td>
                  <td>{run.trigger_source || "—"}</td>
                  <td>{run.status || "—"}</td>
                  <td>{run.events_count ?? 0}</td>
                  <td>{run.notifications_count ?? 0}</td>
                  <td>{run.sent_count ?? 0}</td>
                  <td>{run.skipped_duplicates ?? 0}</td>
                  <td>{run.message || "—"}</td>
                </tr>
              ))}
              {!data?.automation_runs?.length ? <tr><td colSpan={8}>Nenhuma execução automática registrada.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      <section style={twoColumnsStyle}>
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Cadastrar contato</h3>
          <div style={formGridStyle}>
            <input placeholder="Nome" value={contactForm.name} onChange={(e) => setContactForm({ ...contactForm, name: e.target.value })} style={inputStyle} />
            <input placeholder="Cargo/função" value={contactForm.role} onChange={(e) => setContactForm({ ...contactForm, role: e.target.value })} style={inputStyle} />
            <input placeholder="E-mail" value={contactForm.email} onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })} style={inputStyle} />
            <input placeholder="Telefone SMS" value={contactForm.phone} onChange={(e) => setContactForm({ ...contactForm, phone: e.target.value })} style={inputStyle} />
            <input placeholder="WhatsApp" value={contactForm.whatsapp} onChange={(e) => setContactForm({ ...contactForm, whatsapp: e.target.value })} style={inputStyle} />
            <input placeholder="Canais: painel, sms, email" value={contactForm.channels} onChange={(e) => setContactForm({ ...contactForm, channels: e.target.value })} style={inputStyle} />
          </div>
          <button onClick={createContact} style={primaryButtonStyle}>Salvar contato</button>
        </div>

        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Criar regra de alerta</h3>
          <div style={formGridStyle}>
            <input placeholder="Nome da regra" value={ruleForm.name} onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })} style={inputStyle} />
            <select value={ruleForm.event_type} onChange={(e) => setRuleForm({ ...ruleForm, event_type: e.target.value })} style={selectStyle}>
              <option value="any">Qualquer evento</option>
              <option value="editorial_mention">Menção editorial</option>
              <option value="editorial_negative">Notícia negativa</option>
              <option value="executive_alert">Alerta executivo</option>
              <option value="checking_auditable">Publicidade auditável</option>
            </select>
            <input placeholder="Termos: nome, marca, personalidade" value={ruleForm.terms} onChange={(e) => setRuleForm({ ...ruleForm, terms: e.target.value })} style={inputStyle} />
            <input placeholder="Categorias: editorial, checking..." value={ruleForm.categories} onChange={(e) => setRuleForm({ ...ruleForm, categories: e.target.value })} style={inputStyle} />
            <input placeholder="Canais: painel, sms, email, whatsapp" value={ruleForm.channels} onChange={(e) => setRuleForm({ ...ruleForm, channels: e.target.value })} style={inputStyle} />
            <select value={ruleForm.severity_min} onChange={(e) => setRuleForm({ ...ruleForm, severity_min: e.target.value })} style={selectStyle}>
              <option value="informativo">Informativo ou maior</option>
              <option value="medio">Médio ou maior</option>
              <option value="alto">Alto ou crítico</option>
              <option value="critico">Somente crítico</option>
            </select>
            <select value={ruleForm.sentiment_filter} onChange={(e) => setRuleForm({ ...ruleForm, sentiment_filter: e.target.value })} style={selectStyle}>
              <option value="">Qualquer sentimento</option>
              <option value="negativo">Negativo</option>
              <option value="neutro">Neutro</option>
              <option value="positivo">Positivo</option>
            </select>
            <input placeholder="Cooldown em minutos" value={ruleForm.cooldown_minutes} onChange={(e) => setRuleForm({ ...ruleForm, cooldown_minutes: e.target.value })} style={inputStyle} />
            <select value={ruleForm.contact_ids} onChange={(e) => setRuleForm({ ...ruleForm, contact_ids: e.target.value })} style={selectStyle}>
              <option value="">Todos os contatos ativos</option>
              {contactOptions.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <button onClick={createRule} style={primaryButtonStyle}>Salvar regra</button>
        </div>
      </section>

      <section style={panelStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
          <div>
            <h3 style={{ margin: 0 }}>Testes de envio</h3>
            <p style={{ margin: "5px 0 0", color: "#667085" }}>Por padrão, o sistema registra no painel ou simula envio quando NOTIFICATION_DRY_RUN=true.</p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button style={secondaryButtonStyle} onClick={() => testNotification("painel")}>Teste Painel</button>
            <button style={secondaryButtonStyle} onClick={() => testNotification("sms")}>Teste SMS</button>
            <button style={secondaryButtonStyle} onClick={() => testNotification("email")}>Teste E-mail</button>
            <button style={secondaryButtonStyle} onClick={() => testNotification("whatsapp")}>Teste WhatsApp</button>
          </div>
        </div>
      </section>

      <section style={panelStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div>
            <h3 style={{ margin: 0 }}>Teste real imediato por e-mail SMTP</h3>
            <p style={{ margin: "6px 0 0", color: "#667085", lineHeight: 1.55 }}>
              Use esta área para fazer um envio real sem alterar o .env. O teste ignora o dry-run apenas nesta chamada e não salva a senha informada.
            </p>
          </div>
          <span style={{ ...badgeStyle, background: "#ecfdf3", color: "#027a48" }}>Teste real avulso</span>
        </div>
        <div style={formGridStyle}>
          <input placeholder="SMTP Host. Ex: smtp.gmail.com" value={realEmailForm.smtp_host} onChange={(e) => setRealEmailForm({ ...realEmailForm, smtp_host: e.target.value })} style={inputStyle} />
          <input placeholder="Porta" value={realEmailForm.smtp_port} onChange={(e) => setRealEmailForm({ ...realEmailForm, smtp_port: e.target.value })} style={inputStyle} />
          <input placeholder="Usuário SMTP" value={realEmailForm.smtp_user} onChange={(e) => setRealEmailForm({ ...realEmailForm, smtp_user: e.target.value })} style={inputStyle} />
          <input placeholder="Senha SMTP / senha de app" type="password" value={realEmailForm.smtp_password} onChange={(e) => setRealEmailForm({ ...realEmailForm, smtp_password: e.target.value })} style={inputStyle} />
          <input placeholder="Remetente" value={realEmailForm.smtp_from} onChange={(e) => setRealEmailForm({ ...realEmailForm, smtp_from: e.target.value })} style={inputStyle} />
          <input placeholder="Destinatário" value={realEmailForm.to} onChange={(e) => setRealEmailForm({ ...realEmailForm, to: e.target.value })} style={inputStyle} />
          <input placeholder="Assunto" value={realEmailForm.subject} onChange={(e) => setRealEmailForm({ ...realEmailForm, subject: e.target.value })} style={inputStyle} />
          <label style={{ ...smallCardStyle, display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
            <input type="checkbox" checked={realEmailForm.smtp_use_tls} onChange={(e) => setRealEmailForm({ ...realEmailForm, smtp_use_tls: e.target.checked })} />
            Usar TLS/STARTTLS
          </label>
        </div>
        <textarea
          placeholder="Mensagem do teste real"
          value={realEmailForm.message}
          onChange={(e) => setRealEmailForm({ ...realEmailForm, message: e.target.value })}
          style={{ ...inputStyle, minHeight: 82, resize: "vertical", marginBottom: 12 }}
        />
        <button style={primaryButtonStyle} onClick={testRealEmail}>Enviar e-mail real agora</button>
        <p style={{ margin: "10px 0 0", color: "#667085", fontSize: 12 }}>
          Para Gmail/Google Workspace, use senha de app. Para domínio próprio, informe o SMTP do provedor. SMS e WhatsApp agora também podem ser homologados nos blocos abaixo.
        </p>
      </section>

      <section style={panelStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 18, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div>
            <h3 style={{ margin: 0 }}>E-mail real automático por regras</h3>
            <p style={{ margin: "6px 0 0", color: "#667085", lineHeight: 1.55 }}>
              Salve o SMTP validado para este projeto. A partir disso, as regras automáticas com canal e-mail usam envio real, mesmo que o dry-run global continue ativo para SMS/WhatsApp.
            </p>
            <p style={{ margin: "6px 0 0", color: "#98a2b3", fontSize: 12 }}>
              Status: {data?.provider_profiles?.automatic_email_ready ? "SMTP automático ativo" : "SMTP automático não configurado"}
              {data?.provider_profiles?.email?.config?.smtp_host ? ` · Host: ${data.provider_profiles.email.config.smtp_host}` : ""}
              {data?.provider_profiles?.email?.config?.smtp_from ? ` · Remetente: ${data.provider_profiles.email.config.smtp_from}` : ""}
            </p>
          </div>
          <span style={{ ...badgeStyle, background: data?.provider_profiles?.automatic_email_ready ? "#ecfdf3" : "#fff7ed", color: data?.provider_profiles?.automatic_email_ready ? "#027a48" : "#9a3412" }}>
            {data?.provider_profiles?.automatic_email_ready ? "Ativo" : "Pendente"}
          </span>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 14 }}>
          <button style={primaryButtonStyle} onClick={saveAutomaticSmtp}>Salvar SMTP para alertas automáticos</button>
          <button style={secondaryButtonStyle} onClick={testAutomaticEmail}>Testar e-mail automático</button>
          <button style={secondaryButtonStyle} onClick={disableAutomaticSmtp}>Desativar SMTP automático</button>
          <button style={secondaryButtonStyle} onClick={evaluateNow}>Avaliar regras e enviar agora</button>
        </div>
        <p style={{ margin: "10px 0 0", color: "#667085", fontSize: 12 }}>
          Para produção em servidor público, prefira configurar credenciais por .env/secret manager. Esta opção salva o SMTP no banco local para permitir homologação operacional imediata.
        </p>
      </section>

      <section style={twoColumnsStyle}>
        <div style={panelStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
            <div>
              <h3 style={{ margin: 0 }}>SMS real por projeto</h3>
              <p style={{ margin: "6px 0 0", color: "#667085", lineHeight: 1.55 }}>
                Configure webhook, Twilio, Zenvia ou TotalVoice. O perfil salvo permite envio real automático por regra, mesmo com dry-run global ativo para os demais canais.
              </p>
              <p style={{ margin: "6px 0 0", color: "#98a2b3", fontSize: 12 }}>
                Status: {data?.provider_profiles?.automatic_sms_ready ? "SMS automático ativo" : "SMS automático não configurado"}
                {data?.provider_profiles?.sms?.provider_name ? ` · Provider: ${data.provider_profiles.sms.provider_name}` : ""}
              </p>
            </div>
            <span style={{ ...badgeStyle, background: data?.provider_profiles?.automatic_sms_ready ? "#ecfdf3" : "#fff7ed", color: data?.provider_profiles?.automatic_sms_ready ? "#027a48" : "#9a3412" }}>
              {data?.provider_profiles?.automatic_sms_ready ? "Ativo" : "Pendente"}
            </span>
          </div>
          <div style={formGridStyle}>
            <select value={smsForm.provider} onChange={(e) => setSmsForm({ ...smsForm, provider: e.target.value })} style={selectStyle}>
              <option value="webhook">Webhook genérico</option>
              <option value="twilio">Twilio</option>
              <option value="zenvia">Zenvia</option>
              <option value="totalvoice">TotalVoice</option>
            </select>
            <input placeholder="Destinatário de teste SMS" value={smsForm.to} onChange={(e) => setSmsForm({ ...smsForm, to: e.target.value })} style={inputStyle} />
            <input placeholder="Webhook URL" value={smsForm.webhook_url} onChange={(e) => setSmsForm({ ...smsForm, webhook_url: e.target.value })} style={inputStyle} />
            <input placeholder="Twilio Account SID" value={smsForm.account_sid} onChange={(e) => setSmsForm({ ...smsForm, account_sid: e.target.value })} style={inputStyle} />
            <input placeholder="Twilio Auth Token" type="password" value={smsForm.auth_token} onChange={(e) => setSmsForm({ ...smsForm, auth_token: e.target.value })} style={inputStyle} />
            <input placeholder="Número remetente Twilio" value={smsForm.from_number} onChange={(e) => setSmsForm({ ...smsForm, from_number: e.target.value })} style={inputStyle} />
            <input placeholder="Zenvia API Token" type="password" value={smsForm.api_token} onChange={(e) => setSmsForm({ ...smsForm, api_token: e.target.value })} style={inputStyle} />
            <input placeholder="Zenvia remetente / TotalVoice token" value={smsForm.from_name} onChange={(e) => setSmsForm({ ...smsForm, from_name: e.target.value })} style={inputStyle} />
            <input placeholder="TotalVoice Access Token" type="password" value={smsForm.access_token} onChange={(e) => setSmsForm({ ...smsForm, access_token: e.target.value })} style={inputStyle} />
            <input placeholder="Título do teste" value={smsForm.title} onChange={(e) => setSmsForm({ ...smsForm, title: e.target.value })} style={inputStyle} />
          </div>
          <textarea value={smsForm.message} onChange={(e) => setSmsForm({ ...smsForm, message: e.target.value })} style={{ ...inputStyle, minHeight: 72, resize: "vertical", marginBottom: 12 }} />
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button style={primaryButtonStyle} onClick={testRealSms}>Enviar SMS real agora</button>
            <button style={secondaryButtonStyle} onClick={saveSmsProvider}>Salvar SMS automático</button>
            <button style={secondaryButtonStyle} onClick={testAutomaticSms}>Testar SMS automático</button>
            <button style={secondaryButtonStyle} onClick={disableSmsProvider}>Desativar SMS</button>
          </div>
        </div>

        <div style={panelStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
            <div>
              <h3 style={{ margin: 0 }}>WhatsApp real por projeto</h3>
              <p style={{ margin: "6px 0 0", color: "#667085", lineHeight: 1.55 }}>
                Configure webhook, Zenvia ou Meta WhatsApp Cloud API. Use API oficial/provedor homologado para evitar bloqueio de número pessoal.
              </p>
              <p style={{ margin: "6px 0 0", color: "#98a2b3", fontSize: 12 }}>
                Status: {data?.provider_profiles?.automatic_whatsapp_ready ? "WhatsApp automático ativo" : "WhatsApp automático não configurado"}
                {data?.provider_profiles?.whatsapp?.provider_name ? ` · Provider: ${data.provider_profiles.whatsapp.provider_name}` : ""}
              </p>
            </div>
            <span style={{ ...badgeStyle, background: data?.provider_profiles?.automatic_whatsapp_ready ? "#ecfdf3" : "#fff7ed", color: data?.provider_profiles?.automatic_whatsapp_ready ? "#027a48" : "#9a3412" }}>
              {data?.provider_profiles?.automatic_whatsapp_ready ? "Ativo" : "Pendente"}
            </span>
          </div>
          <div style={formGridStyle}>
            <select value={whatsappForm.provider} onChange={(e) => setWhatsappForm({ ...whatsappForm, provider: e.target.value })} style={selectStyle}>
              <option value="webhook">Webhook genérico</option>
              <option value="zenvia">Zenvia</option>
              <option value="meta">Meta WhatsApp Cloud API</option>
            </select>
            <input placeholder="Destinatário de teste WhatsApp" value={whatsappForm.to} onChange={(e) => setWhatsappForm({ ...whatsappForm, to: e.target.value })} style={inputStyle} />
            <input placeholder="Webhook URL" value={whatsappForm.webhook_url} onChange={(e) => setWhatsappForm({ ...whatsappForm, webhook_url: e.target.value })} style={inputStyle} />
            <input placeholder="Zenvia API Token" type="password" value={whatsappForm.api_token} onChange={(e) => setWhatsappForm({ ...whatsappForm, api_token: e.target.value })} style={inputStyle} />
            <input placeholder="Número remetente Zenvia" value={whatsappForm.from_number} onChange={(e) => setWhatsappForm({ ...whatsappForm, from_number: e.target.value })} style={inputStyle} />
            <input placeholder="Meta Access Token" type="password" value={whatsappForm.access_token} onChange={(e) => setWhatsappForm({ ...whatsappForm, access_token: e.target.value })} style={inputStyle} />
            <input placeholder="Meta Phone Number ID" value={whatsappForm.phone_number_id} onChange={(e) => setWhatsappForm({ ...whatsappForm, phone_number_id: e.target.value })} style={inputStyle} />
            <input placeholder="Título do teste" value={whatsappForm.title} onChange={(e) => setWhatsappForm({ ...whatsappForm, title: e.target.value })} style={inputStyle} />
          </div>
          <textarea value={whatsappForm.message} onChange={(e) => setWhatsappForm({ ...whatsappForm, message: e.target.value })} style={{ ...inputStyle, minHeight: 72, resize: "vertical", marginBottom: 12 }} />
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button style={primaryButtonStyle} onClick={testRealWhatsapp}>Enviar WhatsApp real agora</button>
            <button style={secondaryButtonStyle} onClick={saveWhatsappProvider}>Salvar WhatsApp automático</button>
            <button style={secondaryButtonStyle} onClick={testAutomaticWhatsapp}>Testar WhatsApp automático</button>
            <button style={secondaryButtonStyle} onClick={disableWhatsappProvider}>Desativar WhatsApp</button>
          </div>
        </div>
      </section>

      <section style={twoColumnsStyle}>
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Contatos cadastrados</h3>
          <div style={{ display: "grid", gap: 10 }}>
            {(data?.contacts || []).map((c) => (
              <div key={c.id} style={smallCardStyle}>
                <strong>{c.name}</strong> <span style={mutedStyle}>{c.active ? "Ativo" : "Inativo"}</span>
                <div style={mutedStyle}>{c.role || "Sem função"} · {joinList(c.channels)}</div>
                <div style={mutedStyle}>{c.email || "sem e-mail"} · SMS: {c.phone || "—"} · WhatsApp: {c.whatsapp || "—"}</div>
                {c.active ? <button style={miniButtonStyle} onClick={() => deactivateContact(c.id)}>Desativar</button> : null}
              </div>
            ))}
            {!data?.contacts?.length ? <div style={emptyStyle}>Nenhum contato cadastrado.</div> : null}
          </div>
        </div>

        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Regras ativas</h3>
          <div style={{ display: "grid", gap: 10 }}>
            {(data?.rules || []).map((r) => (
              <div key={r.id} style={smallCardStyle}>
                <strong>{r.name}</strong> <span style={mutedStyle}>{r.active ? "Ativa" : "Inativa"}</span>
                <div style={mutedStyle}>Evento: {r.event_type} · Severidade: {r.severity_min} · Canais: {joinList(r.channels)}</div>
                <div style={mutedStyle}>Termos: {joinList(r.terms) || "sem restrição"} · Cooldown: {r.cooldown_minutes}min</div>
                <div style={mutedStyle}>Último acionamento: {fmtDate(r.last_triggered_at)}</div>
                {r.active ? <button style={miniButtonStyle} onClick={() => deactivateRule(r.id)}>Desativar</button> : null}
              </div>
            ))}
            {!data?.rules?.length ? <div style={emptyStyle}>Nenhuma regra cadastrada.</div> : null}
          </div>
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>Últimas notificações</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead><tr><th>Data</th><th>Canal</th><th>Status</th><th>Severidade</th><th>Título</th><th>Resposta</th></tr></thead>
            <tbody>
              {(data?.logs || []).map((log) => (
                <tr key={log.id}>
                  <td>{logDate(log)}</td>
                  <td>{channelLabel(log.channel)}</td>
                  <td>{statusLabel(log.status)}</td>
                  <td>{log.severity || "—"}</td>
                  <td>{log.title || "—"}</td>
                  <td>{log.provider_response || "—"}</td>
                </tr>
              ))}
              {!data?.logs?.length ? <tr><td colSpan={6}>Nenhum log de notificação.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}

function Kpi({ label, value, hint }: { label: string; value: React.ReactNode; hint: string }) {
  return <div style={kpiStyle}><div style={kpiLabelStyle}>{label}</div><div style={kpiValueStyle}>{value}</div><div style={kpiHintStyle}>{hint}</div></div>;
}

function ProviderCard({ name, info }: { name: string; info?: any }) {
  const enabled = Boolean(info?.enabled);
  const ready = Boolean(info?.ready);
  const missing = Array.isArray(info?.missing) ? info.missing : [];
  return (
    <div style={smallCardStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
        <strong>{name}</strong>
        <span style={{ ...badgeStyle, background: enabled && ready ? "#ecfdf3" : enabled ? "#fff7ed" : "#f2f4f7", color: enabled && ready ? "#027a48" : enabled ? "#9a3412" : "#667085" }}>
          {enabled && ready ? "Pronto" : enabled ? "Incompleto" : "Desativado"}
        </span>
      </div>
      <div style={mutedStyle}>Provider: {info?.provider || "—"}</div>
      {enabled && missing.length ? <div style={{ ...mutedStyle, color: "#b42318" }}>Faltam: {missing.join(", ")}</div> : null}
      {!enabled ? <div style={mutedStyle}>Ative no .env para envio real.</div> : null}
    </div>
  );
}

const heroStyle: React.CSSProperties = { background: "linear-gradient(135deg,#071629,#123b63)", color: "#fff", borderRadius: 22, padding: 26, display: "flex", justifyContent: "space-between", gap: 24, alignItems: "center", marginBottom: 20, boxShadow: "0 16px 30px rgba(15,23,42,.18)" };
const eyebrowStyle: React.CSSProperties = { color: "#f43f5e", fontSize: 12, fontWeight: 900, letterSpacing: 1.5 };
const inputStyle: React.CSSProperties = { width: "100%", boxSizing: "border-box", borderRadius: 12, border: "1px solid #d0d5dd", background: "#fff", color: "#111827", WebkitTextFillColor: "#111827", colorScheme: "light", padding: "12px 13px", fontSize: 14, outline: "none" };
const selectStyle: React.CSSProperties = { ...inputStyle, minWidth: 180 };
const primaryButtonStyle: React.CSSProperties = { background: "#b00020", color: "#fff", border: 0, borderRadius: 12, padding: "12px 16px", fontWeight: 900, cursor: "pointer" };
const secondaryButtonStyle: React.CSSProperties = { background: "#fff", color: "#123b63", border: "1px solid #d0d5dd", borderRadius: 12, padding: "12px 16px", fontWeight: 900, cursor: "pointer" };
const miniButtonStyle: React.CSSProperties = { marginTop: 8, background: "#f8fafc", color: "#b00020", border: "1px solid #e5e7eb", borderRadius: 8, padding: "6px 10px", fontWeight: 800, cursor: "pointer" };
const messageStyle: React.CSSProperties = { background: "#fff7ed", color: "#9a3412", border: "1px solid #fed7aa", padding: 14, borderRadius: 14, marginBottom: 18, fontWeight: 800 };
const kpiGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(4, minmax(0,1fr))", gap: 14, marginBottom: 20 };
const kpiStyle: React.CSSProperties = { background: "#fff", borderRadius: 18, padding: 18, boxShadow: "0 8px 18px rgba(15,23,42,.08)", borderTop: "5px solid #b00020" };
const kpiLabelStyle: React.CSSProperties = { color: "#667085", fontSize: 12, fontWeight: 900, textTransform: "uppercase", letterSpacing: .4 };
const kpiValueStyle: React.CSSProperties = { color: "#101828", fontSize: 26, fontWeight: 950, marginTop: 6 };
const kpiHintStyle: React.CSSProperties = { color: "#667085", fontSize: 12, marginTop: 4 };
const panelStyle: React.CSSProperties = { background: "#fff", borderRadius: 20, padding: 20, boxShadow: "0 8px 20px rgba(15,23,42,.08)", marginBottom: 20 };
const twoColumnsStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 20 };
const formGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 10, marginBottom: 12 };
const smallCardStyle: React.CSSProperties = { border: "1px solid #e5e7eb", borderRadius: 14, padding: 14, background: "#f8fafc" };
const mutedStyle: React.CSSProperties = { color: "#667085", fontSize: 13, marginTop: 4 };
const emptyStyle: React.CSSProperties = { background: "#f8fafc", borderRadius: 12, padding: 16, color: "#667085" };
const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: 13 };
const providerGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(4,minmax(0,1fr))", gap: 12, marginTop: 16 };
const badgeStyle: React.CSSProperties = { display: "inline-flex", alignItems: "center", borderRadius: 999, padding: "6px 10px", fontSize: 12, fontWeight: 900 };
