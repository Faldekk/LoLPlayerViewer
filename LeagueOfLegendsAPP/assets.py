"""Pobieranie i pamięci podręczna assetów z Riot Data Dragon."""

import json
import threading
import urllib.error
import urllib.parse
import urllib.request


class DataDragonAssets:
    _version: str | None = None
    _bytes_cache: dict[tuple[str, str], bytes] = {}
    _lock = threading.Lock()

    @classmethod
    def get_version(cls) -> str:
        with cls._lock:
            if cls._version:
                return cls._version
        request = urllib.request.Request(
            "https://ddragon.leagueoflegends.com/api/versions.json",
            headers={"User-Agent": "LoL-Player-Viewer/1.0"},
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            version = json.load(response)[0]
        with cls._lock:
            cls._version = version
        return version

    @classmethod
    def load(cls, kind: str, asset_id: str | int) -> bytes | None:
        key = (kind, str(asset_id))
        with cls._lock:
            if key in cls._bytes_cache:
                return cls._bytes_cache[key]
        folders = {
            "champion": "champion",
            "item": "item",
            "profile": "profileicon",
        }
        folder = folders.get(kind)
        if folder is None:
            return None
        try:
            version = cls.get_version()
            safe_id = urllib.parse.quote(str(asset_id), safe="")
            url = f"https://ddragon.leagueoflegends.com/cdn/{version}/img/{folder}/{safe_id}.png"
            request = urllib.request.Request(
                url, headers={"User-Agent": "LoL-Player-Viewer/1.0"}
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                content = response.read()
        except (urllib.error.URLError, TimeoutError, ValueError, IndexError):
            return None
        with cls._lock:
            cls._bytes_cache[key] = content
        return content
