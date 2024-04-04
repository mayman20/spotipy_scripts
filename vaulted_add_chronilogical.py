import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sys

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

def print_progress(iteration, total, prefix='', suffix='', decimals=1, bar_length=100):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        bar_length  - Optional  : character length of bar (Int)
    """
    format_str = "{0:." + str(decimals) + "f}"
    percent = format_str.format(100 * (iteration / float(total)))
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = '#' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix)),
    sys.stdout.flush()
    if iteration == total:
        sys.stdout.write('\n')
        sys.stdout.flush()

def get_user_playlists():
    playlists = []
    response = sp.current_user_playlists(limit=50)
    while response:
        playlists.extend(response['items'])
        response = sp.next(response) if response['next'] else None
    return playlists

def get_playlist_tracks(playlist_id):
    tracks = []
    results = sp.playlist_tracks(playlist_id, fields="items(track.id),next", limit=100)
    while results:
        tracks.extend([item['track']['id'] for item in results['items'] if item['track'] and item['track']['id']])
        results = sp.next(results) if results['next'] else None
    return tracks

def get_liked_songs():
    liked_songs = []
    results = sp.current_user_saved_tracks(limit=50)
    while results:
        liked_songs.extend([item['track']['id'] for item in results['items'] if item['track']])
        results = sp.next(results) if results['next'] else None
    return liked_songs

def get_existing_playlist_tracks(playlist_id):
    tracks = []
    results = sp.playlist_tracks(playlist_id, fields="items(track.id),next", limit=100)
    while results:
        tracks.extend([item['track']['id'] for item in results['items'] if item['track']])
        results = sp.next(results) if results['next'] else None
    return tracks

def add_tracks_to_existing_playlist(playlist_name):
    user_id = sp.me()['id']
    all_tracks = set()

    playlists = get_user_playlists()
    print_progress(0, len(playlists), prefix='Progress:', suffix='Complete', bar_length=50)
    for i, playlist in enumerate(playlists, start=1):
        if playlist['owner']['id'] == user_id:
            all_tracks.update(get_playlist_tracks(playlist['id']))
        print_progress(i, len(playlists), prefix='Fetching Playlists:', suffix='Complete', bar_length=50)

    liked_songs = get_liked_songs()
    all_tracks.update(liked_songs)

    existing_playlist_id = None
    for playlist in playlists:
        if playlist['name'] == playlist_name and playlist['owner']['id'] == user_id:
            existing_playlist_id = playlist['id']
            break

    if not existing_playlist_id:
        print("\nNo existing playlist named '{}' found.".format(playlist_name))
        return

    existing_tracks = set(get_existing_playlist_tracks(existing_playlist_id))
    tracks_to_add = list(all_tracks - existing_tracks)

    for i in range(0, len(tracks_to_add), 100):
        chunk = tracks_to_add[i:i+100]
        sp.playlist_add_items(existing_playlist_id, chunk)
        print_progress(i + len(chunk), len(tracks_to_add), prefix='Updating Playlist:', suffix='Complete', bar_length=50)

    print("\nSuccessfully added {} unique tracks to the playlist '{}'.".format(len(tracks_to_add), playlist_name))

if __name__ == '__main__':
    playlist_name = 'vaulted_'  # Replace with your actual playlist name
    add_tracks_to_existing_playlist(playlist_name)
