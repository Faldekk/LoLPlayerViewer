"""Pobieranie i pamięci podręczna assetów z Riot Data Dragon."""

import json
import html
import re
import threading
import urllib.error
import urllib.parse
import urllib.request


class DataDragonAssets:
    _version: str | None = None
    _bytes_cache: dict[tuple[str, str], bytes] = {}
    _lock = threading.Lock()
    _champion_map: dict[str, str] | None = None
    _item_map: dict[str, dict] | None = None

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
    def get_champion_map(cls) -> dict[str, str]:
        with cls._lock:
            if cls._champion_map is not None:
                return cls._champion_map.copy()
        version = cls.get_version()
        request = urllib.request.Request(
            f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json",
            headers={"User-Agent": "LoL-Player-Viewer/1.0"},
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.load(response)
        champion_map = {
            str(champion["key"]): champion["id"]
            for champion in payload.get("data", {}).values()
        }
        with cls._lock:
            cls._champion_map = champion_map
        return champion_map.copy()

    @classmethod
    def get_item_map(cls) -> dict[str, dict]:
        with cls._lock:
            if cls._item_map is not None:
                return cls._item_map.copy()
        version = cls.get_version()
        request = urllib.request.Request(
            f"https://ddragon.leagueoflegends.com/cdn/{version}/data/pl_PL/item.json",
            headers={"User-Agent": "LoL-Player-Viewer/1.0"},
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.load(response)
        item_map = {}
        for item_id, item in payload.get("data", {}).items():
            description = html.unescape(str(item.get("description", "")))
            description = re.sub(r"<br\s*/?>", "\n", description, flags=re.I)
            description = re.sub(r"<[^>]+>", " ", description)
            description = re.sub(r"[ \t]+", " ", description)
            description = re.sub(r"\s*\n\s*", "\n", description).strip()
            gold = item.get("gold", {})
            item_map[str(item_id)] = {
                "name": str(item.get("name", f"Item {item_id}")),
                "description": description,
                "plaintext": str(item.get("plaintext", "")),
                "total": int(gold.get("total", 0) or 0),
                "sell": int(gold.get("sell", 0) or 0),
                "purchasable": bool(gold.get("purchasable", False)),
            }
        with cls._lock:
            cls._item_map = item_map
        return item_map.copy()

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
