import requests

STEAM_STORE_APPDETAILS = "https://store.steampowered.com/api/appdetails"

def fetch_app_details(appid: int) -> dict | None:
    """
    Returns a dict with name + genre strings (as tags), or None if not available.
    Uses Steam Store appdetails endpoint.
    """
    r = requests.get(
        STEAM_STORE_APPDETAILS,
        params={"appids": appid},
        timeout=15
    )
    r.raise_for_status()
    data = r.json().get(str(appid), {})
    if not data.get("success"):
        return None

    app = data.get("data", {})
    name = app.get("name")
    genres = app.get("genres", []) or []
    tags = [g.get("description") for g in genres if g.get("description")]

    if not name:
        return None

    return {"appid": appid, "name": name, "tags": tags}
