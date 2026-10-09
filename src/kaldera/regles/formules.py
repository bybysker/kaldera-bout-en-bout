"""Formules d'assurance : garanties, franchise, plafond (specs_metier.md §4)."""

from __future__ import annotations

from typing import Any

FORMULES: dict[str, dict[str, Any]] = {
    "essentiel": {
        "garanties": frozenset({"degat_des_eaux", "incendie"}),
        "franchise": 300.0,
        "plafond": 3_000.0,
    },
    "confort": {
        "garanties": frozenset({"degat_des_eaux", "incendie", "bris_de_glace", "vol"}),
        "franchise": 150.0,
        "plafond": 8_000.0,
    },
    "premium": {
        "garanties": frozenset({"degat_des_eaux", "incendie", "bris_de_glace", "vol"}),
        "franchise": 0.0,
        "plafond": 20_000.0,
    },
}


def franchise(formule: str) -> float:
    return float(FORMULES[formule]["franchise"])


def plafond(formule: str) -> float:
    return float(FORMULES[formule]["plafond"])


def couvre(formule: str, type_sinistre: str) -> bool:
    return type_sinistre in FORMULES[formule]["garanties"]
