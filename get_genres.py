#!/usr/bin/env python3

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sys

client_id = 'YOUR_SPOTIFY_CLIENT_ID'
client_secret = 'YOUR_SPOTIFY_CLIENT_SECRET'
redirect_uri = 'http://localhost:8888/callback'
scope = (
    "playlist-read-private "
    "playlist-read-collaborative "
    "user-library-read"
)

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope
    ),
    requests_timeout=30,
    retries=10,
    status_forcelist=[429, 500, 502, 503, 504],
    backoff_factor=0.3,
)


def get_playlist_by_name(name: str):
    """
    Return the first current-user playlist with the given name, or None if not found.
    """
    offset = 0
    while True:
        response = sp.current_user_playlists(limit=50, offset=offset)
        for playlist in response["items"]:
            if playlist["name"] == name:
                return playlist
        if not response["next"]:
            break
        offset += 50
    return None


def get_all_tracks_from_playlist(playlist_id: str):
    """
    Retrieve all tracks from a playlist, handling pagination.
    Returns a list of playlist-item objects.
    """
    tracks = []
    results = sp.playlist_items(playlist_id, additional_types=["track"])
    tracks.extend(results["items"])

    while results["next"]:
        results = sp.next(results)
        tracks.extend(results["items"])

    return tracks


def gather_all_artist_ids(playlist_items):
    """
    Extracts all unique artist IDs from the given playlist items.
    Returns a list of IDs (strings).
    """
    artist_ids = set()
    for item in playlist_items:
        track = item.get("track")
        if not track:
            continue
        for artist in track.get("artists", []):
            artist_id = artist.get("id")
            if artist_id:
                artist_ids.add(artist_id)
    return list(artist_ids)


def fetch_artists_in_batches(artist_ids):
    """
    Takes a list of artist IDs and fetches their Spotify artist objects in batches (max 50 IDs per request).
    Returns a dict mapping artist_id -> list_of_genres.
    """
    artists_genres = {}
    unique_ids = [aid for aid in set(artist_ids) if aid]

    for i in range(0, len(unique_ids), 50):
        batch = unique_ids[i : i + 50]
        if not batch:
            continue
        result = sp.artists(batch)
        for artist_obj in result["artists"]:
            aid = artist_obj.get("id")
            if aid:
                artists_genres[aid] = artist_obj.get("genres", [])
    return artists_genres


def main():
    classic_playlist = get_playlist_by_name("classic")
    if not classic_playlist:
        print("Error: No playlist named 'classic' found in your account.")
        sys.exit(1)

    print("Fetching tracks from 'classic' playlist...")
    classic_items = get_all_tracks_from_playlist(classic_playlist["id"])
    print(f"  Found {len(classic_items)} playlist items.")

    all_artist_ids = gather_all_artist_ids(classic_items)
    print(f"  Found {len(all_artist_ids)} total artist references.")

    # Fetch artists in batches to get their genres
    print("Fetching artist data in batches...")
    artists_genres = fetch_artists_in_batches(all_artist_ids)
    print(f"  Successfully fetched genres for {len(artists_genres)} artists.")

    #counting how often each genre appears
    genre_count = {}
    for aid, genres in artists_genres.items():
        for g in genres:
            genre_count[g] = genre_count.get(g, 0) + 1

    sorted_genres = sorted(genre_count.items(), key=lambda x: x[1], reverse=True)

    print("\nGenres in the 'classic' playlist (by artist frequency):")
    for genre, count in sorted_genres:
        print(f"{genre}: {count}")

    print("\nDone.")


if __name__ == "__main__":
    main()
