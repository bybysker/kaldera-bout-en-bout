"""Règles sur les pièces justificatives (specs_metier.md §5).

Le mot « cohérence » employé par la spécification n'est pas défini. Le seul critère qu'elle
fournit est le tableau des pièces exigées par type de sinistre : le contrôle s'y limite,
et l'écart est signalé dans le dossier de conception (décision D3).
"""

from __future__ import annotations

from typing import Any

PIECES_EXIGEES: dict[str, tuple[str, ...]] = {
    "degat_des_eaux": ("facture", "photo"),
    "incendie": ("facture", "photo"),
    "bris_de_glace": ("facture", "photo"),
    "vol": ("facture", "depot_plainte"),
}


def exigees(type_sinistre: str) -> tuple[str, ...]:
    return PIECES_EXIGEES[type_sinistre]


def manquantes(type_sinistre: str, recues: list[dict[str, Any]]) -> list[str]:
    """Types de pièces exigées absents ou dont le dernier exemplaire est illisible."""
    insuffisantes = []
    for type_piece in exigees(type_sinistre):
        du_type = [p for p in recues if p.get("type") == type_piece]
        if not du_type or not du_type[-1].get("lisible", False):
            insuffisantes.append(type_piece)
    return insuffisantes


def montants_factures(recues: list[dict[str, Any]]) -> list[float]:
    """Montants des factures lisibles, dans l'ordre de dépôt."""
    return [
        float(p["montant"])
        for p in recues
        if p.get("type") == "facture" and p.get("lisible", False) and p.get("montant") is not None
    ]


def depots_disponibles(demande: dict[str, Any], type_piece: str) -> list[dict[str, Any]]:
    """Dépôts de ce type présents dans l'espace assuré, dans l'ordre où l'assuré les a faits."""
    depots = demande.get("espace_assure", {}).get("depots", [])
    return [p for p in depots if p.get("type") == type_piece]
