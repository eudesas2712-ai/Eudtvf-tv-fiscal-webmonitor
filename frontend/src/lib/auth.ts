export type AuthUser = {
  id: string;
  name: string;
  email: string;
  role: string;
  role_label?: string;
  active?: boolean;
  project_ids?: string[];
  allowed_modules?: string[];
};

const TOKEN_KEY = "tvfiscal_auth_token";
const USER_KEY = "tvfiscal_auth_user";
let fetchInterceptorInstalled = false;

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getAuthUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw) as AuthUser; } catch { return null; }
}

export function setAuthSession(token: string, user: AuthUser) {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuthSession() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function canAccessModule(user: AuthUser | null, module: string): boolean {
  if (!user) return false;
  if (user.role === "admin") return true;
  const modules = user.allowed_modules || [];
  return modules.includes("*") || modules.includes(module);
}

function shouldAttachAuth(input: RequestInfo | URL): boolean {
  if (typeof window === "undefined") return false;
  const token = getAuthToken();
  if (!token) return false;
  const raw = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
  try {
    const url = new URL(raw, window.location.origin);
    return url.origin === window.location.origin || url.origin === "http://localhost:8000" || url.origin === "http://127.0.0.1:8000";
  } catch {
    return false;
  }
}

export function installAuthFetchInterceptor() {
  if (typeof window === "undefined" || fetchInterceptorInstalled) return;
  const originalFetch = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    if (!shouldAttachAuth(input)) return originalFetch(input, init);
    const headers = new Headers(init?.headers || (input instanceof Request ? input.headers : undefined));
    if (!headers.has("Authorization")) {
      const token = getAuthToken();
      if (token) headers.set("Authorization", `Bearer ${token}`);
    }
    return originalFetch(input, { ...init, headers });
  };
  fetchInterceptorInstalled = true;
}
