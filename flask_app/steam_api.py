import os
import re
import requests

STEAM_API_BASE = "https://api.steampowered.com"

def _get_key() -> str:
    key = os.getenv("STEAM_API_KEY")
    if not key:
        raise RuntimeError("STEAM_API_KEY is not set in .env")
    return key

def resolve_to_steamid64(user_input: str) -> str:
    """
    Accepts:
      - 17-digit SteamID64
      - vanity name (e.g., 'gaben')
      - profile URL (https://steamcommunity.com/id/<vanity>/ or /profiles/<steamid64>/)
    Returns SteamID64 as a string.
    """
    s = user_input.strip()

    # If they pasted a full URL, extract the interesting part
    m = re.search(r"steamcommunity\.com/(id|profiles)/([^/]+)/?", s)
    if m:
        kind, value = m.group(1), m.group(2)
        if kind == "profiles":
            return value  # already SteamID64
        s = value        # vanity -> resolve

    # If it's already 17 digits, treat as SteamID64
    if re.fullmatch(r"\d{17}", s):
        return s

    # Otherwise assume vanity and resolve
    url = f"{STEAM_API_BASE}/ISteamUser/ResolveVanityURL/v1/"
    params = {"key": _get_key(), "vanityurl": s}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json().get("response", {})

    # success = 1 means resolved
    if data.get("success") == 1 and data.get("steamid"):
        return data["steamid"]

    raise ValueError("Could not resolve that Steam ID / vanity URL. Try your full profile link or SteamID64.")

def get_owned_games(steamid64: str) -> list[dict]:
    url = f"{STEAM_API_BASE}/IPlayerService/GetOwnedGames/v1/"
    params = {
        "key": _get_key(),
        "steamid": steamid64,
        "include_appinfo": 1,
        "include_played_free_games": 1,
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("response", {}).get("games", [])
