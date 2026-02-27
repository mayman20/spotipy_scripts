const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");
const SESSION_STORAGE_KEY = "spotify_session_token";

export function getApiBaseUrl(): string {
  return API_BASE;
}

export function getSessionToken(): string {
  return localStorage.getItem(SESSION_STORAGE_KEY) || "";
}

export function setSessionToken(token: string): void {
  if (token) {
    localStorage.setItem(SESSION_STORAGE_KEY, token);
  }
}

export function clearSessionToken(): void {
  localStorage.removeItem(SESSION_STORAGE_KEY);
}

export function getSpotifyLoginUrl(): string {
  if (!API_BASE) return "";
  return `${API_BASE}/auth/login`;
}

export async function fetchMe(): Promise<{ spotify_user_id: string; display_name: string }> {
  const token = getSessionToken();
  const resp = await fetch(`${API_BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) {
    throw new Error(`Failed to fetch profile: ${resp.status}`);
  }
  return resp.json();
}

export async function runScript(script: "vaulted" | "liked"): Promise<unknown> {
  const token = getSessionToken();
  const path = script === "vaulted" ? "/run/vaulted" : "/run/liked";
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `Run failed: ${resp.status}`);
  }
  return resp.json();
}

export function captureSessionTokenFromUrl(): boolean {
  const url = new URL(window.location.href);
  const token = url.searchParams.get("session_token");
  if (!token) return false;
  setSessionToken(token);
  url.searchParams.delete("session_token");
  url.searchParams.delete("spotify_user_id");
  url.searchParams.delete("login_error");
  window.history.replaceState({}, "", url.toString());
  return true;
}
