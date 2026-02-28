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
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


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
        result = _backoff(sp.search, q=f'genre:"{genre}"', type="playlist", limit=8)
        items = (((result or {}).get("playlists") or {}).get("items") or [])
        picks = []
        for playlist in items:
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
