from dotenv import load_dotenv
import os
import base64
import json
from requests import post, get

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

def get_token(client_id, client_secret):
    auth_string = client_id + ':' + client_secret
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {"grant_type": "client_credentials"}
    results = post(url, headers=headers, data=data)
    json_result = json.loads(results.content)

    if "access_token" not in json_result:
        print("failed to get token")
        return None
    token = json_result["access_token"]

    return token

def get_auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def search_for_song(song_title, artist=None):
    base_url = "https://api.spotify.com/v1/search"

    if not artist == None:
        q = "track:" + song_title + " artist:" + artist
    else:
        q = "track:" + song_title

    params = {
        "q": q,
        "type": "track",
        "limit": 10,
        "market": "ZA"
    }
    token = get_token(client_id, client_secret)
    headers = get_auth_header(token)

    # Pass params as a separate argument, NOT baked into the URL
    result = get(base_url, headers=headers, params=params)
    data = result.json()

    if result.status_code != 200:
        print("Error: ", data)
        return None

    items = data.get("tracks", {}).get("items")

    if not items:
        print("No song found")
        return None

    return items

token = get_token(client_id, client_secret)
