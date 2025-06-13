import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sys
import time

client_id = '0f57cff8a23d487a88ac66fbc89e1ee3'
client_secret = 'd9ace617384f469a8fa5ad39f2f3b96e'
redirect_uri = 'http://localhost/'

# Permissions needed
scope = (
    "user-library-read "
    "playlist-modify-public "
    "playlist-modify-private "
    "playlist-read-private "
    "playlist-read-collaborative"
)

# Set up Spotify client with retries and timeout
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

# List of rock-related genres we are interested in
DESIRED_ROCK_GENRES = [
    'classic rock',
    'blues rock',
    'rock',
    'psychedelic rock',
    'folk rock',
    'acid rock',
    'hard rock',
    'art rock',
    'soft rock',
    'progressive rock',
    'grunge',
    'symphonic rock',
    'country rock',
    'funk rock'
]

# Find a playlist by its name
def get_playlist_by_name(name):
    playlists = []
    offset = 0
    while True:
        response = sp.current_user_playlists(limit=50, offset=offset)
        playlists.extend(response['items'])
        if not response['next']:
            break
        offset += 50
    
    for playlist in playlists:
        if playlist['name'] == name:
            return playlist
    return None

# Get all tracks from a given playlist
def get_all_tracks_from_playlist(playlist_id):
    tracks = []
    results = sp.playlist_items(playlist_id, additional_types=['track'])
    tracks.extend(results['items'])
    
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    
    return tracks

# Collect all artist IDs from playlist tracks
def gather_all_artist_ids(playlist_items):
    artist_ids = set()
    for item in playlist_items:
        track = item.get('track') or {}
        for artist in track.get('artists', []):
            aid = artist.get('id')
            if aid is not None and aid.strip() != '':
                artist_ids.add(aid)
    return list(artist_ids)

# Fetch genres for a list of artist IDs in batches
def fetch_artists_in_batches(artist_ids):
    artists_genres = {}
    unique_ids = {aid for aid in artist_ids if aid and aid.strip() != ''}

    id_list = list(unique_ids)
    for i in range(0, len(id_list), 50):
        batch = id_list[i:i+50]
        batch = [a for a in batch if a and a.strip() != '']
        if not batch:
            continue

        results = sp.artists(batch)
        for artist_obj in results['artists']:
            aid = artist_obj.get('id')
            if aid:
                artists_genres[aid] = artist_obj.get('genres', [])
    return artists_genres

# Check if a track is rock (by genre and release year)
def is_desired_rock_genre(track_item, artists_genres):
    track = track_item.get('track')
    if not track:
        return False

    album = track.get('album', {})
    release_date = album.get('release_date', '')
    if not release_date:
        return False
    try:
        year = int(release_date.split('-')[0])
    except ValueError:
        return False
    
    if year < 1960 or year >= 2000:
        return False

    for artist in track.get('artists', []):
        aid = artist.get('id')
        if not aid:
            continue
        artist_genres = artists_genres.get(aid, [])
        for g in artist_genres:
            glower = g.lower()
            if any(subgenre in glower for subgenre in DESIRED_ROCK_GENRES):
                return True

    return False

# Main program flow
def main():
    vaulted_playlist = get_playlist_by_name("_vaulted")
    if not vaulted_playlist:
        print("Error: Playlist '_vaulted' not found.")
        sys.exit(1)

    classic_playlist = get_playlist_by_name("_Classic")
    if not classic_playlist:
        print("Error: Playlist '_Classic' not found.")
        sys.exit(1)

    print("Fetching tracks from '_vaulted'...")
    vaulted_items = get_all_tracks_from_playlist(vaulted_playlist['id'])

    print("Fetching tracks from '_Classic' to avoid duplicates...")
    classic_items = get_all_tracks_from_playlist(classic_playlist['id'])
    classic_track_ids = set()
    for item in classic_items:
        track_obj = item.get('track')
        if track_obj and track_obj.get('id'):
            classic_track_ids.add(track_obj['id'])

    print("Gathering artist IDs from '_vaulted'...")
    vaulted_artist_ids = gather_all_artist_ids(vaulted_items)
    print(f"Found {len(vaulted_artist_ids)} unique artist IDs in '_vaulted'.")

    print("Fetching artist genres in batches...")
    artists_genres = fetch_artists_in_batches(vaulted_artist_ids)
    print(f"Successfully fetched genres for {len(artists_genres)} artists.")

    print("Checking which tracks qualify as desired rock (60s–90s, subgenres) ...")
    tracks_to_add = []
    for item in vaulted_items:
        track_obj = item.get('track')
        if not track_obj:
            continue

        track_id = track_obj.get('id')
        if not track_id:
            continue

        if track_id in classic_track_ids:
            continue

        if is_desired_rock_genre(item, artists_genres):
            tracks_to_add.append(track_id)

    print(f"Found {len(tracks_to_add)} new tracks to add to '_Classic'.")

    for i in range(0, len(tracks_to_add), 100):
        batch = tracks_to_add[i:i+100]
        sp.playlist_add_items(classic_playlist['id'], batch)
        print(f"Added {len(batch)} tracks to '_Classic'.")
        time.sleep(1)

    print("Done!")

if __name__ == "__main__":
    main()
