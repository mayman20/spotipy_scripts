# top50_monthly_to_csv.py
"""
Fetch your top 50 monthly Spotify songs and save to CSV.

Output: top_monthly_songs.csv with columns:
- song, artist
- spotify_track_id, spotify_artist_id
- album, release_date, duration_ms, popularity, explicit

Usage:
  1) Export env vars (or put in a .env file with these keys):
     SPOTIPY_CLIENT_ID=...
     SPOTIPY_CLIENT_SECRET=...
     SPOTIPY_REDIRECT_URI=http://localhost:8888/callback

  2) pip install spotipy pandas python-dotenv

  3) python3 top50_monthly_to_csv.py --out top_monthly_songs.csv
     (Optional: --time-range short_term|medium_term|long_term, default short_term)
"""

import os
import logging
import argparse
from typing import List, Dict

import pandas as pd
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)

# ---------- Spotify auth helpers ----------
SCOPE = "user-top-read"

def get_spotify_client() -> spotipy.Spotify:
    load_dotenv()  # reads .env if present
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

    missing = [k for k, v in {
        "SPOTIPY_CLIENT_ID": client_id,
        "SPOTIPY_CLIENT_SECRET": client_secret,
        "SPOTIPY_REDIRECT_URI": redirect_uri
    }.items() if not v]
    if missing:
        raise RuntimeError(
            f"Missing environment variables: {', '.join(missing)}. "
            "Set them in your shell or a .env file."
        )

    auth_mgr = SpotifyOAuth(
        scope=SCOPE,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri
    )
    return spotipy.Spotify(auth_manager=auth_mgr)

# ---------- Data fetch ----------
def fetch_top_tracks(sp: spotipy.Spotify, limit: int = 50, time_range: str = "short_term") -> List[Dict]:
    """
    time_range: 'short_term' (~4 weeks), 'medium_term' (~6 months), 'long_term' (several years)
    """
    logging.info("Fetching top tracks: limit=%d, time_range=%s", limit, time_range)
    resp = sp.current_user_top_tracks(limit=limit, time_range=time_range)
    items = resp.get("items", []) or []
    logging.info("Received %d tracks.", len(items))
    return items

def normalize_tracks(items: List[Dict]) -> pd.DataFrame:
    rows = []
    for t in items:
        # Primary artist only (first in list)
        artist = (t.get("artists") or [{}])[0]
        album = t.get("album") or {}
        rows.append({
            "song": t.get("name"),
            "artist": artist.get("name"),
            "spotify_track_id": t.get("id"),
            "spotify_artist_id": artist.get("id"),
            "album": album.get("name"),
            "release_date": album.get("release_date"),
            "duration_ms": t.get("duration_ms"),
            "popularity": t.get("popularity"),
            "explicit": t.get("explicit"),
        })
    df = pd.DataFrame(rows)
    # Keep just what preprocess will surely need + helpful extras
    # You can drop columns later if you want.
    return df

# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(description="Save top 50 monthly Spotify tracks to CSV.")
    parser.add_argument("--out", default="top_monthly_songs.csv", help="Output CSV path")
    parser.add_argument("--time-range", default="short_term",
                        choices=["short_term", "medium_term", "long_term"],
                        help="short_term ≈ last 4 weeks (default)")
    parser.add_argument("--limit", type=int, default=50, help="How many tracks (max 50)")
    args = parser.parse_args()

    logging.info("🚀 Starting: export top tracks to CSV")
    try:
        sp = get_spotify_client()
    except Exception as e:
        logging.error("Auth error: %s", str(e))
        raise

    items = fetch_top_tracks(sp, limit=min(args.limit, 50), time_range=args.time_range)
    if not items:
        logging.warning("No top tracks found for this time range.")
        # Still write an empty CSV with headers so downstream steps don't crash
        pd.DataFrame(columns=[
            "song","artist","spotify_track_id","spotify_artist_id",
            "album","release_date","duration_ms","popularity","explicit"
        ]).to_csv(args.out, index=False)
        logging.info("Wrote empty CSV with headers to %s", args.out)
        return

    df = normalize_tracks(items)
    df.to_csv(args.out, index=False)
    logging.info("✅ Saved %d rows to %s", len(df), args.out)
    logging.info("Tip: Your preprocess expects columns ['song','artist','text']. "
                 "This file has song/artist + IDs; you can join it with your lyrics dataset later.")

if __name__ == "__main__":
    main()
