const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/+$/, "");
const SESSION_STORAGE_KEY = "spotify_session_token";
export type TimeRange = "short_term" | "medium_term" | "long_term";

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
  const returnTo = `${window.location.origin}${window.location.pathname}`;
  return `${API_BASE}/auth/login?return_to=${encodeURIComponent(returnTo)}`;
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

export async function fetchOverviewStats(timeRange: TimeRange): Promise<{
  ok: boolean;
  overview: {
    time_range: TimeRange;
    counts: {
      playlists_total: number;
      playlists_owned: number;
      saved_tracks_total: number;
      added_7d: number;
      added_30d: number;
    };
    top_artists: Array<{
      id: string;
      name: string;
      genres: string[];
      popularity: number;
      image_url: string | null;
    }>;
    top_tracks: Array<{
      id: string;
      name: string;
      artists: string[];
      popularity: number;
      image_url: string | null;
    }>;
  };
}> {
  const token = getSessionToken();
  const resp = await fetch(`${API_BASE}/stats/overview?time_range=${encodeURIComponent(timeRange)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `Stats fetch failed: ${resp.status}`);
  }
  return resp.json();
}

export function captureSessionTokenFromUrl(): boolean {
  const url = new URL(window.location.href);
  let token = url.searchParams.get("session_token");
  if (!token && url.hash.includes("?")) {
    const hashQuery = url.hash.slice(url.hash.indexOf("?") + 1);
    token = new URLSearchParams(hashQuery).get("session_token");
  }
  if (!token) return false;
  setSessionToken(token);
  url.searchParams.delete("session_token");
  url.searchParams.delete("spotify_user_id");
  url.searchParams.delete("login_error");
  window.history.replaceState({}, "", url.toString());
  if (window.location.hash !== "#/dashboard") {
    window.location.hash = "#/dashboard";
  }
  return true;
}
