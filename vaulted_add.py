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
    """Fetch all playlists created by the user, handling pagination."""
    playlists = []
    response = sp.current_user_playlists(limit=50)
    playlists.extend(response['items'])
    
    while response['next']:
        response = sp.next(response)
        playlists.extend(response['items'])
        
    return [playlist for playlist in playlists if playlist['owner']['id'] == sp.me()['id']]

def get_playlist_tracks(playlist_id):
    """Fetch all tracks from a given playlist, handling pagination."""
    tracks = []
    results = sp.playlist_tracks(playlist_id, limit=100)
    tracks.extend(results['items'])
    
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
        
    return [item['track']['id'] for item in tracks if item['track'] and item['track']['id']]

def get_liked_songs():
    """Fetch all liked (saved) songs of the user, handling pagination."""
    liked_songs = []
    results = sp.current_user_saved_tracks(limit=50)
    liked_songs.extend(results['items'])
    
    while results['next']:
        results = sp.next(results)
        liked_songs.extend(results['items'])
        
    return [item['track']['id'] for item in liked_songs if item['track']]

def add_tracks_to_existing_playlist(playlist_name):
    user_id = sp.me()['id']
    unique_tracks = set()
    existing_playlist_tracks = set()
    
    # Include liked songs
    unique_tracks.update(get_liked_songs())
    
    # Include tracks from user's playlists
    for playlist in get_user_playlists():
        unique_tracks.update(get_playlist_tracks(playlist['id']))
    
    existing_playlist_id = None
    playlists = get_user_playlists()
    for playlist in playlists:
        if playlist['name'] == playlist_name:
            existing_playlist_id = playlist['id']
            existing_playlist_tracks.update(get_playlist_tracks(existing_playlist_id))
            break
    
    if not existing_playlist_id:
        print(f"No existing playlist named '{playlist_name}' found.")
        return
    
    tracks_to_add = list(unique_tracks - existing_playlist_tracks)
    if not tracks_to_add:
        print(f"All unique tracks are already in the playlist '{playlist_name}'.")
        return
    
    tracks_chunked = [tracks_to_add[i:i + 100] for i in range(0, len(tracks_to_add), 100)]
    for chunk in tracks_chunked:
        try:
            sp.playlist_add_items(existing_playlist_id, chunk)
        except TypeError as e:
            print(f"An error occurred while adding tracks: {e}")
    
    print(f"Added {len(tracks_to_add)} new unique tracks to the existing playlist '{playlist_name}'.")

if __name__ == '__main__':
    playlist_name = 'vaulted'  # Replace with your actual playlist name
    add_tracks_to_existing_playlist(playlist_name)
