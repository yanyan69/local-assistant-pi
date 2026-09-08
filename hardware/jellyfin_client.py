import json
import os
import random
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional
from core.app_config import JELLYFIN_TOKEN, JELLYFIN_URL


class JellyfinClient:
    """Small allowlisted Jellyfin client for local media playback control."""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, timeout: int = 5):
        self.base_url = (base_url or JELLYFIN_URL).strip().rstrip("/")
        self.token = (token or JELLYFIN_TOKEN).strip()
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        if not path.startswith("/") or ".." in path:
            raise ValueError("Invalid Jellyfin API path")
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(url, data=body, method=method)
        request.add_header("Accept", "application/json")
        request.add_header("X-Emby-Token", self.token)
        if body is not None:
            request.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}

    def _session(self) -> Optional[Dict[str, Any]]:
        sessions = self._request("GET", "/Sessions")
        candidates = [
            session for session in sessions
            if session.get("Id")
            and session.get("SupportsRemoteControl", False)
            and session.get("DeviceId")
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda session: bool(session.get("NowPlayingItem")), reverse=True)
        return candidates[0]

    def search(self, query: str = "") -> List[Dict[str, Any]]:
        params = {
            "Recursive": "true",
            "IncludeItemTypes": "Audio,Movie,Episode",
            "Limit": "25",
            "SearchTerm": query.strip(),
        }
        path = "/Items?" + urllib.parse.urlencode(params)
        return self._request("GET", path).get("Items", [])

    def play(self, query: str = "") -> str:
        session = self._session()
        if not session:
            return "No controllable Jellyfin phone or laptop session is connected. Open Jellyfin on the device first."
        items = self.search(query)
        audio_items = [item for item in items if item.get("Type") == "Audio"]
        selected = random.choice(audio_items) if not query.strip() and audio_items else (items[0] if items else None)
        if not selected:
            return f"I could not find media matching '{query.strip()}'." if query.strip() else "No media was found in Jellyfin."
        self._request("POST", f"/Sessions/{urllib.parse.quote(session['Id'], safe='')}/Playing", {
            "ItemIds": [selected["Id"]],
            "PlayCommand": "PlayNow",
        })
        return f"Playing {selected.get('Name', 'the selected media')} on {session.get('DeviceName', 'your connected device')}."

    def command(self, command: str) -> str:
        session = self._session()
        if not session:
            return "No controllable Jellyfin phone or laptop session is connected. Open Jellyfin on the device first."
        endpoint = {
            "MUSIC_STOP": "Stop",
            "MUSIC_PAUSE": "Pause",
            "MUSIC_RESUME": "Unpause",
            "MUSIC_NEXT": "Next",
            "MUSIC_PREVIOUS": "Previous",
        }.get(command)
        if not endpoint:
            return "Unsupported Jellyfin media command."
        self._request("POST", f"/Sessions/{urllib.parse.quote(session['Id'], safe='')}/Playing/{endpoint}")
        return f"{endpoint} sent to {session.get('DeviceName', 'your connected device')}."

    def execute(self, command: str, query: str = "") -> Optional[str]:
        if not self.configured:
            return None
        try:
            if command in {"MEDIA_PLAY", "MUSIC_ON", "MUSIC_SHUFFLE"}:
                return self.play(self._extract_query(query))
            return self.command(command)
        except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as error:
            return f"Jellyfin control failed locally: {error}"

    @staticmethod
    def _extract_query(query: str) -> str:
        words = (query or "").strip().split()
        if len(words) <= 1:
            return ""
        if len(words) == 2 and words[1].lower() in {"music", "song", "songs", "tracks", "playlist"}:
            return ""
        prefixes = {"play", "start", "shuffle", "resume", "music", "song", "track"}
        while words and words[0].lower() in prefixes:
            words.pop(0)
        return " ".join(words)