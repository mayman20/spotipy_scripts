"""
Script Name: top_monthly_recommendation.py
Author: Assistant
Date: 2025‑08‑02

Purpose
-------
This script uses the Spotipy library to build a personalised Spotify playlist for
the authenticated user.  It performs the following steps:

1. Authenticate the user via Spotify's Authorization Code flow.
2. Fetch the user's top 50 tracks over the last four weeks using the
   `current_user_top_tracks` endpoint.  Spotify's Web API documentation notes
   that the `time_range` parameter accepts `short_term` for approximately the
   last four weeks and allows a maximum of 50 items per request【107126540958127†L290-L351】.
3. For each of those top tracks, request a single recommended track using the
   `/recommendations` endpoint with the top track as the seed.  According to
   Spotify, recommendations can be generated using up to five seeds (artists,
   tracks or genres), and the number of tracks returned is controlled by the
   `limit` parameter【405106581519715†L304-L347】.  Here we supply only one track ID
   per request and set `limit=1` to get exactly one recommendation per seed.
4. Deduplicate any recommended tracks that might repeat across seeds or that
   appear in the user's original top tracks.
5. Create (or optionally find) a playlist named ``Top Monthly Recommendation``
   under the current user's account.  Playlists are created via the
   `user_playlist_create` endpoint; by default new playlists are public, but you
   can specify `public=False` to make them private【303264597445994†L356-L365】.
6. Populate the playlist with the list of recommended tracks.  The
   `playlist_add_items` endpoint allows adding up to 100 items per request,
   which comfortably covers the 50 recommendations.

Usage
-----
1. Install the Spotipy package (if you haven't already) and ensure network
   connectivity:

   .. code-block:: bash

       pip install spotipy

2. Register a Spotify application at https://developer.spotify.com/dashboard/
   and note your client ID, client secret and redirect URI.  Add the redirect
   URI to your application's settings.

3. Set the following environment variables before running the script so
   Spotipy can pick up your credentials automatically:

   .. code-block:: bash

       export SPOTIPY_CLIENT_ID="your‑client‑id"
       export SPOTIPY_CLIENT_SECRET="your‑client‑secret"
       export SPOTIPY_REDIRECT_URI="your‑redirect‑uri"

4. Run the script:

   .. code-block:: bash

       python top_monthly_recommendation.py

   On the first run, Spotipy will open a web browser for you to authenticate
   with your Spotify account and grant the required scopes.  Once authorised,
   an access token will be cached in ``.cache``, so subsequent runs won't need
   to re‑authenticate unless the token expires or the scopes change.

Dependencies
------------
* spotipy >= 2.22 (a lightweight Python wrapper for the Spotify Web API)
* python-dotenv (optional, if you prefer to load credentials from a ``.env`` file)

Required Scopes
---------------
The script requests the following OAuth scopes:

* ``user-top-read`` – required for reading the user's top tracks over a
  specified time range【107126540958127†L290-L351】.
* ``playlist-modify-private`` and ``playlist-modify-public`` – required for
  creating and editing playlists【303264597445994†L356-L365】.

If you set ``public=False`` when creating the playlist, your user must have
authorised ``playlist-modify-private``; if you leave the playlist public, you
need ``playlist-modify-public``.
"""

import os
from typing import List, Set
from pathlib import Path

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
CACHE_PATH = PROJECT_ROOT / ".cache" / "spotipy_general.cache"


def get_top_tracks(sp: spotipy.Spotify, limit: int = 50, time_range: str = "short_term") -> List[dict]:
    """Return the user's top tracks.

    Parameters
    ----------
    sp : spotipy.Spotify
        An authenticated Spotipy client.
    limit : int, optional
        Maximum number of tracks to retrieve (1–50).  Default is 50.
    time_range : str, optional
        Over what time frame the affinities are computed.  Valid values are
        'short_term' (~4 weeks), 'medium_term' (~6 months), or 'long_term'
        (~1 year).  Default is 'short_term'.

    Returns
    -------
    List[dict]
        A list of track objects as returned by the Spotify API.
    """
    # Call the /me/top/tracks endpoint using spotipy's helper.  It returns a
    # dictionary with an 'items' key containing the tracks.  We specify
    # `limit` and `time_range` as per the Web API specification【107126540958127†L290-L351】.
    response = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    return response.get("items", [])


def get_recommendations_for_tracks(sp: spotipy.Spotify, track_ids: List[str]) -> List[str]:
    """Generate one recommendation per seed track.

    For each track in `track_ids`, query the Spotify recommendations endpoint
    using that track ID as the sole seed.  Return a list of unique track URIs
    (prefixed with ``spotify:track:``) recommended across all seeds.

    Parameters
    ----------
    sp : spotipy.Spotify
        An authenticated Spotipy client.
    track_ids : List[str]
        List of Spotify track IDs to use as seeds.

    Returns
    -------
    List[str]
        A list of unique Spotify track URIs for the recommended tracks.
    """
    recommendations: List[str] = []
    seen_ids: Set[str] = set()

    for seed in track_ids:
        # Request a single recommendation for each seed track.  Spotify allows
        # between one and five seed values per request, but here we use one
        # seed and set limit=1.  If a recommendation cannot be generated
        # (e.g. the seed is too obscure), skip gracefully.
        recs = sp.recommendations(seed_tracks=[seed], limit=1)
        for track in recs.get("tracks", []):
            rec_id = track.get("id")
            if rec_id and rec_id not in seen_ids:
                seen_ids.add(rec_id)
                recommendations.append(track.get("uri"))

    return recommendations


def filter_duplicates(source_ids: List[str], recommendations: List[str]) -> List[str]:
    """Remove recommendations that are already in the source list.

    Parameters
    ----------
    source_ids : List[str]
        List of original top track IDs.  Recommendations matching any of these
        IDs will be excluded.
    recommendations : List[str]
        List of recommended track URIs (``spotify:track:...``) to filter.

    Returns
    -------
    List[str]
        Filtered list of recommendation URIs not present in the source IDs.
    """
    source_set: Set[str] = set(source_ids)
    filtered: List[str] = []
    for uri in recommendations:
        # Extract the track ID from the URI by splitting on ':'
        parts = uri.split(":")
        track_id = parts[-1] if parts else uri
        if track_id not in source_set:
            filtered.append(uri)
    return filtered


def create_playlist_if_not_exists(sp: spotipy.Spotify, user_id: str, name: str, description: str = "") -> str:
    """Create a new playlist with the specified name or return the ID if it already exists.

    Parameters
    ----------
    sp : spotipy.Spotify
        An authenticated Spotipy client.
    user_id : str
        The Spotify user ID of the current user.
    name : str
        Desired name of the playlist.
    description : str, optional
        Description of the playlist.

    Returns
    -------
    str
        The Spotify playlist ID.
    """
    # Check if a playlist with the desired name already exists for the user.
    playlists = sp.current_user_playlists(limit=50)
    for playlist in playlists.get("items", []):
        if playlist.get("name") == name:
            return playlist.get("id") or ""

    # Playlist not found; create a new one.  We set public=False for a private
    # playlist.  If you prefer public playlists, set public=True.  See
    # Spotify's create playlist reference for details【303264597445994†L356-L365】.
    new_playlist = sp.user_playlist_create(user_id, name, public=False, description=description)
    return new_playlist.get("id")


def populate_playlist(sp: spotipy.Spotify, playlist_id: str, track_uris: List[str]) -> None:
    """Populate a playlist with the given list of track URIs.

    Parameters
    ----------
    sp : spotipy.Spotify
        An authenticated Spotipy client.
    playlist_id : str
        The Spotify playlist ID to populate.
    track_uris : List[str]
        A list of Spotify track URIs to add to the playlist.
    """
    if not track_uris:
        return
    # Add tracks in batches of 100 (max allowed per request).  Although our
    # default list contains 50 items, batching ensures scalability.
    batch_size = 100
    for i in range(0, len(track_uris), batch_size):
        batch = track_uris[i : i + batch_size]
        sp.playlist_add_items(playlist_id, batch)


def main() -> None:
    # Scopes required for reading top tracks and creating/modifying playlists.
    scope = "user-top-read playlist-modify-private playlist-modify-public"
    load_dotenv(dotenv_path=ENV_PATH)

    # Instantiate the Spotify client using the Authorization Code Flow.  The
    # SpotifyOAuth helper will open a browser window on first run to obtain
    # user consent.  Credentials are taken from environment variables.  If
    # `cache_path` is not provided, Spotipy will default to `.cache` in the
    # current working directory.
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope, cache_path=str(CACHE_PATH)))

    # Get the current user's profile to extract their user ID.  The `me()`
    # endpoint returns a dictionary containing the 'id' field among others.
    user = sp.me()
    user_id = user.get("id")
    if not user_id:
        raise RuntimeError("Unable to determine current user's ID.")

    # Step 1: Fetch the top 50 tracks for the past 4 weeks
    top_tracks = get_top_tracks(sp, limit=50, time_range="short_term")
    track_ids = [track.get("id") for track in top_tracks if track.get("id")]

    # Step 2: Generate one recommendation per top track
    recommended_uris = get_recommendations_for_tracks(sp, track_ids)

    # Step 3: Remove any duplicate recommendations or songs already in the top list
    cleaned_uris = filter_duplicates(track_ids, recommended_uris)

    # Step 4: Create (or retrieve) the target playlist
    playlist_name = "Top Monthly Recommendation"
    playlist_description = "Recommendations based on your top tracks from the past month."
    playlist_id = create_playlist_if_not_exists(sp, user_id, playlist_name, description=playlist_description)
    if not playlist_id:
        raise RuntimeError("Failed to create or retrieve playlist.")

    # Step 5: Populate the playlist with the recommended tracks
    populate_playlist(sp, playlist_id, cleaned_uris)

    print(f"Created/updated playlist '{playlist_name}' with {len(cleaned_uris)} recommended tracks.")


if __name__ == "__main__":
    main()
