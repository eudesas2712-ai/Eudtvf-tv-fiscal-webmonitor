const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://backend:8000";

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("tvfiscal_auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: authHeaders(),
  });

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`Erro ao acessar API: ${response.status}${body ? ` - ${body}` : ""}`);
  }

  return response.json();
}
