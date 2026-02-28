import time

import spotipy
from spotipy.exceptions import SpotifyException

EXCLUDE_DESCRIPTION_FLAG = "-*"
VAULTED_TAG = "[spotipy:vaulted_add]"
LIKED_TAG = "[spotipy:liked_mirror]"


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


def run_vaulted_add(sp: spotipy.Spotify, playlist_name: str = "_vaulted") -> dict:
    me = _backoff(sp.me)
    user_id = me["id"]
    playlists = _all_user_playlists(sp)

    existing_playlist = _find_playlist_by_tag(playlists, user_id, VAULTED_TAG)
    if not existing_playlist:
        for playlist in playlists:
            if playlist.get("name") == playlist_name and (playlist.get("owner") or {}).get("id") == user_id:
                existing_playlist = playlist
                break

    if not existing_playlist:
        created = _backoff(
            sp.user_playlist_create,
            user=user_id,
            name=playlist_name,
            public=False,
            description=f"Managed by Spotipy Scripts {VAULTED_TAG}",
        )
        existing_playlist = created

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
) -> dict:
    playlists = _all_user_playlists(sp)
    if tag:
        tagged = _find_playlist_by_tag(playlists, user_id, tag)
        if tagged:
            return tagged
    for pl in playlists:
        if pl.get("name") == playlist_name and (pl.get("owner") or {}).get("id") == user_id:
            return pl
    description = "Managed by Spotipy Scripts"
    if tag:
        description = f"{description} {tag}"
    created = _backoff(sp.user_playlist_create, user=user_id, name=playlist_name, public=public, description=description)
    return created


def run_liked_add(sp: spotipy.Spotify, playlist_name: str = "Liked Songs Mirror") -> dict:
    me = _backoff(sp.me)
    user_id = me["id"]
    playlist = _get_or_create_playlist(sp, user_id, playlist_name, public=False, tag=LIKED_TAG)
    playlist_id = playlist["id"]
    resolved_playlist_name = playlist.get("name") or playlist_name

    desired = _liked_track_ids(sp)  # API returns newest -> oldest

    head = desired[:100]
    _backoff(sp.playlist_replace_items, playlist_id, head)
    for i in range(100, len(desired), 100):
        _backoff(sp.playlist_add_items, playlist_id, desired[i : i + 100])

    return {"playlist_id": playlist_id, "playlist_name": resolved_playlist_name, "total_tracks": len(desired), "tag": LIKED_TAG}
