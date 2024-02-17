import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Your Spotify API credentials
client_id = '0f57cff8a23d487a88ac66fbc89e1ee3'
client_secret = 'd9ace617384f469a8fa5ad39f2f3b96e'
redirect_uri = 'http://localhost/'
scope = 'user-library-read playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative'

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                               client_secret=client_secret,
                                               redirect_uri=redirect_uri,
                                               scope=scope))

def get_user_playlists():
    """Fetches all user-created playlists, handling pagination."""
    playlists = []
    response = sp.current_user_playlists(limit=50)
    while response:
        playlists.extend(response['items'])
        response = sp.next(response)
    return playlists

def get_playlist_tracks(playlist_id):
    """Fetches all tracks from a given playlist, along with their added_at timestamp, handling pagination."""
    tracks = []
    results = sp.playlist_tracks(playlist_id, fields="items(added_at,track.id),next", limit=100)
    while results:
        tracks.extend([(item['added_at'], item['track']['id']) for item in results['items'] if item['track'] and item['track']['id']])
        results = sp.next(results)
    return tracks

def get_liked_songs():
    """Fetches all liked (saved) songs, along with their added_at timestamp, handling pagination."""
    liked_songs = []
    results = sp.current_user_saved_tracks(limit=50)
    while results:
        liked_songs.extend([(item['added_at'], item['track']['id']) for item in results['items'] if item['track']])
        results = sp.next(results)
    return liked_songs

def add_tracks_to_existing_playlist(playlist_name):
    user_id = sp.me()['id']
    all_tracks = []

    # Include liked songs with their added_at timestamp
    all_tracks.extend(get_liked_songs())

    # Include tracks from user's playlists with their added_at timestamp
    for playlist in get_user_playlists():
        if playlist['owner']['id'] == user_id:  # Ensure only user-owned playlists are considered
            all_tracks.extend(get_playlist_tracks(playlist['id']))

    # Remove duplicates but maintain order by using a dictionary
    unique_tracks_ordered = dict()
    for added_at, track_id in all_tracks:
        if track_id not in unique_tracks_ordered:
            unique_tracks_ordered[track_id] = added_at

    # Sort tracks by their original added_at timestamp in descending order (newer first)
    sorted_tracks = sorted(unique_tracks_ordered.items(), key=lambda x: x[1], reverse=True)

    # Find the existing playlist by name
    existing_playlist_id = None
    playlists = get_user_playlists()
    for playlist in playlists:
        if playlist['name'] == playlist_name and playlist['owner']['id'] == user_id:
            existing_playlist_id = playlist['id']
            break

    if not existing_playlist_id:
        print(f"No existing playlist named '{playlist_name}' found.")
        return

    # Extract just the track IDs, now sorted by their original added_at timestamp in reverse order
    sorted_track_ids = [track_id for track_id, _ in sorted_tracks]

    # Since the Spotify API has a limit on the number of tracks you can add in a single request, chunk the list
    for i in range(0, len(sorted_track_ids), 100):
        chunk = sorted_track_ids[i:i+100]
        sp.playlist_add_items(existing_playlist_id, chunk)

    print(f"Added {len(sorted_track_ids)} unique tracks to the playlist '{playlist_name}' in reverse order (newer first).")

if __name__ == '__main__':
    playlist_name = 'vaulted_'  # Replace with your actual playlist name
    add_tracks_to_existing_playlist(playlist_name)
