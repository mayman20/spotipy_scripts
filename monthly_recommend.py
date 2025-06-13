from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from vaulted_add import sp  # assuming sp is initialized in that file


# Spotify auth setup
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope="user-library-read playlist-modify-private playlist-read-private user-top-read"
))

# Step 1: Fetch top 50 tracks
print("Fetching top 50 tracks of the month...")
top_tracks = sp.current_user_top_tracks(time_range='short_term', limit=50)
track_ids = [item['id'] for item in top_tracks['items'] if item['id']]
print(f"Fetched {len(track_ids)} tracks.")

# Step 2: Create/update a temporary playlist
user_id = sp.current_user()['id']
playlist_name = "TEMP - Monthly Top 50"
playlists = sp.current_user_playlists(limit=50)['items']
temp_playlist = next((pl for pl in playlists if pl['name'] == playlist_name), None)

if temp_playlist:
    playlist_id = temp_playlist['id']
    print("Updating existing temp playlist...")
    sp.playlist_replace_items(playlist_id, track_ids)
else:
    print("Creating new temp playlist...")
    new = sp.user_playlist_create(user=user_id, name=playlist_name, public=False)
    playlist_id = new['id']
    sp.playlist_add_items(playlist_id, track_ids)

# Step 3: Use playlist tracks for recommendations
print("Generating recommendations from seed tracks...")
valid_seeds = track_ids[:5]
try:
    recs = sp.recommendations(seed_tracks=valid_seeds, limit=20)
    recommended_ids = [track['id'] for track in recs['tracks'] if track['id']]
except spotipy.SpotifyException as e:
    print(f"⚠️ Failed to get recommendations: {e}")
    recommended_ids = []

# Step 4: Create/update final playlist
month_str = datetime.now().strftime('%B %Y')
final_name = f"Top Monthly Recommended - {month_str}"
existing = next((pl for pl in playlists if pl['name'] == final_name), None)

if existing:
    print(f"Overwriting playlist '{final_name}'...")
    final_id = existing['id']
    sp.playlist_replace_items(final_id, recommended_ids)
else:
    print(f"Creating playlist '{final_name}'...")
    new_playlist = sp.user_playlist_create(user=user_id, name=final_name, public=False)
    final_id = new_playlist['id']
    sp.playlist_add_items(final_id, recommended_ids)

print(f"✅ Done! {len(recommended_ids)} tracks added to '{final_name}'.")
