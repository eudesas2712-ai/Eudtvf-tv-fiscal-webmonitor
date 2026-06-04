"use client";

import React, { useEffect, useMemo, useState } from "react";
import AppShell from "../../../components/AppShell";
import { adminJson, adminFetch, API_BASE, ADMIN_TOKEN_KEY, DEFAULT_ADMIN_TOKEN } from "../../../lib/apiClient";

const API = API_BASE;

type BackupItem = { filename: string; size_bytes: number; created_at: string; path?: string };
type Status = {
  generated_at?: string;
  backup_dir?: string;
  backup_count?: number;
  latest_backup?: BackupItem | null;
  backup_freshness?: { status?: string; message?: string; age_hours?: number; warning_hours?: number; error_hours?: number };
  auto_backup?: { enabled?: boolean; interval_hours?: number; include_minio?: boolean };
  notification_errors?: { active_errors_24h?: number; archived_errors_24h?: number };
  retention_days?: number;
  pg_dump_available?: boolean;
  minio_bucket?: string;
  disk?: { total: number; used: number; free: number };
  table_counts?: Record<string, number>;
};

type AutoBackup = {
  enabled?: boolean;
  interval_hours?: number;
  check_every_minutes?: number;
  include_minio?: boolean;
  backup_dir?: string;
  latest_backup_age_hours?: number | null;
  latest_backup?: BackupItem | null;
};

function formatBytes(value?: number) {
  const n = Number(value || 0);
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function formatDate(value?: string) {
  if (!value) return "—";
  try { return new Date(value).toLocaleString("pt-BR"); } catch { return value; }
}

function statusColor(status?: string) {
  if (status === "ok") return "#027A48";
  if (status === "warning") return "#B54708";
  if (status === "error") return "#B42318";
  return "#344054";
}

function statusBg(status?: string) {
  if (status === "ok") return "#ECFDF3";
  if (status === "warning") return "#FFFAEB";
  if (status === "error") return "#FEF3F2";
  return "#F2F4F7";
}

export default function MaintenancePage() {
  const [token, setToken] = useState(DEFAULT_ADMIN_TOKEN);
  const [status, setStatus] = useState<Status | null>(null);
  const [autoBackup, setAutoBackup] = useState<AutoBackup | null>(null);
  const [backups, setBackups] = useState<BackupItem[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [includeDatabase, setIncludeDatabase] = useState(true);
  const [includeMinio, setIncludeMinio] = useState(false);
  const [backupLabel, setBackupLabel] = useState("manual");
  const [cleanupDays, setCleanupDays] = useState("90");
  const [backupRetention, setBackupRetention] = useState("15");
  const [cleanupDryRun, setCleanupDryRun] = useState(true);
  const [cleanupResult, setCleanupResult] = useState<any>(null);
  const [archiveHours, setArchiveHours] = useState("24");
  const [archiveDryRun, setArchiveDryRun] = useState(true);
  const [archiveResult, setArchiveResult] = useState<any>(null);
  const [homologationHours, setHomologationHours] = useState("24");
  const [homologationDryRun, setHomologationDryRun] = useState(true);
  const [homologationResult, setHomologationResult] = useState<any>(null);

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
      const [st, list, auto] = await Promise.all([
        api("/maintenance/status"),
        api("/maintenance/backups"),
        api("/maintenance/auto-backup/status"),
      ]);
      setStatus(st);
      setBackups(list.items || []);
      setAutoBackup(auto);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao carregar manutenção.");
    } finally {
      setLoading(false);
    }
  }

  async function createBackup() {
    setLoading(true);
    setMessage("Gerando backup. Aguarde...");
    try {
      const payload = {
        include_database: includeDatabase,
        include_minio: includeMinio,
        include_manifest: true,
        minio_max_objects: 5000,
        label: backupLabel || "manual",
      };
      const result = await api("/maintenance/backup", { method: "POST", body: JSON.stringify(payload) });
      setMessage(`Backup gerado: ${result.filename} (${formatBytes(result.size_bytes)})${result.warnings?.length ? ` · Avisos: ${result.warnings.join(" | ")}` : ""}`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao gerar backup.");
    } finally {
      setLoading(false);
    }
  }

  async function runAutoBackupNow() {
    setLoading(true);
    setMessage("Executando backup automático agora...");
    try {
      const result = await api("/maintenance/auto-backup/run", { method: "POST" });
      setMessage(`Backup automático executado: ${result.filename} (${formatBytes(result.size_bytes)})`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao executar backup automático.");
    } finally {
      setLoading(false);
    }
  }

  async function runCleanup() {
    setLoading(true);
    setMessage(cleanupDryRun ? "Simulando limpeza..." : "Executando limpeza...");
    try {
      const result = await api("/maintenance/cleanup", {
        method: "POST",
        body: JSON.stringify({
          days: Number(cleanupDays || 90),
          dry_run: cleanupDryRun,
          cleanup_dry_run_notifications: true,
          cleanup_resolved_notifications: false,
          cleanup_automation_runs: true,
          cleanup_old_backups: true,
          backup_retention_days: Number(backupRetention || 15),
        }),
      });
      setCleanupResult(result);
      setMessage(cleanupDryRun ? "Simulação de limpeza concluída." : "Limpeza executada.");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao executar limpeza.");
    } finally {
      setLoading(false);
    }
  }

  async function runArchiveErrors() {
    setLoading(true);
    setMessage(archiveDryRun ? "Simulando arquivamento de erros..." : "Arquivando erros históricos...");
    try {
      const result = await api("/maintenance/archive-notification-errors", {
        method: "POST",
        body: JSON.stringify({
          hours: Number(archiveHours || 24),
          dry_run: archiveDryRun,
          archived_by: "admin",
          reason: "Saneamento operacional pela tela de manutenção V40",
        }),
      });
      setArchiveResult(result);
      setMessage(archiveDryRun ? "Simulação de arquivamento concluída." : "Erros históricos arquivados.");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao arquivar erros.");
    } finally {
      setLoading(false);
    }
  }


  async function runArchiveHomologationErrors() {
    setLoading(true);
    setMessage(homologationDryRun ? "Simulando arquivamento de erros de homologação..." : "Arquivando erros de homologação...");
    try {
      const result = await api("/maintenance/archive-homologation-errors", {
        method: "POST",
        body: JSON.stringify({
          hours: Number(homologationHours || 24),
          dry_run: homologationDryRun,
          archived_by: "admin",
          reason: "Arquivamento de erros de homologação pela tela de manutenção V40.1",
        }),
      });
      setHomologationResult(result);
      setMessage(homologationDryRun ? "Simulação de arquivamento de homologação concluída." : "Erros de homologação arquivados.");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao arquivar erros de homologação.");
    } finally {
      setLoading(false);
    }
  }

  async function deleteBackup(filename: string) {
    if (!confirm(`Excluir backup ${filename}?`)) return;
    setLoading(true);
    try {
      await adminFetch(`${API}/maintenance/backups/${encodeURIComponent(filename)}`, {
        method: "DELETE",
      }).then((res) => { if (!res.ok) throw new Error(`Erro HTTP ${res.status}`); });
      setMessage(`Backup excluído: ${filename}`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao excluir backup.");
    } finally {
      setLoading(false);
    }
  }

  function backupDownloadUrl(filename: string) {
    return `${API}/maintenance/backups/${encodeURIComponent(filename)}?admin_token=${encodeURIComponent(token)}`;
  }

  function securityExportUrl() {
    return `${API}/maintenance/security-export.csv?admin_token=${encodeURIComponent(token)}`;
  }

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  const diskUsedPct = useMemo(() => {
    if (!status?.disk?.total) return 0;
    return Math.round((status.disk.used / status.disk.total) * 100);
  }, [status]);

  return (
    <AppShell
      title="Manutenção e Backup"
      subtitle="Rotina de produção: backup persistente, retenção automática, saneamento de logs e exportação de segurança."
    >
      <section style={heroStyle}>
        <div>
          <div style={eyebrowStyle}>PRODUCTION OPS · TV FISCAL WEBMONITOR</div>
          <h2 style={{ margin: "8px 0 10px", fontSize: 32 }}>Backup, retenção e saneamento operacional</h2>
          <p style={{ margin: 0, maxWidth: 900, lineHeight: 1.65 }}>
            Gere pacotes de backup, mantenha a rotina protegida em volume persistente, acompanhe validade do último backup e arquive erros históricos sem perder rastreabilidade.
          </p>
        </div>
        <div style={{ display: "grid", gap: 10, minWidth: 360 }}>
          <input value={token} onChange={(e) => setToken(e.target.value)} type="password" style={inputStyle} />
          <button onClick={load} style={primaryButtonStyle}>{loading ? "Atualizando..." : "Atualizar status"}</button>
          <a href={securityExportUrl()} target="_blank" rel="noreferrer" style={secondaryLinkStyle}>Exportar segurança CSV</a>
        </div>
      </section>

      {message ? <div style={messageStyle}>{message}</div> : null}

      <section style={kpiGridStyle}>
        <Kpi label="Backups" value={status?.backup_count || 0} hint="pacotes salvos" />
        <Kpi label="Validade backup" value={status?.backup_freshness?.status === "ok" ? "OK" : "Atenção"} hint={status?.backup_freshness?.age_hours == null ? "sem backup" : `${status.backup_freshness.age_hours}h`} danger={status?.backup_freshness?.status !== "ok"} />
        <Kpi label="Auto backup" value={autoBackup?.enabled ? "Ativo" : "Off"} hint={`${autoBackup?.interval_hours || 24}h`} danger={!autoBackup?.enabled} />
        <Kpi label="Disco usado" value={`${diskUsedPct}%`} hint={`${formatBytes(status?.disk?.free)} livres`} danger={diskUsedPct >= 85} />
        <Kpi label="Erros ativos" value={status?.notification_errors?.active_errors_24h || 0} hint="notificações 24h" danger={(status?.notification_errors?.active_errors_24h || 0) > 0} />
        <Kpi label="Logs" value={status?.table_counts?.notification_logs || 0} hint="notificações" />
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginBottom: 18 }}>
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Gerar pacote de backup</h3>
          <p style={mutedStyle}>Recomendado: banco de dados sempre ativo. Evidências MinIO podem gerar pacote maior; use quando precisar de cópia completa documental.</p>
          <div style={formGridStyle}>
            <label style={checkStyle}><input type="checkbox" checked={includeDatabase} onChange={(e) => setIncludeDatabase(e.target.checked)} /> PostgreSQL</label>
            <label style={checkStyle}><input type="checkbox" checked={includeMinio} onChange={(e) => setIncludeMinio(e.target.checked)} /> Evidências MinIO</label>
            <input value={backupLabel} onChange={(e) => setBackupLabel(e.target.value)} placeholder="Rótulo do backup" style={inputStyle} />
            <button onClick={createBackup} style={primaryButtonStyle}>Gerar pacote de backup</button>
          </div>
          <div style={infoBoxStyle}>
            <strong>Diretório:</strong> {status?.backup_dir || "—"}<br />
            <strong>Último backup:</strong> {status?.latest_backup ? `${status.latest_backup.filename} · ${formatDate(status.latest_backup.created_at)}` : "Nenhum"}<br />
            <strong>Status:</strong> <span style={{ color: statusColor(status?.backup_freshness?.status), fontWeight: 900 }}>{status?.backup_freshness?.message || "—"}</span>
          </div>
        </div>

        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Backup automático e persistência</h3>
          <p style={mutedStyle}>O agendador interno pode gerar backup diário. Para persistência após rebuild, monte um volume/host path em <strong>BACKUP_DIR</strong>.</p>
          <div style={infoBoxStyle}>
            <strong>Status:</strong> {autoBackup?.enabled ? "Ativo" : "Desativado"}<br />
            <strong>Intervalo:</strong> {autoBackup?.interval_hours || 24}h<br />
            <strong>Diretório:</strong> {autoBackup?.backup_dir || status?.backup_dir || "—"}<br />
            <strong>MinIO no automático:</strong> {autoBackup?.include_minio ? "Sim" : "Não"}
          </div>
          <button onClick={runAutoBackupNow} style={secondaryButtonStyle}>Executar backup automático agora</button>
          <pre style={preStyle}>{`Env recomendado:\nBACKUP_DIR=/app/backups\nAUTO_BACKUP_ENABLED=true\nAUTO_BACKUP_INTERVAL_HOURS=24\nAUTO_BACKUP_INCLUDE_MINIO=false\nBACKUP_WARNING_HOURS=24\nBACKUP_ERROR_HOURS=168`}</pre>
        </div>
      </section>

      <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginBottom: 18 }}>
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Limpeza de logs e retenção</h3>
          <p style={mutedStyle}>Execute primeiro em modo simulação. A limpeza remove logs simulados antigos e execuções antigas de automação; alertas resolvidos não são removidos por padrão.</p>
          <div style={formGridStyle}>
            <input value={cleanupDays} onChange={(e) => setCleanupDays(e.target.value)} placeholder="Dias para logs" style={inputStyle} />
            <input value={backupRetention} onChange={(e) => setBackupRetention(e.target.value)} placeholder="Retenção backups" style={inputStyle} />
            <label style={checkStyle}><input type="checkbox" checked={cleanupDryRun} onChange={(e) => setCleanupDryRun(e.target.checked)} /> Simular antes de apagar</label>
            <button onClick={runCleanup} style={cleanupDryRun ? secondaryButtonStyle : dangerButtonStyle}>{cleanupDryRun ? "Simular limpeza" : "Executar limpeza real"}</button>
          </div>
          {cleanupResult ? <pre style={preStyle}>{JSON.stringify(cleanupResult, null, 2)}</pre> : null}
        </div>

        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>Saneamento de erros de notificação</h3>
          <p style={mutedStyle}>Arquiva erros históricos de teste/timeout sem apagar registros. O healthcheck passa a considerar apenas erros ativos não arquivados.</p>
          <div style={formGridStyle}>
            <input value={archiveHours} onChange={(e) => setArchiveHours(e.target.value)} placeholder="Arquivar erros mais antigos que X horas" style={inputStyle} />
            <label style={checkStyle}><input type="checkbox" checked={archiveDryRun} onChange={(e) => setArchiveDryRun(e.target.checked)} /> Simular antes de arquivar</label>
            <button onClick={runArchiveErrors} style={archiveDryRun ? secondaryButtonStyle : dangerButtonStyle}>{archiveDryRun ? "Simular arquivamento" : "Arquivar erros históricos"}</button>
          </div>
          <div style={infoBoxStyle}>
            <strong>Erros ativos 24h:</strong> {status?.notification_errors?.active_errors_24h || 0}<br />
            <strong>Erros arquivados 24h:</strong> {status?.notification_errors?.archived_errors_24h || 0}
          </div>
          {archiveResult ? <pre style={preStyle}>{JSON.stringify(archiveResult, null, 2)}</pre> : null}
        </div>
      </section>

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>Arquivamento de erros de homologação/teste</h3>
        <p style={mutedStyle}>Use esta rotina para limpar da Saúde do Sistema erros recentes de testes SMTP/SMS/WhatsApp, timeouts e tentativas sem credenciais. O histórico não é apagado: os registros apenas são marcados como arquivados.</p>
        <div style={{ display: "grid", gridTemplateColumns: "220px 1fr 220px", gap: 12, alignItems: "center" }}>
          <input value={homologationHours} onChange={(e) => setHomologationHours(e.target.value)} placeholder="Últimas X horas" style={inputStyle} />
          <label style={checkStyle}><input type="checkbox" checked={homologationDryRun} onChange={(e) => setHomologationDryRun(e.target.checked)} /> Simular antes de arquivar</label>
          <button onClick={runArchiveHomologationErrors} style={homologationDryRun ? secondaryButtonStyle : dangerButtonStyle}>{homologationDryRun ? "Simular homologação" : "Arquivar homologação"}</button>
        </div>
        <div style={infoBoxStyle}>
          <strong>O que será considerado:</strong> registros com status erro, recentes, ainda não arquivados, contendo indicação de teste/homologação, SMTP, timeout, credencial/token, dry-run ou conexão fechada.
        </div>
        {homologationResult ? <pre style={preStyle}>{JSON.stringify(homologationResult, null, 2)}</pre> : null}
      </section>

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>Backups disponíveis</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead><tr><th>Arquivo</th><th>Data</th><th>Tamanho</th><th>Ações</th></tr></thead>
            <tbody>
              {backups.map((b) => (
                <tr key={b.filename}>
                  <td>{b.filename}</td>
                  <td>{formatDate(b.created_at)}</td>
                  <td>{formatBytes(b.size_bytes)}</td>
                  <td>
                    <a href={backupDownloadUrl(b.filename)} target="_blank" rel="noreferrer" style={smallLinkStyle}>Baixar</a>
                    <button onClick={() => deleteBackup(b.filename)} style={smallDangerButtonStyle}>Excluir</button>
                  </td>
                </tr>
              ))}
              {!backups.length ? <tr><td colSpan={4}>Nenhum backup encontrado.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}

function Kpi({ label, value, hint, danger }: { label: string; value: number | string; hint: string; danger?: boolean }) {
  return (
    <div style={kpiStyle}>
      <div style={{ color: danger ? "#b42318" : "#b00020", fontSize: 28, fontWeight: 900 }}>{value}</div>
      <div style={{ fontWeight: 800, color: "#0b1f3a" }}>{label}</div>
      <div style={{ color: "#667085", fontSize: 12 }}>{hint}</div>
    </div>
  );
}

const heroStyle: React.CSSProperties = { background: "linear-gradient(135deg,#071a33 0%,#0b2a4a 62%,#b00020 100%)", color: "#fff", borderRadius: 22, padding: 26, marginBottom: 18, display: "flex", justifyContent: "space-between", gap: 24, alignItems: "center", boxShadow: "0 14px 32px rgba(7,26,51,.22)" };
const eyebrowStyle: React.CSSProperties = { letterSpacing: 2.4, fontSize: 11, fontWeight: 900, opacity: .86 };
const inputStyle: React.CSSProperties = { padding: "11px 12px", borderRadius: 10, border: "1px solid #d0d5dd", fontSize: 14, width: "100%", boxSizing: "border-box" };
const primaryButtonStyle: React.CSSProperties = { background: "#b00020", color: "#fff", border: 0, borderRadius: 10, padding: "11px 14px", fontWeight: 900, cursor: "pointer" };
const secondaryButtonStyle: React.CSSProperties = { background: "#0b2a4a", color: "#fff", border: 0, borderRadius: 10, padding: "11px 14px", fontWeight: 900, cursor: "pointer" };
const dangerButtonStyle: React.CSSProperties = { background: "#b42318", color: "#fff", border: 0, borderRadius: 10, padding: "11px 14px", fontWeight: 900, cursor: "pointer" };
const secondaryLinkStyle: React.CSSProperties = { background: "rgba(255,255,255,.16)", color: "#fff", border: "1px solid rgba(255,255,255,.32)", textDecoration: "none", borderRadius: 10, padding: "11px 14px", fontWeight: 900, textAlign: "center" };
const messageStyle: React.CSSProperties = { background: "#fff7e6", border: "1px solid #ffd591", color: "#7a4b00", borderRadius: 12, padding: 14, marginBottom: 18 };
const kpiGridStyle: React.CSSProperties = { display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 14, marginBottom: 18 };
const kpiStyle: React.CSSProperties = { background: "#fff", borderRadius: 16, padding: 18, boxShadow: "0 8px 22px rgba(15,23,42,.08)", border: "1px solid #edf0f5" };
const panelStyle: React.CSSProperties = { background: "#fff", borderRadius: 18, padding: 20, boxShadow: "0 8px 24px rgba(15,23,42,.08)", border: "1px solid #edf0f5" };
const mutedStyle: React.CSSProperties = { color: "#667085", lineHeight: 1.55, marginTop: 0 };
const formGridStyle: React.CSSProperties = { display: "grid", gap: 10 };
const checkStyle: React.CSSProperties = { display: "flex", gap: 8, alignItems: "center", fontWeight: 700, color: "#344054" };
const infoBoxStyle: React.CSSProperties = { marginTop: 14, padding: 12, borderRadius: 12, background: "#f8fafc", color: "#344054", lineHeight: 1.6 };
const preStyle: React.CSSProperties = { marginTop: 12, padding: 12, borderRadius: 12, background: "#101828", color: "#e6f4ff", overflowX: "auto", fontSize: 12, maxHeight: 260 };
const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: 13 };
const smallLinkStyle: React.CSSProperties = { color: "#0b2a4a", fontWeight: 900, marginRight: 10 };
const smallDangerButtonStyle: React.CSSProperties = { background: "#fff1f0", color: "#b42318", border: "1px solid #ffccc7", borderRadius: 8, padding: "6px 10px", fontWeight: 800, cursor: "pointer" };
