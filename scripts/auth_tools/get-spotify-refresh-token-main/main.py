import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import dotenv_values

config = dotenv_values(".env")

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id="0f57cff8a23d487a88ac66fbc89e1ee3",
        client_secret="d9ace617384f469a8fa5ad39f2f3b96e",
        redirect_uri="http://localhost/",
        scope="playlist-modify-private",
    )
)

current_user = sp.current_user()

assert current_user is not None

print(current_user["id"], "token saved in '.cache' file.")
