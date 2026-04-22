const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://backend:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Erro ao acessar API: ${response.status}`);
  }

  return response.json();
}