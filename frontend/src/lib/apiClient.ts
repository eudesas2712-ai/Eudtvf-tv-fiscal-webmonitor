const ADMIN_TOKEN_KEY = "tvfiscal_admin_token";
const SESSION_TOKEN_KEY = "tvfiscal_auth_token";
const DEFAULT_ADMIN_TOKEN = "tvfiscal-admin-2026";

export const API_BASE =
  (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_API_BASE ||
    "http://localhost:8000"
  ).replace(/\/$/, "");

type ApiHeaderOptions = {
  json?: boolean;
  admin?: boolean;
  bearer?: boolean;
};

type ApiFetchOptions = RequestInit & {
  bearer?: boolean;
  admin?: boolean;
  json?: boolean;
};

function isBrowser() {
  return typeof window !== "undefined";
}

export function getAdminToken() {
  if (!isBrowser()) return DEFAULT_ADMIN_TOKEN;
  return localStorage.getItem(ADMIN_TOKEN_KEY) || DEFAULT_ADMIN_TOKEN;
}

export function getSessionToken() {
  if (!isBrowser()) return null;
  return localStorage.getItem(SESSION_TOKEN_KEY);
}

export function buildApiHeaders(options: ApiHeaderOptions = {}) {
  const { json = true, admin = true, bearer = false } = options;

  const headers: Record<string, string> = {};

  if (json) {
    headers["Content-Type"] = "application/json";
  }

  if (admin) {
    headers["X-Admin-Token"] = getAdminToken();
  }

  /*
    Importante:
    bearer=false por padrão nas telas administrativas.
    Isso evita o erro 401 "Sessão expirada" quando existe JWT antigo no localStorage.
  */
  if (bearer) {
    const token = getSessionToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  return headers;
}

export function apiUrl(pathOrUrl: string) {
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl;
  return `${API_BASE}${pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`}`;
}

export async function adminFetch(pathOrUrl: string, options: ApiFetchOptions = {}) {
  const {
    bearer = false,
    admin = true,
    json = true,
    headers,
    ...rest
  } = options;

  return fetch(apiUrl(pathOrUrl), {
    ...rest,
    cache: rest.cache || "no-store",
    headers: {
      ...buildApiHeaders({ json, admin, bearer }),
      ...(headers || {}),
    },
  });
}

export async function adminJson<T>(pathOrUrl: string, options: ApiFetchOptions = {}): Promise<T> {
  const res = await adminFetch(pathOrUrl, options);

  if (!res.ok) {
    let detail = "";

    try {
      detail = JSON.stringify(await res.json());
    } catch {
      detail = await res.text().catch(() => "");
    }

    throw new Error(`Erro HTTP ${res.status}${detail ? `: ${detail}` : ""}`);
  }

  return res.json() as Promise<T>;
}

export async function adminDownload(pathOrUrl: string, filenameFallback: string) {
  const res = await adminFetch(pathOrUrl, {
    json: false,
    bearer: false,
    admin: true,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Erro ao exportar arquivo: ${res.status} ${text || res.statusText}`);
  }

  const blob = await res.blob();
  const cd = res.headers.get("content-disposition") || "";
  const match = cd.match(/filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)\"?/i);
  const filename = decodeURIComponent(match?.[1] || match?.[2] || filenameFallback);

  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(objectUrl);
}
