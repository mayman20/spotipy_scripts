import spotipy
from spotipy.oauth2 import SpotifyOAuth
import random
import time



client_id = '0f57cff8a23d487a88ac66fbc89e1ee3'
client_secret = 'd9ace617384f469a8fa5ad39f2f3b96e'
redirect_uri = 'http://localhost/'
scope = 'user-library-read playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative user-modify-playback-state'

target_playlist_name = "_vaulted"

number_of_tracks_to_add = 50


def authenticate_spotify():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope
    ))
    return sp

def get_target_playlist(sp, playlist_name):
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
    for uri in track_uris:
        try:
            sp.add_to_queue(uri)
            print(f"Added {uri} to queue.")
            time.sleep(0.5)
        except spotipy.exceptions.SpotifyException as e:
            print(f"Failed to add {uri} to queue: {e}")

def main():
    sp = authenticate_spotify()

    user = sp.current_user()
    print(f"Authenticated as {user['display_name']}")

    playlist = get_target_playlist(sp, target_playlist_name)
    if not playlist:
        print(f"Playlist named '{target_playlist_name}' not found.")
        return

    print(f"Found playlist '{playlist['name']}' with ID {playlist['id']}")


    all_track_uris = get_all_tracks(sp, playlist['id'])
    total_tracks = len(all_track_uris)
    print(f"Total tracks in playlist: {total_tracks}")

    if total_tracks == 0:
        print("No tracks found in the playlist.")
        return

    tracks_to_add_count = min(number_of_tracks_to_add, total_tracks)

    selected_track_uris = random.sample(all_track_uris, tracks_to_add_count)
    print(f"Selected {tracks_to_add_count} random tracks to add to the queue.")

    add_tracks_to_queue(sp, selected_track_uris)
    print("All selected tracks have been added to the queue.")

if __name__ == "__main__":
    main()
