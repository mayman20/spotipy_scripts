import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import spotipy
from spotipy.exceptions import SpotifyException

EXCLUDE_DESCRIPTION_FLAG = "-*"
VAULTED_TAG = "[spotipy:vaulted_add]"
LIKED_TAG = "[spotipy:liked_mirror]"
VALID_TIME_RANGES = {"short_term", "medium_term", "long_term"}
_CACHE_TTL_SECONDS = 120
_CACHE: dict[str, tuple[float, dict]] = {}


def _backoff(call, *args, **kwargs):
    delay = 1.0
    while True:
        try:
            return call(*args, **kwargs)
        except SpotifyException as exc:
            if exc.http_status == 429:
                retry_after = 2
                try:
                    retry_after = int(getattr(exc, "headers", {}).get("Retry-After", 2))
                except Exception:
                    pass
                time.sleep(max(retry_after, 2))
                continue
            raise
        except Exception:
            time.sleep(delay)
            delay = min(delay * 2, 16)


def _cache_get(key: str) -> dict | None:
    record = _CACHE.get(key)
    if not record:
        return None
    expires_at, value = record
    if time.time() > expires_at:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: dict, ttl: int = _CACHE_TTL_SECONDS) -> dict:
    _CACHE[key] = (time.time() + ttl, value)
    return value


def _all_user_playlists(sp: spotipy.Spotify) -> list[dict]:
    playlists = []
    response = _backoff(sp.current_user_playlists, limit=50)
    while response:
        playlists.extend(response.get("items", []))
        response = _backoff(sp.next, response) if response.get("next") else None
    return playlists


def _find_playlist_by_tag(playlists: list[dict], user_id: str, tag: str) -> dict | None:
    for playlist in playlists:
        if (playlist.get("owner") or {}).get("id") != user_id:
            continue
        description = (playlist.get("description") or "").lower()
        if tag.lower() in description:
            return playlist
    return None


def _find_owned_playlist_by_name(playlists: list[dict], user_id: str, playlist_name: str) -> dict | None:
    expected = (playlist_name or "").strip().casefold()
    if not expected:
        return None
    for playlist in playlists:
        if (playlist.get("owner") or {}).get("id") != user_id:
            continue
        name = (playlist.get("name") or "").strip().casefold()
        if name == expected:
            return playlist
    return None


def _find_owned_playlist_by_id(playlists: list[dict], user_id: str, playlist_id: str | None) -> dict | None:
    if not playlist_id:
        return None
    for playlist in playlists:
        if (playlist.get("owner") or {}).get("id") != user_id:
            continue
        if playlist.get("id") == playlist_id:
            return playlist
    return None


def _has_tag(description: str, tag: str) -> bool:
    return tag.lower() in (description or "").lower()


def _ensure_playlist_tag(sp: spotipy.Spotify, playlist: dict, tag: str) -> None:
    description = playlist.get("description") or ""
    if _has_tag(description, tag):
        return
    new_description = f"{description.strip()} {tag}".strip()
    _backoff(sp.playlist_change_details, playlist["id"], description=new_description)


def _playlist_track_ids(sp: spotipy.Spotify, playlist_id: str) -> list[str]:
    tracks: list[str] = []
    results = _backoff(sp.playlist_tracks, playlist_id, fields="items(track.id),next", limit=100)
    while results:
        for item in results.get("items", []):
            track = item.get("track") or {}
            tid = track.get("id")
            if tid:
                tracks.append(tid)
        results = _backoff(sp.next, results) if results.get("next") else None
    return tracks


def _liked_track_ids(sp: spotipy.Spotify) -> list[str]:
    liked: list[str] = []
    results = _backoff(sp.current_user_saved_tracks, limit=50)
    while results:
        for item in results.get("items", []):
            track = item.get("track") or {}
            tid = track.get("id")
            if tid:
                liked.append(tid)
        results = _backoff(sp.next, results) if results.get("next") else None
    return liked


def _parse_spotify_date(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _fetch_top_lists(sp: spotipy.Spotify, time_range: str, limit: int = 25) -> dict:
    top_artists_resp = _backoff(sp.current_user_top_artists, time_range=time_range, limit=limit)
    top_tracks_resp = _backoff(sp.current_user_top_tracks, time_range=time_range, limit=limit)

    top_artists = []
    for artist in top_artists_resp.get("items", []):
        images = artist.get("images") or []
        image_url = images[0]["url"] if images else None
        top_artists.append(
            {
                "id": artist.get("id"),
                "name": artist.get("name"),
                "genres": artist.get("genres") or [],
                "popularity": artist.get("popularity"),
                "image_url": image_url,
            }
        )

    top_tracks = []
    for track in top_tracks_resp.get("items", []):
        album = track.get("album") or {}
        images = album.get("images") or []
        image_url = images[0]["url"] if images else None
        artists = [a.get("name") for a in (track.get("artists") or []) if a.get("name")]
        top_tracks.append(
            {
                "id": track.get("id"),
                "name": track.get("name"),
                "artists": artists,
                "popularity": track.get("popularity"),
                "image_url": image_url,
            }
        )

    return {"top_artists": top_artists, "top_tracks": top_tracks}


def get_dashboard_overview(sp: spotipy.Spotify, time_range: str = "short_term") -> dict:
    if time_range not in VALID_TIME_RANGES:
        time_range = "short_term"

    me = _backoff(sp.me)
    user_id = me["id"]
    cache_key = f"overview:{user_id}:{time_range}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    # Playlist totals and owned count.
    playlists_total = 0
    playlists_owned = 0
    playlist_resp = _backoff(sp.current_user_playlists, limit=50, offset=0)
    playlists_total = int(playlist_resp.get("total", 0))
    while playlist_resp:
        for pl in playlist_resp.get("items", []):
            if (pl.get("owner") or {}).get("id") == user_id:
                playlists_owned += 1
        if playlist_resp.get("next"):
            playlist_resp = _backoff(sp.next, playlist_resp)
        else:
            break

    # Saved tracks total and recent adds (7d/30d), scanning newest-first until older than 30d.
    saved_resp = _backoff(sp.current_user_saved_tracks, limit=50, offset=0)
    saved_total = int(saved_resp.get("total", 0))
    now = datetime.now(timezone.utc)
    cut_7 = now - timedelta(days=7)
    cut_30 = now - timedelta(days=30)
    added_7d = 0
    added_30d = 0
    while saved_resp:
        items = saved_resp.get("items", [])
        stop = False
        for item in items:
            dt = _parse_spotify_date(item.get("added_at") or "")
            if not dt:
                continue
            if dt >= cut_30:
                added_30d += 1
                if dt >= cut_7:
                    added_7d += 1
            else:
                stop = True
                break
        if stop or not saved_resp.get("next"):
            break
        saved_resp = _backoff(sp.next, saved_resp)

    payload = {
        "time_range": time_range,
        "counts": {
            "playlists_total": playlists_total,
            "playlists_owned": playlists_owned,
            "saved_tracks_total": saved_total,
            "added_7d": added_7d,
            "added_30d": added_30d,
        },
        # Top lists are loaded via /stats/top to keep this endpoint fast/reliable.
        "top_artists": [],
        "top_tracks": [],
    }
    return _cache_set(cache_key, payload)


def get_top_lists(sp: spotipy.Spotify, time_range: str = "short_term") -> dict:
    if time_range not in VALID_TIME_RANGES:
        time_range = "short_term"
    me = _backoff(sp.me)
    user_id = me["id"]
    cache_key = f"top_lists:{user_id}:{time_range}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    payload = {"time_range": time_range, **_fetch_top_lists(sp, time_range=time_range, limit=25)}
    return _cache_set(cache_key, payload)


def get_track_longevity(sp: spotipy.Spotify) -> dict:
    me = _backoff(sp.me)
    user_id = me["id"]
    cache_key = f"track_longevity:{user_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    ranges = ("short_term", "medium_term", "long_term")
    weights = {"short_term": 1.0, "medium_term": 1.2, "long_term": 1.4}
    tracks_by_id: dict[str, dict] = {}

    for time_range in ranges:
        resp = _backoff(sp.current_user_top_tracks, time_range=time_range, limit=50)
        for idx, track in enumerate(resp.get("items", []) or [], start=1):
            tid = track.get("id")
            if not tid:
                continue
            if tid not in tracks_by_id:
                album = track.get("album") or {}
                images = album.get("images") or []
                image_url = images[0]["url"] if images else None
                artists = [a.get("name") for a in (track.get("artists") or []) if a.get("name")]
                tracks_by_id[tid] = {
                    "id": tid,
                    "name": track.get("name") or "",
                    "artists": artists,
                    "image_url": image_url,
                    "popularity": track.get("popularity") or 0,
                    "ranks": {},
                }
            tracks_by_id[tid]["ranks"][time_range] = idx

    items = []
    for track in tracks_by_id.values():
        ranks = track["ranks"]
        overlap_count = len(ranks)
        rank_score = 0.0
        for r, rank in ranks.items():
            rank_score += (51 - rank) * weights.get(r, 1.0)
        longevity_score = round(overlap_count * 100 + rank_score, 1)

        items.append(
            {
                "id": track["id"],
                "name": track["name"],
                "artists": track["artists"],
                "image_url": track["image_url"],
                "popularity": track["popularity"],
                "overlap_count": overlap_count,
                "present_in": sorted(list(ranks.keys())),
                "ranks": ranks,
                "longevity_score": longevity_score,
            }
        )

    # Prefer tracks appearing in multiple windows, then highest score.
    items.sort(key=lambda x: (x["overlap_count"], x["longevity_score"]), reverse=True)

    payload = {
        "tracks": items[:25],
        "scoring": {
            "base_per_range": 100,
            "rank_formula": "sum((51-rank) * weight)",
            "weights": weights,
        },
    }
    return _cache_set(cache_key, payload, ttl=300)


def get_genre_playlist_recommendations(sp: spotipy.Spotify, time_range: str = "medium_term") -> dict:
    if time_range not in VALID_TIME_RANGES:
        time_range = "medium_term"
    me = _backoff(sp.me)
    user_id = me["id"]
    cache_key = f"genre_recs:{user_id}:{time_range}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    top_artists_resp = _backoff(sp.current_user_top_artists, time_range=time_range, limit=30)
    artists = top_artists_resp.get("items", [])

    genre_scores: dict[str, int] = defaultdict(int)
    for idx, artist in enumerate(artists):
        weight = max(1, 30 - idx)
        for genre in artist.get("genres") or []:
            g = (genre or "").strip()
            if g:
                genre_scores[g] += weight

    top_genres = [g for g, _ in sorted(genre_scores.items(), key=lambda kv: kv[1], reverse=True)[:5]]

    recommendations = []
    seen_ids: set[str] = set()
    for genre in top_genres:
        # Query Spotify playlists by genre and keep only unique IDs globally.
        result = _backoff(sp.search, q=genre, type="playlist", limit=8)
        items = (((result or {}).get("playlists") or {}).get("items") or [])
        picks = []
        for playlist in items:
            if not playlist:
                continue
            pid = playlist.get("id")
            if not pid or pid in seen_ids:
                continue
            seen_ids.add(pid)
            images = playlist.get("images") or []
            image_url = images[0]["url"] if images else None
            picks.append(
                {
                    "id": pid,
                    "name": playlist.get("name") or "",
                    "description": playlist.get("description") or "",
                    "owner_name": (playlist.get("owner") or {}).get("display_name") or "",
                    "url": ((playlist.get("external_urls") or {}).get("spotify") or ""),
                    "open_url": f"https://open.spotify.com/playlist/{pid}",
                    "image_url": image_url,
                }
            )
            if len(picks) >= 4:
                break

        recommendations.append({"genre": genre, "playlists": picks})

    payload = {"time_range": time_range, "genres": top_genres, "recommendations": recommendations}
    return _cache_set(cache_key, payload)


def get_recently_played(sp: spotipy.Spotify) -> dict:
    me = _backoff(sp.me)
    user_id = me["id"]
    cache_key = f"recently_played:{user_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    results = _backoff(sp.current_user_recently_played, limit=50)
    items = (results or {}).get("items") or []
    tracks = []
    seen: set[str] = set()
    for item in items:
        if not item:
            continue
        track = item.get("track") or {}
        tid = track.get("id")
        if not tid or tid in seen:
            continue
        seen.add(tid)
        album = track.get("album") or {}
        images = album.get("images") or []
        image_url = images[0]["url"] if images else None
        artists = [a.get("name") for a in (track.get("artists") or []) if a.get("name")]
        tracks.append({
            "id": tid,
            "name": track.get("name") or "",
            "artists": artists,
            "image_url": image_url,
            "played_at": item.get("played_at") or "",
        })

    payload = {"tracks": tracks}
    return _cache_set(cache_key, payload, ttl=60)


def get_listening_pattern(sp: spotipy.Spotify) -> dict:
    me = _backoff(sp.me)
    user_id = me["id"]
    cache_key = f"listening_pattern:{user_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    # Primary source: recently played (requires user-read-recently-played scope).
    items = []
    source = "recently_played"
    note = None
    try:
        results = _backoff(sp.current_user_recently_played, limit=50)
        items = (results or {}).get("items") or []
    except SpotifyException as exc:
        # Fallback when scope is missing or endpoint unavailable.
        if exc.http_status in (401, 403):
            source = "saved_tracks_added_at"
            note = "Using liked-track added timestamps because recently played scope is unavailable."
            items = []
            saved = _backoff(sp.current_user_saved_tracks, limit=50, offset=0)
            pages = 0
            while saved and pages < 4:  # up to ~200 records for lightweight fallback
                for it in (saved.get("items") or []):
                    items.append({"played_at": (it or {}).get("added_at") or ""})
                if not saved.get("next"):
                    break
                saved = _backoff(sp.next, saved)
                pages += 1
        else:
            raise

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    grid = [[0 for _ in range(24)] for _ in range(7)]
    total_events = 0

    for item in items:
        played_at = (item or {}).get("played_at") or ""
        dt = _parse_spotify_date(played_at)
        if not dt:
            continue
        # Keep UTC for consistency since user timezone is not directly provided by Spotify here.
        dt_utc = dt.astimezone(timezone.utc)
        day_idx = dt_utc.weekday()  # Monday=0
        hour = dt_utc.hour
        grid[day_idx][hour] += 1
        total_events += 1

    max_cell = max((value for row in grid for value in row), default=0)
    has_enough_data = total_events >= 20

    payload = {
        "source": source,
        "note": note,
        "timezone": "UTC",
        "total_events": total_events,
        "max_cell": max_cell,
        "has_enough_data": has_enough_data,
        "day_labels": day_names,
        "hours": list(range(24)),
        "grid": grid,
    }
    return _cache_set(cache_key, payload, ttl=120)


def search_artists(sp: spotipy.Spotify, query: str, limit: int = 6) -> dict:
    if not (query or "").strip():
        return {"artists": []}
    result = _backoff(sp.search, q=query.strip(), type="artist", limit=limit)
    artists = []
    for artist in (((result or {}).get("artists") or {}).get("items") or []):
        if not artist:
            continue
        images = artist.get("images") or []
        image_url = images[0]["url"] if images else None
        artists.append({
            "id": artist.get("id") or "",
            "name": artist.get("name") or "",
            "genres": artist.get("genres") or [],
            "popularity": artist.get("popularity") or 0,
            "image_url": image_url,
        })
    return {"artists": artists}


def get_artist_catalog_depth(sp: spotipy.Spotify, artist_id: str) -> dict:
    me = _backoff(sp.me)
    user_id = me["id"]
    cache_key = f"catalog:{user_id}:{artist_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    artist_info = _backoff(sp.artist, artist_id) or {}
    artist_name = artist_info.get("name") or ""

    albums_resp = _backoff(sp.artist_albums, artist_id, album_type="album", limit=50, country="US")
    all_albums = (albums_resp or {}).get("items") or []

    seen_names: set[str] = set()
    unique_albums = []
    for album in all_albums:
        if not album:
            continue
        name = (album.get("name") or "").strip().lower()
        if name in seen_names:
            continue
        seen_names.add(name)
        images = album.get("images") or []
        image_url = images[0]["url"] if images else None
        unique_albums.append({
            "id": album["id"],
            "name": album.get("name") or "",
            "year": (album.get("release_date") or "")[:4],
            "total_tracks": album.get("total_tracks") or 0,
            "image_url": image_url,
        })

    unique_albums.sort(key=lambda a: a["year"], reverse=True)

    album_ids = [a["id"] for a in unique_albums]
    saved_flags: list[bool] = []
    for i in range(0, len(album_ids), 50):
        batch = album_ids[i:i + 50]
        result = _backoff(sp.current_user_saved_albums_contains, batch)
        saved_flags.extend(result or [False] * len(batch))

    for album, saved in zip(unique_albums, saved_flags):
        album["saved"] = saved

    total_albums = len(unique_albums)
    saved_albums_count = sum(1 for s in saved_flags if s)
    total_tracks = sum(a["total_tracks"] for a in unique_albums)
    saved_tracks_est = sum(a["total_tracks"] for a, s in zip(unique_albums, saved_flags) if s)
    pct = round(saved_albums_count / total_albums * 100, 1) if total_albums else 0.0

    payload = {
        "artist_id": artist_id,
        "artist_name": artist_name,
        "total_albums": total_albums,
        "saved_albums": saved_albums_count,
        "total_tracks": total_tracks,
        "saved_tracks_est": saved_tracks_est,
        "pct": pct,
        "albums": unique_albums,
    }
    return _cache_set(cache_key, payload, ttl=300)


def get_genre_breakdown(sp: spotipy.Spotify) -> dict:
    me = _backoff(sp.me)
    user_id = me["id"]
    cache_key = f"genre_breakdown:{user_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    artist_ids: set[str] = set()
    results = _backoff(sp.current_user_saved_tracks, limit=50)
    scanned = 0
    while results and scanned < 1000:
        for item in (results.get("items") or []):
            track = (item or {}).get("track") or {}
            for artist in (track.get("artists") or []):
                aid = (artist or {}).get("id")
                if aid:
                    artist_ids.add(aid)
        scanned += len(results.get("items") or [])
        results = _backoff(sp.next, results) if results.get("next") else None

    genre_counts: dict[str, int] = defaultdict(int)
    artist_id_list = list(artist_ids)
    for i in range(0, len(artist_id_list), 50):
        batch = artist_id_list[i:i + 50]
        artists_resp = _backoff(sp.artists, batch)
        for artist in ((artists_resp or {}).get("artists") or []):
            for genre in ((artist or {}).get("genres") or []):
                if genre:
                    genre_counts[genre] += 1

    top = sorted(genre_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    total = sum(c for _, c in top)
    genres = [{"genre": g, "count": c, "pct": round(c / total * 100, 1) if total else 0} for g, c in top]

    payload = {"genres": genres, "total_artists": len(artist_ids), "songs_scanned": scanned}
    return _cache_set(cache_key, payload, ttl=600)


def get_mood_timeline(sp: spotipy.Spotify) -> dict:
    me = _backoff(sp.me)
    user_id = me["id"]
    cache_key = f"mood_timeline:{user_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    timeline = []

    def _release_year(track: dict) -> int | None:
        album = (track or {}).get("album") or {}
        date_s = (album.get("release_date") or "").strip()
        if len(date_s) >= 4 and date_s[:4].isdigit():
            return int(date_s[:4])
        return None

    def _proxy_point(time_range: str, tracks: list[dict]) -> dict:
        if not tracks:
            return {
                "time_range": time_range,
                "popularity": None,
                "explicitness": None,
                "freshness": None,
                "length": None,
            }

        pop = [((t or {}).get("popularity") or 0) / 100 for t in tracks]
        explicit = [1.0 if (t or {}).get("explicit") else 0.0 for t in tracks]
        length = [min(((t or {}).get("duration_ms") or 0) / 360000, 1.0) for t in tracks]

        now_year = datetime.now(timezone.utc).year
        min_year = 1970
        fresh_vals: list[float] = []
        for t in tracks:
            yr = _release_year(t)
            if yr is None:
                continue
            fresh_vals.append(max(0.0, min((yr - min_year) / max(now_year - min_year, 1), 1.0)))

        def _avg(vals: list[float]) -> float | None:
            if not vals:
                return None
            return round(sum(vals) / len(vals), 3)

        return {
            "time_range": time_range,
            "popularity": _avg(pop),
            "explicitness": _avg(explicit),
            "freshness": _avg(fresh_vals),
            "length": _avg(length),
        }

    def _build_proxy_timeline() -> list[dict]:
        proxy = []
        for tr in ("short_term", "medium_term", "long_term"):
            resp = _backoff(sp.current_user_top_tracks, time_range=tr, limit=25)
            items = (resp.get("items") or [])
            proxy.append(_proxy_point(tr, items))
        return proxy

    for time_range in ("short_term", "medium_term", "long_term"):
        top_tracks_resp = _backoff(sp.current_user_top_tracks, time_range=time_range, limit=25)
        track_ids = [t["id"] for t in (top_tracks_resp.get("items") or []) if t and t.get("id")]
        if not track_ids:
            timeline.append({"time_range": time_range, "energy": None, "valence": None, "danceability": None, "acousticness": None})
            continue
        try:
            features_resp = _backoff(sp.audio_features, track_ids)
        except SpotifyException as exc:
            if exc.http_status in (400, 403):
                payload = {
                    "mode": "proxy",
                    "timeline": [],
                    "proxy_timeline": _build_proxy_timeline(),
                    "error": "audio_features_unavailable",
                }
                return _cache_set(cache_key, payload, ttl=3600)
            raise
        valid = [f for f in (features_resp or []) if f]
        if not valid:
            timeline.append({"time_range": time_range, "energy": None, "valence": None, "danceability": None, "acousticness": None})
            continue

        def avg(key: str) -> float:
            return round(sum(f[key] for f in valid) / len(valid), 3)

        timeline.append({
            "time_range": time_range,
            "energy": avg("energy"),
            "valence": avg("valence"),
            "danceability": avg("danceability"),
            "acousticness": avg("acousticness"),
        })

    payload = {
        "mode": "audio_features",
        "timeline": timeline,
        "proxy_timeline": [],
        "error": None,
    }
    return _cache_set(cache_key, payload, ttl=300)


def run_vaulted_add(
    sp: spotipy.Spotify,
    playlist_name: str = "_vaulted",
    playlist_id: str | None = None,
) -> dict:
    me = _backoff(sp.me)
    user_id = me["id"]
    playlists = _all_user_playlists(sp)

    existing_playlist = _find_owned_playlist_by_id(playlists, user_id, playlist_id)
    if not existing_playlist:
        existing_playlist = _find_playlist_by_tag(playlists, user_id, VAULTED_TAG)
    if not existing_playlist:
        existing_playlist = _find_owned_playlist_by_name(playlists, user_id, playlist_name)

    if not existing_playlist:
        created = _backoff(
            sp.user_playlist_create,
            user=user_id,
            name=playlist_name,
            public=False,
            description=f"Managed by Spotipy Scripts {VAULTED_TAG}",
        )
        existing_playlist = created
    else:
        # Keep existing description and append automation tag if missing.
        _ensure_playlist_tag(sp, existing_playlist, VAULTED_TAG)

    existing_playlist_id = existing_playlist["id"]
    existing_playlist_name = existing_playlist.get("name") or playlist_name

    all_tracks: set[str] = set()
    excluded = 0
    for playlist in playlists:
        owner_id = (playlist.get("owner") or {}).get("id")
        description = playlist.get("description") or ""
        if owner_id == user_id and EXCLUDE_DESCRIPTION_FLAG in description:
            excluded += 1
        if owner_id == user_id and playlist.get("id") != existing_playlist_id and EXCLUDE_DESCRIPTION_FLAG not in description:
            all_tracks.update(_playlist_track_ids(sp, playlist["id"]))

    all_tracks.update(_liked_track_ids(sp))
    existing = set(_playlist_track_ids(sp, existing_playlist_id))

    to_add = [tid for tid in (all_tracks - existing) if tid]
    to_remove = [tid for tid in (existing - all_tracks) if tid]

    for i in range(0, len(to_add), 100):
        _backoff(sp.playlist_add_items, existing_playlist_id, to_add[i : i + 100])

    for i in range(0, len(to_remove), 100):
        _backoff(sp.playlist_remove_all_occurrences_of_items, existing_playlist_id, to_remove[i : i + 100])

    return {
        "playlist_id": existing_playlist_id,
        "playlist_name": existing_playlist_name,
        "added": len(to_add),
        "removed": len(to_remove),
        "excluded_playlists": excluded,
        "tag": VAULTED_TAG,
    }


def _get_or_create_playlist(
    sp: spotipy.Spotify,
    user_id: str,
    playlist_name: str,
    public: bool = False,
    tag: str | None = None,
    playlist_id: str | None = None,
) -> dict:
    playlists = _all_user_playlists(sp)
    explicit = _find_owned_playlist_by_id(playlists, user_id, playlist_id)
    if explicit:
        if tag:
            _ensure_playlist_tag(sp, explicit, tag)
        return explicit
    if tag:
        tagged = _find_playlist_by_tag(playlists, user_id, tag)
        if tagged:
            return tagged
    named = _find_owned_playlist_by_name(playlists, user_id, playlist_name)
    if named:
        if tag:
            _ensure_playlist_tag(sp, named, tag)
        return named
    description = "Managed by Spotipy Scripts"
    if tag:
        description = f"{description} {tag}"
    created = _backoff(sp.user_playlist_create, user=user_id, name=playlist_name, public=public, description=description)
    return created


def run_liked_add(sp: spotipy.Spotify, playlist_name: str = "Liked Songs Mirror", playlist_id: str | None = None) -> dict:
    me = _backoff(sp.me)
    user_id = me["id"]
    playlist = _get_or_create_playlist(
        sp,
        user_id,
        playlist_name,
        public=False,
        tag=LIKED_TAG,
        playlist_id=playlist_id,
    )
    playlist_id = playlist["id"]
    resolved_playlist_name = playlist.get("name") or playlist_name

    desired = _liked_track_ids(sp)  # API returns newest -> oldest

    head = desired[:100]
    _backoff(sp.playlist_replace_items, playlist_id, head)
    for i in range(100, len(desired), 100):
        _backoff(sp.playlist_add_items, playlist_id, desired[i : i + 100])

    return {"playlist_id": playlist_id, "playlist_name": resolved_playlist_name, "total_tracks": len(desired), "tag": LIKED_TAG}


def get_automation_targets(sp: spotipy.Spotify) -> dict:
    me = _backoff(sp.me)
    user_id = me["id"]
    playlists = _all_user_playlists(sp)
    owned = [p for p in playlists if (p.get("owner") or {}).get("id") == user_id]

    def resolve_default(tag: str, fallback_name: str) -> tuple[str, dict | None]:
        tagged = _find_playlist_by_tag(owned, user_id, tag)
        if tagged:
            return "tag", tagged
        named = _find_owned_playlist_by_name(owned, user_id, fallback_name)
        if named:
            return "name", named
        return "none", None

    liked_match, liked_default = resolve_default(LIKED_TAG, "liked songs mirror")
    vaulted_match, vaulted_default = resolve_default(VAULTED_TAG, "_vaulted")

    options = []
    for playlist in owned:
        options.append(
            {
                "id": playlist.get("id"),
                "name": playlist.get("name") or "",
                "description": playlist.get("description") or "",
            }
        )

    return {
        "playlists": options,
        "liked": {
            "tag": LIKED_TAG,
            "name_fallback": "Liked Songs Mirror",
            "matched_by": liked_match,
            "default_playlist_id": liked_default.get("id") if liked_default else None,
            "default_playlist_name": liked_default.get("name") if liked_default else None,
        },
        "vaulted": {
            "tag": VAULTED_TAG,
            "name_fallback": "_vaulted",
            "matched_by": vaulted_match,
            "default_playlist_id": vaulted_default.get("id") if vaulted_default else None,
            "default_playlist_name": vaulted_default.get("name") if vaulted_default else None,
        },
    }
