import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sys
import time
import itertools

client_id = '0f57cff8a23d487a88ac66fbc89e1ee3'
client_secret = 'd9ace617384f469a8fa5ad39f2f3b96e'
redirect_uri = 'http://localhost/'
scope = 'user-top-read user-library-read playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative'

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                               client_secret=client_secret,
                                               redirect_uri=redirect_uri,
                                               scope=scope))

class ProgressBar:
    """
    A class to display a progress bar with an optional spinner.
    """
    spinner_cycle = itertools.cycle(['|', '/', '-', '\\'])

    def __init__(self, total, prefix='', suffix='', decimals=1, bar_length=50, spinner=True):
        """
        Initializes the ProgressBar.

        :param total: Total iterations (int)
        :param prefix: Prefix string (str)
        :param suffix: Suffix string (str)
        :param decimals: Number of decimals in percent complete (int)
        :param bar_length: Length of the progress bar (int)
        :param spinner: Whether to display a spinner (bool)
        """
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self.bar_length = bar_length
        self.spinner = spinner
        self.iteration = 0

    def update(self, iteration=None):
        """
        Updates the progress bar.

        :param iteration: Current iteration (int). If None, increments by 1.
        """
        if iteration is not None:
            self.iteration = iteration
        else:
            self.iteration += 1

        percent = f"{100 * (self.iteration / float(self.total)):.{self.decimals}f}"
        filled_length = int(round(self.bar_length * self.iteration / float(self.total)))
        bar = '#' * filled_length + '-' * (self.bar_length - filled_length)

        spinner_char = next(self.spinner_cycle) if self.spinner else ''

        sys.stdout.write(f'\r{self.prefix} |{bar}| {percent}% {self.suffix} {spinner_char}')
        sys.stdout.flush()

        if self.iteration >= self.total:
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
    total_playlists = len(playlists)
    fetch_pb = ProgressBar(total=total_playlists, prefix='Fetching Playlists:', suffix='Complete', bar_length=50)
    fetch_pb.update(0)
    for i, playlist in enumerate(playlists, start=1):
        if playlist['owner']['id'] == user_id:
            all_tracks.update(get_playlist_tracks(playlist['id']))
        fetch_pb.update(i)

    print("Fetching Liked Songs:")
    liked_songs = get_liked_songs()
    all_tracks.update(liked_songs)
    print(f"Fetched {len(liked_songs)} liked songs.")

    existing_playlist_id = None
    for playlist in playlists:
        if playlist['name'] == playlist_name and playlist['owner']['id'] == user_id:
            existing_playlist_id = playlist['id']
            break

    if not existing_playlist_id:
        print(f"\nNo existing playlist named '{playlist_name}' found.")
        return

    existing_tracks = set(get_existing_playlist_tracks(existing_playlist_id))
    tracks_to_add = list(all_tracks - existing_tracks)
    total_new_tracks = len(tracks_to_add)

    if total_new_tracks == 0:
        print(f"\nNo new tracks to add to the playlist '{playlist_name}'.")
        return

    update_pb = ProgressBar(total=total_new_tracks, prefix='Updating Playlist:', suffix='Complete', bar_length=50)
    update_pb.update(0)
    for i in range(0, total_new_tracks, 100):
        chunk = tracks_to_add[i:i+100]
        sp.playlist_add_items(existing_playlist_id, chunk)
        update_pb.update(min(i + len(chunk), total_new_tracks))

    print(f"\nSuccessfully added {total_new_tracks} unique tracks to the playlist '{playlist_name}'.")

if __name__ == '__main__':
    playlist_name = '_vaulted'
    add_tracks_to_existing_playlist(playlist_name)
