import { adminJson, adminFetch, API_BASE } from "./apiClient";

export { API_BASE };

export async function apiGet<T>(path: string): Promise<T> {
  return adminJson<T>(path, {
    method: "GET",
    bearer: false,
    admin: true,
    json: true,
  });
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return adminJson<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
    bearer: false,
    admin: true,
    json: true,
  });
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  return adminJson<T>(path, {
    method: "PUT",
    body: JSON.stringify(body),
    bearer: false,
    admin: true,
    json: true,
  });
}

export async function apiDelete<T>(path: string): Promise<T> {
  return adminJson<T>(path, {
    method: "DELETE",
    bearer: false,
    admin: true,
    json: true,
  });
}

export async function apiRaw(path: string, options: RequestInit = {}) {
  return adminFetch(path, {
    ...options,
    bearer: false,
    admin: true,
    json: false,
  });
}
