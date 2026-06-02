"use client";

import React, { useState } from "react";
import { setAuthSession } from "../../lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@tvfiscal.local");
  const [password, setPassword] = useState("tvfiscal-admin-2026");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        let detail = "Falha no login.";
        try { detail = (await response.json()).detail || detail; } catch {}
        throw new Error(detail);
      }
      const data = await response.json();
      setAuthSession(data.access_token, data.user);
      window.location.href = "/";
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Erro ao autenticar.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "linear-gradient(135deg,#4a0010,#8d001d 45%,#101828 100%)", padding: 24 }}>
      <section style={{ width: "100%", maxWidth: 460, background: "#fff", borderRadius: 22, padding: 30, boxShadow: "0 24px 70px rgba(0,0,0,0.35)" }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 18 }}>
          <img src="/logo-tv-fiscal-clean.png" alt="TV Fiscal" style={{ width: 220, height: "auto" }} />
        </div>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div style={{ color: "#b00020", fontSize: 12, fontWeight: 900, letterSpacing: 1.4 }}>ACESSO SEGURO · WEBMONITOR</div>
          <h1 style={{ margin: "8px 0 6px", color: "#101828" }}>Entrar na plataforma</h1>
          <p style={{ margin: 0, color: "#667085", fontSize: 14 }}>Use seu usuário para acessar projetos, relatórios, alertas e áreas administrativas.</p>
        </div>

        <form onSubmit={submit} style={{ display: "grid", gap: 14 }}>
          <label style={labelStyle}>E-mail</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required style={inputStyle} />
          <label style={labelStyle}>Senha</label>
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required style={inputStyle} />
          <button disabled={loading} style={{ ...buttonStyle, opacity: loading ? 0.65 : 1 }}>{loading ? "Entrando..." : "Entrar"}</button>
        </form>

        {message && <div style={{ marginTop: 16, padding: 12, borderRadius: 12, background: "#FEF3F2", color: "#B42318", fontSize: 13 }}>{message}</div>}

        <div style={{ marginTop: 22, fontSize: 12, color: "#667085", lineHeight: 1.6, background: "#F9FAFB", padding: 12, borderRadius: 12 }}>
          Primeiro acesso padrão: <strong>admin@tvfiscal.local</strong> / <strong>tvfiscal-admin-2026</strong>. Altere a senha após criar os usuários reais.
        </div>
      </section>
    </main>
  );
}

const labelStyle: React.CSSProperties = { fontSize: 13, fontWeight: 800, color: "#344054" };
const inputStyle: React.CSSProperties = { height: 44, border: "1px solid #D0D5DD", borderRadius: 12, padding: "0 12px", fontSize: 15, outline: "none" };
const buttonStyle: React.CSSProperties = { marginTop: 10, height: 46, border: 0, borderRadius: 12, background: "#b00020", color: "#fff", fontWeight: 900, cursor: "pointer" };
