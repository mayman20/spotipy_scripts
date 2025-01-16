import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
import time

# ----------------------- Configuration -----------------------

# Your Spotify API credentials
client_id = '0f57cff8a23d487a88ac66fbc89e1ee3'
client_secret = 'd9ace617384f469a8fa5ad39f2f3b96e'
redirect_uri = 'http://localhost/'
scope = 'user-library-read playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative user-modify-playback-state'

# Name of the target playlist
target_playlist_name = "_vaulted"

# Number of random tracks to add to the queue
number_of_tracks_to_add = 50

# ------------------------------------------------------------

def authenticate_spotify():
    """
    Authenticate with Spotify using Spotipy and return the Spotify client.
    """
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope
    ))
    return sp

def get_target_playlist(sp, playlist_name):
    """
    Retrieve the playlist with the specified name from the user's playlists.
    """
    playlists = []
    results = sp.current_user_playlists(limit=50)
    playlists.extend(results['items'])
    
    while results['next']:
        results = sp.next(results)
        playlists.extend(results['items'])
    
    for playlist in playlists:
        if playlist['name'] == playlist_name:
            return playlist
    return None

def get_all_tracks(sp, playlist_id):
    """
    Retrieve all track URIs from the specified playlist.
    """
    tracks = []
    results = sp.playlist_items(playlist_id, additional_types=['track'], limit=100)
    tracks.extend(results['items'])
    
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    
    track_uris = []
    for item in tracks:
        track = item['track']
        if track and track['uri']:
            track_uris.append(track['uri'])
    return track_uris

def add_tracks_to_queue(sp, track_uris):
    """
    Add the specified track URIs to the user's playback queue.
    """
    for uri in track_uris:
        try:
            sp.add_to_queue(uri)
            print(f"Added {uri} to queue.")
            # To prevent hitting rate limits
            time.sleep(0.5)
        except spotipy.exceptions.SpotifyException as e:
            print(f"Failed to add {uri} to queue: {e}")

def main():
    # Authenticate and create Spotify client
    sp = authenticate_spotify()

    # Get current user's display name
    user = sp.current_user()
    print(f"Authenticated as {user['display_name']}")

    # Retrieve the target playlist
    playlist = get_target_playlist(sp, target_playlist_name)
    if not playlist:
        print(f"Playlist named '{target_playlist_name}' not found.")
        return

    print(f"Found playlist '{playlist['name']}' with ID {playlist['id']}")

    # Get all track URIs from the playlist
    all_track_uris = get_all_tracks(sp, playlist['id'])
    total_tracks = len(all_track_uris)
    print(f"Total tracks in playlist: {total_tracks}")

    if total_tracks == 0:
        print("No tracks found in the playlist.")
        return

    # Determine the number of tracks to add
    tracks_to_add_count = min(number_of_tracks_to_add, total_tracks)

    # Select random tracks
    selected_track_uris = random.sample(all_track_uris, tracks_to_add_count)
    print(f"Selected {tracks_to_add_count} random tracks to add to the queue.")

    # Add selected tracks to the queue
    add_tracks_to_queue(sp, selected_track_uris)
    print("All selected tracks have been added to the queue.")

if __name__ == "__main__":
    main()
