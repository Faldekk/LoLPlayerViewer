"""Modele danych aplikacji LoL Player Viewer."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerData:
    riot_id: str
    level: int
    ranks: list[dict]
    matches: list[dict]
    profile_icon_id: int = 0
