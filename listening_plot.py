import spotipy
from spotipy.oauth2 import SpotifyOAuth
import matplotlib.pyplot as plt
import collections
import sys

client_id = '0f57cff8a23d487a88ac66fbc89e1ee3'
client_secret = 'd9ace617384f469a8fa5ad39f2f3b96e'
redirect_uri = 'http://localhost/'
scope = "user-library-read"

# Set up Spotify client
sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope
    )
)

# Get all saved tracks
def get_saved_tracks():
    tracks = []
    offset = 0
    while True:
        results = sp.current_user_saved_tracks(limit=50, offset=offset)
        tracks.extend(results['items'])
        if not results['next']:
            break
        offset += 50
    return tracks

# Gather release years and artist IDs
def extract_years_and_artists(tracks):
    years = []
    artist_ids = set()
    for item in tracks:
        track = item.get('track', {})
        album = track.get('album', {})
        release_date = album.get('release_date', '')
        if release_date:
            try:
                year = int(release_date.split('-')[0])
                if year >= 1900:
                    years.append(year)
            except ValueError:
                continue
        for artist in track.get('artists', []):
            aid = artist.get('id')
            if aid:
                artist_ids.add(aid)
    return years, list(artist_ids)

# Fetch artist genres
def fetch_artist_genres(artist_ids):
    genres = collections.Counter()
    for i in range(0, len(artist_ids), 50):
        batch = artist_ids[i:i+50]
        results = sp.artists(batch)
        for artist_obj in results['artists']:
            artist_genres = artist_obj.get('genres', [])
            genres.update(artist_genres)
    return genres

# Plot the timeline
def plot_year_distribution(years):
    year_counts = collections.Counter(years)
    years_sorted = sorted(year_counts.items())

    x = [y for y, _ in years_sorted]
    y = [c for _, c in years_sorted]

    plt.figure(figsize=(10,6))
    plt.plot(x, y, marker='o')
    plt.title('Your Listening Timeline (by Track Release Year)')
    plt.xlabel('Release Year')
    plt.ylabel('Number of Tracks')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# Main
def main():
    print("Fetching saved tracks...")
    tracks = get_saved_tracks()

    print(f"Fetched {len(tracks)} tracks.")

    print("Extracting release years and artist IDs...")
    years, artist_ids = extract_years_and_artists(tracks)

    if not years:
        print("No release years found.")
        sys.exit(1)

    print("Fetching genres from artists...")
    genres = fetch_artist_genres(artist_ids)

    print(f"Top genres:")
    for genre, count in genres.most_common(10):
        print(f"{genre}: {count}")

    print("Plotting timeline...")
    plot_year_distribution(years)

if __name__ == "__main__":
    main()
