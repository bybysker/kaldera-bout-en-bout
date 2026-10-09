"""Calculs de dates (specs_metier.md §3)."""

from __future__ import annotations

from datetime import date


def jours_entre(debut: str, fin: str) -> int:
    """Nombre de jours entre deux dates ``AAAA-MM-JJ``."""
    return (date.fromisoformat(fin) - date.fromisoformat(debut)).days
