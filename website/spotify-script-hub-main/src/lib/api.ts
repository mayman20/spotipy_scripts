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

export async function runScript(
  script: "vaulted" | "liked",
  payload?: { target_playlist_id?: string; target_playlist_name?: string },
): Promise<unknown> {
  const token = getSessionToken();
  const path = script === "vaulted" ? "/run/vaulted" : "/run/liked";
  const resp = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload || {}),
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `Run failed: ${resp.status}`);
  }
  return resp.json();
}

export async function fetchAutomationTargets(): Promise<{
  ok: boolean;
  targets: {
    playlists: Array<{ id: string; name: string; description: string }>;
    liked: {
      tag: string;
      name_fallback: string;
      matched_by: "tag" | "name" | "none";
      default_playlist_id: string | null;
      default_playlist_name: string | null;
    };
    vaulted: {
      tag: string;
      name_fallback: string;
      matched_by: "tag" | "name" | "none";
      default_playlist_id: string | null;
      default_playlist_name: string | null;
    };
  };
}> {
  const token = getSessionToken();
  const resp = await fetch(`${API_BASE}/automation/targets`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (resp.status === 404) {
    // Compatibility fallback for older backend deploys.
    return {
      ok: true,
      targets: {
        playlists: [],
        liked: {
          tag: "[spotipy:liked_mirror]",
          name_fallback: "Liked Songs Mirror",
          matched_by: "none",
          default_playlist_id: null,
          default_playlist_name: null,
        },
        vaulted: {
          tag: "[spotipy:vaulted_add]",
          name_fallback: "_vaulted",
          matched_by: "none",
          default_playlist_id: null,
          default_playlist_name: null,
        },
      },
    };
  }
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `Targets fetch failed: ${resp.status}`);
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
    if (resp.status === 404) {
      throw new Error("Backend endpoint /stats/overview not found. Redeploy Render backend from latest main.");
    }
    throw new Error(text || `Stats fetch failed: ${resp.status}`);
  }
  return resp.json();
}

export async function fetchTopStats(timeRange: TimeRange): Promise<{
  ok: boolean;
  data: {
    time_range: TimeRange;
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
  const resp = await fetch(`${API_BASE}/stats/top?time_range=${encodeURIComponent(timeRange)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) {
    const text = await resp.text();
    if (resp.status === 404) {
      throw new Error("Backend endpoint /stats/top not found. Redeploy Render backend from latest main.");
    }
    throw new Error(text || `Top stats fetch failed: ${resp.status}`);
  }
  return resp.json();
}

export async function fetchGenrePlaylistRecommendations(timeRange: TimeRange): Promise<{
  ok: boolean;
  data: {
    time_range: TimeRange;
    genres: string[];
    recommendations: Array<{
      genre: string;
      playlists: Array<{
        id: string;
        name: string;
        description: string;
        owner_name: string;
        url: string;
        open_url: string;
        image_url: string | null;
      }>;
    }>;
  };
}> {
  const token = getSessionToken();
  const resp = await fetch(`${API_BASE}/recommendations/genre-playlists?time_range=${encodeURIComponent(timeRange)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) {
    const text = await resp.text();
    if (resp.status === 404) {
      throw new Error("Backend endpoint /recommendations/genre-playlists not found. Redeploy Render backend from latest main.");
    }
    throw new Error(text || `Genre recommendations fetch failed: ${resp.status}`);
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
