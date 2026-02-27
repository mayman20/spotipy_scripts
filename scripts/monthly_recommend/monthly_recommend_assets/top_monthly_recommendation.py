#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Monthly 'Discover-like' builder (no /recommendations dependency):

- Seeds = your top tracks (short & medium term).
- Primary path: Spotify /v1/recommendations (if it works for you).
- Fallback (when recs 404): Per-seed audio-similarity:
    • build a small candidate pool around the *song* (same artist deep cuts + related artists' album cuts)
    • fetch audio features and rank by distance to the seed song
    • take only a couple per seed to preserve variety
- Always dedup + enforce strict caps (total and per-artist).
- Gentle 429 backoff.
"""

import os
import sys
import time
import math
import random
import logging
from datetime import datetime
from typing import Iterable, List, Dict, Set, Tuple

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
from dotenv import load_dotenv

# =================== TUNABLES ===================

PLAYLIST_NAME_PREFIX = "Monthly Recs"
TARGET_ADD_COUNT     = 30   # strict maximum new tracks per run
SEEDS_PER_RECS_CALL  = 4    # up to 5 allowed by API; we use 4
RECS_PER_CALL        = 10   # 1..100
PER_SEED_TAKE        = 2    # fallback: take at most N similar tracks per seed
MAX_PER_ARTIST_TOTAL = 2    # never add more than this many from the same artist overall
MARKET               = "US" # fixed country for stable behavior

LOG_LEVEL            = logging.INFO

# Audio feature weighting for distance calc (fallback)
FEATURE_WEIGHTS = {
    "danceability":     1.0,
    "energy":           1.0,
    "valence":          1.0,
    "acousticness":     0.8,
    "instrumentalness": 0.7,
    "liveness":         0.6,
    "speechiness":      0.5,
    "tempo":            0.6,   # scaled to ~0..1
    "loudness":         0.6,   # mapped to 0..1
}

# Candidate pool sizing (fallback)
CANDIDATES_SAME_ARTIST_ALBUMS  = 2   # #albums from the seed's main artist to sample
CANDIDATES_SAME_ARTIST_TRACKS  = 8   # total tracks sampled from those albums
CANDIDATES_RELATED_ARTISTS     = 6   # #related artists to sample
CANDIDATES_RELATED_ALBUMS_EACH = 1   # #albums to sample per related artist
CANDIDATES_RELATED_TRACKS_EACH = 6   # #tracks to sample per related artist

# Popularity window to keep results fresh but not all mega-hits
POPULARITY_MIN = 10
POPULARITY_MAX = 75

# =================== LOGGING ===================

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("monthly_discover_like")

# =================== UTILS ===================

def chunked(seq: Iterable, size: int):
    buf = []
    for item in seq:
        buf.append(item)
        if len(buf) == size:
            yield buf
            buf = []
    if buf:
        yield buf

def sleep_backoff(seconds: int):
    time.sleep(max(1, seconds))

def sp_call(fn, *args, **kwargs):
    """Spotipy call wrapper with 429 retry."""
    retries = 5
    while True:
        try:
            return fn(*args, **kwargs)
        except SpotifyException as e:
            if e.http_status == 429:
                retry_after = 1
                try:
                    retry_after = int(getattr(e, "headers", {}).get("Retry-After", 1))
                except Exception:
                    pass
                log.warning("Rate limit. Retrying after: %s", retry_after)
                sleep_backoff(retry_after + 1)
                retries -= 1
                if retries <= 0:
                    raise
                continue
            raise

def normalized_features_row(feat: Dict) -> Dict:
    """
    Map audio features to ~0..1. None-safe.
    """
    if not feat:
        return {}
    out = {}
    out["danceability"]     = feat.get("danceability")
    out["energy"]           = feat.get("energy")
    out["valence"]          = feat.get("valence")
    out["acousticness"]     = feat.get("acousticness")
    out["instrumentalness"] = feat.get("instrumentalness")
    out["liveness"]         = feat.get("liveness")
    out["speechiness"]      = feat.get("speechiness")
    # Tempo approx 0..200; clamp then scale
    tempo = feat.get("tempo")
    if tempo is not None:
        tempo = max(0.0, min(210.0, float(tempo)))
        out["tempo"] = tempo / 210.0
    else:
        out["tempo"] = None
    # Loudness typically -60..0 dB; map to 0..1
    loud = feat.get("loudness")
    if loud is not None:
        loud = max(-60.0, min(0.0, float(loud)))
        out["loudness"] = (loud + 60.0) / 60.0
    else:
        out["loudness"] = None
    return out

def feature_distance(a: Dict, b: Dict) -> float:
    """
    Weighted L2 distance over shared features.
    """
    s = 0.0
    wsum = 0.0
    for k, w in FEATURE_WEIGHTS.items():
        va = a.get(k)
        vb = b.get(k)
        if va is None or vb is None:
            continue
        d = (va - vb)
        s += w * (d * d)
        wsum += w
    if wsum <= 0:
        return float("inf")
    return math.sqrt(s / wsum)

# =================== CLIENT ===================

def get_spotify_client() -> spotipy.Spotify:
    load_dotenv()
    sp = spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            scope="user-top-read user-library-read playlist-modify-private playlist-modify-public",
            open_browser=False,
        )
    )
    return sp

def current_user_id(sp: spotipy.Spotify) -> str:
    return sp_call(sp.me)["id"]

# =================== SEEDS ===================

def gather_seed_tracks(sp: spotipy.Spotify) -> List[Dict]:
    seeds = []
    for tr in ("short_term", "medium_term"):
        res = sp_call(sp.current_user_top_tracks, time_range=tr, limit=50)
        items = res.get("items", [])
        log.info("Seeds gathered from %s → %d tracks", tr, len(items))
        seeds.extend(items)
    # Dedup by id, preserve order
    seen: Set[str] = set()
    unique = []
    for t in seeds:
        tid = t.get("id")
        if tid and tid not in seen:
            unique.append(t)
            seen.add(tid)
    log.info("Total unique seeds: %d", len(unique))
    return unique

# =================== PLAYLIST HELPERS ===================

def get_or_create_playlist(sp: spotipy.Spotify, user_id: str, name: str) -> str:
    res = sp_call(sp.current_user_playlists, limit=50)
    while True:
        for pl in res.get("items", []):
            if pl.get("name") == name:
                log.info("Using existing playlist '%s' (%s)", name, pl["id"])
                return pl["id"]
        nxt = res.get("next")
        if not nxt:
            break
        res = sp_call(sp.next, res)
    # create
    pl = sp_call(sp.user_playlist_create, user=user_id, name=name, public=False,
                 description="Auto-curated monthly discover-like picks.")
    log.info("Created playlist '%s' (%s)", name, pl["id"])
    return pl["id"]

def get_playlist_track_ids(sp: spotipy.Spotify, playlist_id: str) -> Set[str]:
    ids: Set[str] = set()
    fields = "items.track.id,items.track.uri,next"
    res = sp_call(sp.playlist_items, playlist_id=playlist_id, fields=fields, additional_types=["track"], limit=100)
    while True:
        for it in res.get("items", []):
            tr = it.get("track") or {}
            tid = tr.get("id")
            if tid:
                ids.add(tid)
        nxt = res.get("next")
        if not nxt:
            break
        res = sp_call(sp.next, res)
    return ids

def add_tracks(sp: spotipy.Spotify, playlist_id: str, track_ids: List[str]):
    uris = [f"spotify:track:{tid}" for tid in track_ids]
    for chunk in chunked(uris, 100):
        sp_call(sp.playlist_add_items, playlist_id, chunk)

# =================== PRIMARY PATH: /recommendations ===================

def try_recommendations(sp: spotipy.Spotify, seed_track_ids: List[str]) -> Tuple[bool, List[str]]:
    """
    Try /v1/recommendations. Returns (endpoint_ok, track_ids).
    endpoint_ok=False means we saw a 404 and should stop calling it.
    """
    try:
        recs = sp_call(
            sp.recommendations,
            seed_tracks=seed_track_ids,
            limit=RECS_PER_CALL,
            market=MARKET,
        )
        items = recs.get("tracks", []) or []
        return True, [t["id"] for t in items if t.get("id")]
    except SpotifyException as e:
        if e.http_status == 404:
            log.error("recommendations 404 for seeds=%s → disabling recs and using audio-similarity fallback.",
                      seed_track_ids)
            return False, []
        log.warning("recommendations error (status=%s) for seeds=%s: %s",
                    e.http_status, seed_track_ids, e.msg)
        # treat as soft failure; endpoint still exists
        return True, []

# =================== FALLBACK: AUDIO-SIMILARITY ===================

def pick_album_track_ids(sp: spotipy.Spotify, album_id: str, max_tracks: int) -> List[str]:
    tracks = []
    res = sp_call(sp.album_tracks, album_id=album_id, limit=50)
    items = res.get("items", []) or []
    for it in items:
        tid = it.get("id")
        if tid:
            tracks.append(tid)
    random.shuffle(tracks)
    return tracks[:max_tracks]

def build_candidate_pool(sp: spotipy.Spotify, seed_track_id: str) -> List[str]:
    """
    Build a *small* pool of candidates AROUND THE SONG (not just artist hits):
    - deep cuts from the seed's main artist (from a couple of albums)
    - a few tracks from related artists' albums
    """
    try:
        seed_track = sp_call(sp.track, seed_track_id)
    except SpotifyException:
        return []

    main_artist = (seed_track.get("artists") or [{}])[0]
    main_artist_id = main_artist.get("id")
    pool: List[str] = []

    # 1) Same artist, a couple of albums → album cuts
    if main_artist_id:
        albums = []
        res = sp_call(sp.artist_albums, main_artist_id, include_groups="album,single", country=MARKET, limit=50)
        albums.extend(res.get("items", []))
        # Favor most recent, then randomize a little
        albums.sort(key=lambda a: a.get("release_date", ""), reverse=True)
        if len(albums) > CANDIDATES_SAME_ARTIST_ALBUMS:
            albums = albums[:CANDIDATES_SAME_ARTIST_ALBUMS + 2]
            random.shuffle(albums)
            albums = albums[:CANDIDATES_SAME_ARTIST_ALBUMS]
        for alb in albums:
            pool.extend(pick_album_track_ids(sp, alb["id"], max_tracks=CANDIDATES_SAME_ARTIST_TRACKS // max(1, len(albums))))

    # 2) Related artists → pick one album and sample a few tracks each
    related = []
    if main_artist_id:
        try:
            rel = sp_call(sp.artist_related_artists, main_artist_id)
            related = rel.get("artists", []) or []
        except SpotifyException:
            related = []
    random.shuffle(related)
    related = related[:CANDIDATES_RELATED_ARTISTS]

    for ra in related:
        aid = ra.get("id")
        if not aid:
            continue
        try:
            r_albums = sp_call(sp.artist_albums, aid, include_groups="album,single", country=MARKET, limit=20)
            items = r_albums.get("items", []) or []
            if not items:
                continue
            # bias toward recent albums
            items.sort(key=lambda a: a.get("release_date", ""), reverse=True)
            items = items[:max(1, CANDIDATES_RELATED_ALBUMS_EACH * 2)]
            random.shuffle(items)
            items = items[:CANDIDATES_RELATED_ALBUMS_EACH]
            for alb in items:
                pool.extend(pick_album_track_ids(sp, alb["id"], max_tracks=CANDIDATES_RELATED_TRACKS_EACH))
        except SpotifyException:
            continue

    # Dedup and drop the seed itself
    uniq: List[str] = []
    seen: Set[str] = set([seed_track_id])
    for tid in pool:
        if tid and tid not in seen:
            uniq.append(tid)
            seen.add(tid)
    return uniq

def fetch_features_map(sp: spotipy.Spotify, track_ids: List[str]) -> Dict[str, Dict]:
    feats: Dict[str, Dict] = {}
    for chunk in chunked(track_ids, 100):
        arr = sp_call(sp.audio_features, chunk) or []
        for tfeat in arr:
            if not tfeat:
                continue
            tid = tfeat.get("id")
            if not tid:
                continue
            feats[tid] = normalized_features_row(tfeat)
    return feats

def filter_candidates_metadata(sp: spotipy.Spotify, track_ids: List[str]) -> Dict[str, Dict]:
    """
    Fetch small metadata so we can filter by popularity and count per-artist.
    """
    meta: Dict[str, Dict] = {}
    for chunk in chunked(track_ids, 50):
        res = sp_call(sp.tracks, chunk) or {}
        for t in (res.get("tracks") or []):
            tid = t.get("id")
            if tid:
                meta[tid] = {
                    "popularity": t.get("popularity", 0),
                    "artists": [a.get("id") for a in (t.get("artists") or []) if a.get("id")],
                }
    return meta

def audio_similarity_fallback(sp: spotipy.Spotify,
                              seed_track_id: str,
                              existing_ids: Set[str],
                              already_picked: List[str],
                              artist_counts: Dict[str, int]) -> List[str]:
    """
    For one seed track, return up to PER_SEED_TAKE candidate IDs ranked by audio similarity.
    """
    pool = build_candidate_pool(sp, seed_track_id)
    if not pool:
        log.info("    no pool for seed %s", seed_track_id)
        return []

    # Filter out what's already in playlist or already chosen
    pool = [tid for tid in pool if tid not in existing_ids and tid not in already_picked]

    if not pool:
        return []

    # Features
    seed_feat_list = sp_call(sp.audio_features, [seed_track_id]) or [None]
    seed_feat = normalized_features_row(seed_feat_list[0] if seed_feat_list else None)
    if not seed_feat:
        return []

    feats_map = fetch_features_map(sp, pool)
    if not feats_map:
        return []

    # Metadata (popularity + artists)
    meta = filter_candidates_metadata(sp, list(feats_map.keys()))

    # Score and rank
    scored: List[Tuple[float, str]] = []
    for tid, f in feats_map.items():
        # Popularity filter
        pop = meta.get(tid, {}).get("popularity", 0)
        if pop < POPULARITY_MIN or pop > POPULARITY_MAX:
            continue
        dist = feature_distance(seed_feat, f)
        if math.isfinite(dist):
            scored.append((dist, tid))

    scored.sort(key=lambda x: x[0])  # smaller distance is better

    # Respect per-artist total cap
    picks: List[str] = []
    for _, tid in scored:
        if len(picks) >= PER_SEED_TAKE:
            break
        art_ids = meta.get(tid, {}).get("artists", []) or []
        # Allow if all artists are under the cap
        if all(artist_counts.get(aid, 0) < MAX_PER_ARTIST_TOTAL for aid in art_ids):
            picks.append(tid)
            for aid in art_ids:
                artist_counts[aid] = artist_counts.get(aid, 0) + 1

    return picks

# =================== LIBRARY FILTER ===================

def filter_new(sp: spotipy.Spotify,
               track_ids: List[str],
               existing_in_playlist: Set[str],
               seen: Set[str]) -> List[str]:
    # Remove already in playlist or already chosen this run
    track_ids = [tid for tid in track_ids if tid not in existing_in_playlist and tid not in seen]

    # Try to remove already-saved library tracks (best-effort)
    pruned: List[str] = []
    for chunk in chunked(track_ids, 50):
        try:
            contains = sp_call(sp.current_user_saved_tracks_contains, chunk)
        except SpotifyException:
            # If scope not granted, skip this filter
            pruned.extend(chunk)
            continue
        for tid, have in zip(chunk, contains):
            if not have:
                pruned.append(tid)
    return pruned

# =================== MAIN ===================

def main():
    sp = get_spotify_client()
    user_id = current_user_id(sp)
    playlist_name = f"{PLAYLIST_NAME_PREFIX} {datetime.now():%Y-%m}"
    playlist_id = get_or_create_playlist(sp, user_id, playlist_name)

    existing = get_playlist_track_ids(sp, playlist_id)
    log.info("Existing tracks in '%s': %d", playlist_name, len(existing))

    seeds = gather_seed_tracks(sp)
    if not seeds:
        log.warning("No seeds available; nothing to do.")
        return

    seed_ids = [t["id"] for t in seeds if t.get("id")]
    random.shuffle(seed_ids)

    added: List[str] = []
    seen_global: Set[str] = set()
    artist_counts: Dict[str, int] = {}
    recs_endpoint_hard_404 = False

    for i, batch in enumerate(chunked(seed_ids, SEEDS_PER_RECS_CALL), start=1):
        if len(added) >= TARGET_ADD_COUNT:
            break

        log.info("[BATCH %d] seeds=%s", i, ", ".join(batch))

        # ---- primary path
        rec_ids: List[str] = []
        if not recs_endpoint_hard_404:
            ok, rec_ids = try_recommendations(sp, batch)
            if not ok:
                recs_endpoint_hard_404 = True

        candidates: List[str] = []
        if rec_ids:
            candidates = rec_ids
        else:
            # ---- strictly per-seed audio similarity (NOT artist top tracks)
            per_seed_take = max(1, min(PER_SEED_TAKE, TARGET_ADD_COUNT - len(added)))
            for sid in batch:
                if len(added) >= TARGET_ADD_COUNT:
                    break
                picks = audio_similarity_fallback(
                    sp, sid, existing_ids=existing,
                    already_picked=added, artist_counts=artist_counts
                )
                if per_seed_take < len(picks):
                    picks = picks[:per_seed_take]
                candidates.extend(picks)

        if not candidates:
            log.info("  → no candidates from this batch.")
            continue

        # Final filtering + strict cap
        fresh = filter_new(sp, candidates, existing, seen_global | set(added))
        if not fresh:
            log.info("  → nothing new after filtering.")
            continue

        space_left = TARGET_ADD_COUNT - len(added)
        take = fresh[:max(0, space_left)]
        if take:
            add_tracks(sp, playlist_id, take)
            added.extend(take)
            log.info("  → added %d (total=%d/%d)", len(take), len(added), TARGET_ADD_COUNT)

    log.info("Done! Playlist '%s' updated with %d new tracks.", playlist_name, len(added))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.warning("Aborted by user.")
        sys.exit(130)
