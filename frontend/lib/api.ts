const API_BASE = "/api";

export function getToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("ndsp_token") || "";
}

export function setToken(token: string) {
  localStorage.setItem("ndsp_token", token);
}

export function clearToken() {
  localStorage.removeItem("ndsp_token");
}

export async function api(path: string, options: RequestInit = {}) {
  const token = getToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {})
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers
  });

  const text = await res.text();

  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!res.ok) {
    throw new Error(typeof data === "string" ? data : JSON.stringify(data));
  }

  return data;
}
