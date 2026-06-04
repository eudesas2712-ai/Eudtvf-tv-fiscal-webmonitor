"use client";

import { useEffect, useState } from "react";
import AppShell from "../../../components/AppShell";
import { adminFetch, API_BASE, ADMIN_TOKEN_KEY } from "../../../lib/apiClient";

const API = API_BASE;
const DEFAULT_PROJECT_ID = "9b972aa2-f8a4-483b-a7d1-e979d86482fb";

function fmtDate(value: any) {
  if (!value) return "Não registrado";

  let normalizedValue = String(value);

  const looksLikeIsoWithoutTimezone =
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(normalizedValue) &&
    !normalizedValue.endsWith("Z") &&
    !normalizedValue.includes("+");

  if (looksLikeIsoWithoutTimezone) {
    normalizedValue = `${normalizedValue}Z`;
  }

  const d = new Date(normalizedValue);

  if (Number.isNaN(d.getTime())) {
    return String(value);
  }

  return d.toLocaleString("pt-BR");
}

function nextRunDate(lastCycleStartedAt: any, intervalSeconds: any) {
  if (!lastCycleStartedAt || !intervalSeconds) {
    return "Não estimada";
  }

  const lastDate = new Date(lastCycleStartedAt);

  if (Number.isNaN(lastDate.getTime())) {
    return "Não estimada";
  }

  const nextDate = new Date(
    lastDate.getTime() + Number(intervalSeconds) * 1000
  );

  return nextDate.toLocaleString("pt-BR");
}

function fmtInterval(seconds: number) {
  if (!seconds) return "Não configurado";

  if (seconds < 60) {
    return `${seconds} segundos`;
  }

  if (seconds < 3600) {
    return `${Math.round(seconds / 60)} minutos`;
  }

  return `${Math.round(seconds / 3600)} hora(s)`;
}

export default function SchedulerAdminPage() {
  const [status, setStatus] = useState<any>(null);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const [portalScanRunning, setPortalScanRunning] = useState(false);
  const [bootstrapPortalsRunning, setBootstrapPortalsRunning] = useState(false);
  const [portalScanResult, setPortalScanResult] = useState<any>(null);
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [historyStatus, setHistoryStatus] = useState("all");
  const [historyLimit, setHistoryLimit] = useState(50);

  const [adminToken, setAdminToken] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [authenticated, setAuthenticated] = useState(false);

  function getAuthHeaders(token = adminToken) {
    return {
      "X-Admin-Token": token,
    };
  }

  function logoutAdmin() {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    setAdminToken("");
    setTokenInput("");
    setAuthenticated(false);
    setStatus(null);
    setHistoryItems([]);
    setError("");
  }

  async function loginAdmin() {
    try {
      setError("");

      const cleanedToken = tokenInput.trim();

      if (!cleanedToken) {
        throw new Error("Informe o token administrativo.");
      }

      const res = await adminFetch(`${API}/admin/scheduler/status`, {
        headers: getAuthHeaders(cleanedToken),
      });

      if (!res.ok) {
        throw new Error("Token administrativo inválido.");
      }

      const json = await res.json();

      localStorage.setItem(ADMIN_TOKEN_KEY, cleanedToken);

      setAdminToken(cleanedToken);
      setTokenInput(cleanedToken);
      setAuthenticated(true);
      setStatus(json);

      await loadHistoryWithToken(cleanedToken);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erro desconhecido ao autenticar."
      );
    }
  }

  async function loadStatus() {
    try {
      setError("");

      const res = await adminFetch(`${API}/admin/scheduler/status`, {
        headers: getAuthHeaders(),
      });

      if (res.status === 401) {
        logoutAdmin();
        throw new Error("Sessão administrativa expirada ou token inválido.");
      }

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Erro HTTP ${res.status}: ${text}`);
      }

      const json = await res.json();
      setStatus(json);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erro desconhecido ao carregar status."
      );
    }
  }

  async function loadHistoryWithToken(token: string) {
    const params = new URLSearchParams();

    params.set("limit", String(historyLimit));

    if (historyStatus !== "all") {
      params.set("status", historyStatus);
    }

    const res = await adminFetch(
      `${API}/admin/scheduler/history?${params.toString()}`,
      {
        headers: getAuthHeaders(token),
      }
    );

    if (res.status === 401) {
      throw new Error("Sessão administrativa expirada ou token inválido.");
    }

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Erro HTTP ${res.status}: ${text}`);
    }

    const json = await res.json();
    setHistoryItems(Array.isArray(json.items) ? json.items : []);
  }

  async function loadHistory() {
    try {
      setError("");
      await loadHistoryWithToken(adminToken);
    } catch (err) {
      if (err instanceof Error && err.message.includes("token inválido")) {
        logoutAdmin();
      }

      setError(
        err instanceof Error
          ? err.message
          : "Erro desconhecido ao carregar histórico."
      );
    }
  }

  async function clearHistory() {
    const confirmClear = window.confirm(
      historyStatus === "all"
        ? "Deseja limpar todo o histórico de coletas?"
        : `Deseja limpar o histórico com status ${historyStatus}?`
    );

    if (!confirmClear) return;

    try {
      setError("");

      const params = new URLSearchParams();

      if (historyStatus !== "all") {
        params.set("status", historyStatus);
      }

      const query = params.toString();

      const url = query
        ? `${API}/admin/scheduler/history?${query}`
        : `${API}/admin/scheduler/history`;

      const res = await adminFetch(url, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });

      if (res.status === 401) {
        logoutAdmin();
        throw new Error("Sessão administrativa expirada ou token inválido.");
      }

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Erro HTTP ${res.status}: ${text}`);
      }

      await res.json();
      await loadStatus();
      await loadHistory();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erro desconhecido ao limpar histórico."
      );
    }
  }

  function downloadHistoryCsv() {
    const params = new URLSearchParams();

    params.set("limit", String(historyLimit));
    params.set("admin_token", adminToken);

    if (historyStatus !== "all") {
      params.set("status", historyStatus);
    }

    window.open(
      `${API}/admin/scheduler/history/export.csv?${params.toString()}`,
      "_blank"
    );
  }

  async function runNow() {
    try {
      setError("");
      setRunning(true);

      const res = await adminFetch(`${API}/admin/scheduler/run-now`, {
        method: "POST",
        headers: getAuthHeaders(),
      });

      if (res.status === 401) {
        logoutAdmin();
        throw new Error("Sessão administrativa expirada ou token inválido.");
      }

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Erro HTTP ${res.status}: ${text}`);
      }

      await res.json();
      await loadStatus();
      await loadHistory();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erro desconhecido ao executar coleta."
      );
    } finally {
      setRunning(false);
    }
  }


  async function bootstrapProjectPortals() {
    try {
      setError("");
      setBootstrapPortalsRunning(true);
      const projectId = (status?.project_ids || [])[0] || DEFAULT_PROJECT_ID;

      const res = await adminFetch(`${API}/registry/projects/${projectId}/bootstrap-portals`, {
        method: "POST",
        headers: getAuthHeaders(),
      });

      if (res.status === 401) {
        logoutAdmin();
        throw new Error("Sessão administrativa expirada ou token inválido.");
      }

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Erro HTTP ${res.status}: ${text}`);
      }

      await res.json();
      await loadStatus();
      await loadHistory();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erro desconhecido ao criar/vincular portais padrão."
      );
    } finally {
      setBootstrapPortalsRunning(false);
    }
  }


  async function runPortalScanNow() {
    try {
      setError("");
      setPortalScanRunning(true);
      setPortalScanResult(null);

      const res = await adminFetch(`${API}/admin/scheduler/run-portal-scan-now?save_rejected=true`, {
        method: "POST",
        headers: getAuthHeaders(),
      });

      if (res.status === 401) {
        logoutAdmin();
        throw new Error("Sessão administrativa expirada ou token inválido.");
      }

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Erro HTTP ${res.status}: ${text}`);
      }

      const json = await res.json();
      setPortalScanResult(json);
      await loadStatus();
      await loadHistory();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erro desconhecido ao executar varredura dos portais."
      );
    } finally {
      setPortalScanRunning(false);
    }
  }

  async function toggleScheduler() {
    try {
      setError("");

      const endpoint = status?.running ? "disable" : "enable";

      const res = await adminFetch(`${API}/admin/scheduler/${endpoint}`, {
        method: "POST",
        headers: getAuthHeaders(),
      });

      if (res.status === 401) {
        logoutAdmin();
        throw new Error("Sessão administrativa expirada ou token inválido.");
      }

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Erro HTTP ${res.status}: ${text}`);
      }

      await res.json();
      await loadStatus();
      await loadHistory();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erro desconhecido ao alterar status do scheduler."
      );
    }
  }

  useEffect(() => {
    const savedToken = localStorage.getItem(ADMIN_TOKEN_KEY);

    if (savedToken) {
      setAdminToken(savedToken);
      setTokenInput(savedToken);
      setAuthenticated(true);
    }
  }, []);

  useEffect(() => {
    if (!authenticated || !adminToken) return;

    loadStatus();
    loadHistory();

    const timer = setInterval(() => {
      loadStatus();
      loadHistory();
    }, 15000);

    return () => clearInterval(timer);
  }, [authenticated, adminToken, historyStatus, historyLimit]);

  if (!authenticated) {
    return (
      <main
        style={{
          padding: 30,
          fontFamily: "Arial",
          background: "#f5f6fa",
          minHeight: "100vh",
        }}
      >
        <section
          style={{
            maxWidth: 460,
            margin: "80px auto",
            background: "#fff",
            padding: 30,
            borderRadius: 12,
            boxShadow: "0 4px 14px rgba(0,0,0,0.08)",
            borderLeft: "5px solid #c52625",
          }}
        >
          <h1 style={{ marginTop: 0, color: "#b00020" }}>
            Acesso Administrativo
          </h1>

          <p style={{ color: "#666" }}>
            Informe o token administrativo para acessar o Scheduler.
          </p>

          <input
            type="password"
            value={tokenInput}
            onChange={(event) => setTokenInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                loginAdmin();
              }
            }}
            placeholder="Token administrativo"
            style={{
              width: "100%",
              padding: 12,
              borderRadius: 6,
              border: "1px solid #ccc",
              marginTop: 10,
              boxSizing: "border-box",
            }}
          />

          {error && <p style={{ color: "red", marginTop: 12 }}>{error}</p>}

          <button
            onClick={loginAdmin}
            style={{
              marginTop: 18,
              padding: "12px 22px",
              background: "#c52625",
              color: "#fff",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 15,
              width: "100%",
            }}
          >
            Entrar
          </button>
        </section>
      </main>
    );
  }

  if (error) {
    return (
      <main style={{ padding: 30, fontFamily: "Arial", color: "red" }}>
        <h1>Administração do Scheduler</h1>

        <p>{error}</p>

        <div style={{ display: "flex", gap: 12, marginTop: 20, flexWrap: "wrap" }}>
          <button onClick={loadStatus} style={buttonStyle("#c52625")}>
            Tentar novamente
          </button>

          <button onClick={loadHistory} style={buttonStyle("#555")}>
            Recarregar histórico
          </button>

          <button onClick={logoutAdmin} style={buttonStyle("#777")}>
            Sair
          </button>
        </div>
      </main>
    );
  }

  if (!status) {
    return (
      <main style={{ padding: 30, fontFamily: "Arial" }}>
        Carregando status do scheduler...
      </main>
    );
  }

  return (
    <main
      style={{
        padding: 30,
        fontFamily: "Arial",
        background: "#f5f6fa",
        minHeight: "100vh",
      }}
    >
      <h1 style={{ marginBottom: 0 }}>Administração do Scheduler</h1>

      <p style={{ color: "#666", marginTop: 5 }}>
        Monitoramento automático de snapshots do TV Fiscal WebMonitor
      </p>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 20,
          marginTop: 30,
        }}
      >
        <Card
          title="Status"
          value={status.running ? "Rodando" : "Parado"}
          highlight={status.running}
        />

        <Card
          title="Habilitado"
          value={status.enabled ? "Sim" : "Não"}
          highlight={status.enabled}
        />

        <Card title="Intervalo" value={fmtInterval(status.interval_seconds)} />

        <Card title="Coletas executadas" value={status.run_count ?? 0} />

        <Card title="Varreduras de portais" value={status.scan_count ?? 0} />
      </section>

      <Panel title="Última coleta">
        <Info
          label="Último projeto coletado"
          value={status.last_project_id || "—"}
        />

        <Info
          label="Última coleta com sucesso"
          value={fmtDate(status.last_success_at)}
        />

        <Info
          label="Último ciclo iniciado em"
          value={fmtDate(status.last_cycle_started_at)}
        />

        <Info
          label="Próxima coleta estimada"
          value={nextRunDate(
            status.last_cycle_started_at,
            status.interval_seconds
          )}
        />

        <Info
          label="Scheduler iniciado em"
          value={fmtDate(status.started_at)}
        />

        <Info
          label="Última varredura de portal"
          value={fmtDate(status.last_scan_at)}
        />

        <Info
          label="Último portal escaneado"
          value={status.last_portal_url || "—"}
        />
      </Panel>

      <Panel title="Configuração">
        <Info label="Base URL" value={status.base_url || "—"} />

        <Info
          label="Projetos monitorados"
          value={(status.project_ids || []).join(", ") || "Nenhum"}
        />

        <Info
          label="Origem dos projetos"
          value={status.use_registered_projects ? "Cadastros operacionais" : "Variável SNAPSHOT_PROJECT_IDS"}
        />

        <Info
          label="Varredura automática de portais"
          value={status.scan_registered_portals ? "Ativa" : "Inativa"}
        />

        <Info
          label="Portais cadastrados vinculados"
          value={status.configured_portal_count ?? 0}
        />
      </Panel>

      <Panel title="Projetos e portais cadastrados">
        <p style={{ color: "#666", marginTop: 0 }}>
          Estes são os projetos e portais que o scheduler passa a usar para varredura automática.
          Cadastre e vincule novos portais em <strong>/admin/cadastros</strong> ou use o botão abaixo para criar e vincular os portais padrão ao projeto ativo.
        </p>

        {(status.configured_portal_count ?? 0) === 0 && (
          <div style={{ background: "#fff7ed", border: "1px solid #fed7aa", color: "#9a3412", borderRadius: 10, padding: 12, marginBottom: 14 }}>
            Nenhum portal ativo vinculado ao projeto. Clique em <strong>Criar/vincular portais padrão</strong> e depois execute a varredura.
          </div>
        )}

        <button
          onClick={bootstrapProjectPortals}
          disabled={bootstrapPortalsRunning}
          style={buttonStyle(bootstrapPortalsRunning ? "#999" : "#0f766e", bootstrapPortalsRunning)}
        >
          {bootstrapPortalsRunning ? "Vinculando portais..." : "Criar/vincular portais padrão"}
        </button>

        {(!status.configured_projects || status.configured_projects.length === 0) && (
          <p style={{ color: "#b00020" }}>Nenhum projeto com portal ativo vinculado.</p>
        )}

        {(status.configured_projects || []).map((project: any) => (
          <div
            key={project.project_id}
            style={{
              border: "1px solid #eee",
              borderRadius: 10,
              padding: 14,
              marginBottom: 12,
              background: "#fafafa",
            }}
          >
            <strong>{project.project_name || project.project_id}</strong>
            <div style={{ color: "#777", fontSize: 12, marginTop: 4 }}>
              {project.project_id}
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
              {(project.portals || []).length === 0 && (
                <span style={{ color: "#b00020" }}>Sem portal ativo vinculado.</span>
              )}

              {(project.portals || []).map((portal: any) => (
                <span
                  key={portal.id}
                  style={{
                    background: "#fff",
                    border: "1px solid #ddd",
                    borderRadius: 999,
                    padding: "6px 10px",
                    fontSize: 12,
                  }}
                >
                  {portal.name} · {portal.base_url}
                </span>
              ))}
            </div>
          </div>
        ))}

        {status.last_scan_summary && (
          <div style={{ marginTop: 16, padding: 12, background: "#f8f9fa", borderRadius: 8 }}>
            <strong>Último resumo de varredura:</strong>{" "}
            {status.last_scan_summary.detected ?? 0} detectados · {status.last_scan_summary.auditables ?? 0} auditáveis · {status.last_scan_summary.inserted ?? 0} salvos · {status.last_scan_summary.news_candidates ?? 0} candidatos a notícia.
          </div>
        )}

        {portalScanResult?.totals && (
          <div style={{ marginTop: 16, padding: 12, background: "#eef8f0", borderRadius: 8 }}>
            <strong>Varredura manual concluída:</strong>{" "}
            {portalScanResult.totals.detected} detectados · {portalScanResult.totals.auditables} auditáveis · {portalScanResult.totals.inserted} salvos · {portalScanResult.totals.errors} erro(s).
          </div>
        )}
      </Panel>

      {status.last_error && (
        <Panel title="Último erro">
          <Info label="Data do erro" value={fmtDate(status.last_error_at)} />
          <Info label="Mensagem" value={status.last_error} />
        </Panel>
      )}

      <Panel title="Histórico de coletas">
        <div
          style={{
            display: "flex",
            gap: 12,
            marginBottom: 20,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <label>
            Status:{" "}
            <select
              value={historyStatus}
              onChange={(event) => setHistoryStatus(event.target.value)}
              style={{
                padding: 8,
                borderRadius: 6,
                border: "1px solid #ccc",
              }}
            >
              <option value="all">Todos</option>
              <option value="success">Sucesso</option>
              <option value="error">Erro</option>
            </select>
          </label>

          <label>
            Limite:{" "}
            <select
              value={historyLimit}
              onChange={(event) => setHistoryLimit(Number(event.target.value))}
              style={{
                padding: 8,
                borderRadius: 6,
                border: "1px solid #ccc",
              }}
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </label>

          <button onClick={loadHistory} style={smallButtonStyle("#555")}>
            Filtrar
          </button>

          <button onClick={clearHistory} style={smallButtonStyle("#c52625")}>
            Limpar histórico
          </button>

          <button onClick={downloadHistoryCsv} style={smallButtonStyle("#198754")}>
            Baixar histórico
          </button>
        </div>

        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 14,
          }}
        >
          <thead>
            <tr>
              <th style={thStyle}>Data</th>
              <th style={thStyle}>Projeto</th>
              <th style={thStyle}>Status</th>
              <th style={thStyle}>Mensagem</th>
            </tr>
          </thead>

          <tbody>
            {historyItems.length === 0 && (
              <tr>
                <td colSpan={4} style={tdStyle}>
                  Nenhum registro encontrado.
                </td>
              </tr>
            )}

            {historyItems.map((item: any, index: number) => (
              <tr key={item.id || index}>
                <td style={tdStyle}>{fmtDate(item.created_at)}</td>
                <td style={tdStyle}>{item.project_id || "—"}</td>
                <td style={tdStyle}>
                  <span
                    style={{
                      padding: "4px 8px",
                      borderRadius: 6,
                      color: "#fff",
                      background:
                        item.status === "success" ? "#198754" : "#c52625",
                      fontSize: 12,
                      fontWeight: "bold",
                    }}
                  >
                    {item.status === "success" ? "Sucesso" : "Erro"}
                  </span>
                </td>
                <td style={tdStyle}>{item.message || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      <div style={{ display: "flex", gap: 12, marginTop: 30, flexWrap: "wrap" }}>
        <button onClick={loadStatus} style={buttonStyle("#555")}>
          Atualizar status
        </button>

        <button
          onClick={runNow}
          disabled={running}
          style={buttonStyle(running ? "#999" : "#c52625", running)}
        >
          {running ? "Executando..." : "Executar snapshot agora"}
        </button>

        <button
          onClick={runPortalScanNow}
          disabled={portalScanRunning}
          style={buttonStyle(portalScanRunning ? "#999" : "#198754", portalScanRunning)}
        >
          {portalScanRunning ? "Escaneando portais..." : "Escanear portais cadastrados"}
        </button>

        <button
          onClick={toggleScheduler}
          style={buttonStyle(status.running ? "#333" : "#c52625")}
        >
          {status.running ? "Desativar scheduler" : "Ativar scheduler"}
        </button>

        <button onClick={logoutAdmin} style={buttonStyle("#777")}>
          Sair
        </button>
      </div>
    </main>
  );
}

function Card({ title, value, highlight = false }: any) {
  return (
    <div
      style={{
        background: "#fff",
        padding: 20,
        borderRadius: 8,
        borderLeft: `5px solid ${highlight ? "#c52625" : "#bbb"}`,
        boxShadow: "0 2px 5px rgba(0,0,0,0.05)",
      }}
    >
      <div style={{ fontSize: 13, color: "#777", marginBottom: 8 }}>
        {title}
      </div>

      <div style={{ fontSize: 22, fontWeight: "bold", color: "#222" }}>
        {value}
      </div>
    </div>
  );
}

function Panel({ title, children }: any) {
  return (
    <section
      style={{
        marginTop: 30,
        background: "#fff",
        borderRadius: 8,
        padding: 24,
        boxShadow: "0 2px 5px rgba(0,0,0,0.05)",
      }}
    >
      <h2 style={{ marginTop: 0 }}>{title}</h2>
      {children}
    </section>
  );
}

function Info({ label, value }: any) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "220px 1fr",
        gap: 20,
        padding: "10px 0",
        borderBottom: "1px solid #eee",
      }}
    >
      <strong style={{ color: "#555" }}>{label}</strong>
      <span>{value}</span>
    </div>
  );
}

function buttonStyle(bg: string, disabled = false) {
  return {
    padding: "12px 22px",
    background: bg,
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: disabled ? "not-allowed" : "pointer",
    fontSize: 15,
  };
}

function smallButtonStyle(bg: string) {
  return {
    padding: "9px 16px",
    background: bg,
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
  };
}

const thStyle = {
  textAlign: "left" as const,
  padding: "10px",
  borderBottom: "2px solid #ddd",
  color: "#555",
};

const tdStyle = {
  padding: "10px",
  borderBottom: "1px solid #eee",
  verticalAlign: "top" as const,
};
