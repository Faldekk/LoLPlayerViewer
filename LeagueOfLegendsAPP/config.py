"""Stała konfiguracja regionów i kolejek League of Legends."""

REGIONS = {
    "Europa Zachodnia (EUW)": ("euw1", "europe"),
    "Europa Pn.-Wsch. (EUNE)": ("eun1", "europe"),
    "Ameryka Północna (NA)": ("na1", "americas"),
    "Korea (KR)": ("kr", "asia"),
    "Brazylia (BR)": ("br1", "americas"),
    "Japonia (JP)": ("jp1", "asia"),
    "Turcja (TR)": ("tr1", "europe"),
    "Oceania (OCE)": ("oc1", "sea"),
}

QUEUE_NAMES = {
    400: "Normal Draft",
    420: "Solo/Duo",
    430: "Normal Blind",
    440: "Flex",
    450: "ARAM",
    490: "Quickplay",
    1700: "Arena",
    1750: "Arena (1750)",
}
