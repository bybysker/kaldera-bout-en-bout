"""Règles d'éligibilité E1 à E5 (specs_metier.md §4).

Ces règles ne chiffrent rien : le plafond de garantie est un écrêtage du remboursement,
il appartient donc à l'estimation (voir ``montants.py``).
"""

from __future__ import annotations

from typing import Any

from . import formules
from .calendrier import jours_entre

CARENCE_JOURS = 30
DELAI_DECLARATION_JOURS = 30
DELAI_DECLARATION_VOL_JOURS = 5


def delai_declaration_max(type_sinistre: str) -> int:
    """Délai de déclaration autorisé, en jours (E4)."""
    return DELAI_DECLARATION_VOL_JOURS if type_sinistre == "vol" else DELAI_DECLARATION_JOURS


def motifs_non_eligibilite(contrat: dict[str, Any], sinistre: dict[str, Any]) -> list[str]:
    """Liste les conditions non remplies, dans l'ordre E1 à E5. Vide si la demande est éligible."""
    motifs: list[str] = []

    if contrat["statut"] != "actif":
        motifs.append("contrat non actif")

    if not contrat["cotisations_a_jour"]:
        motifs.append("cotisations impayées")

    if anciennete_contrat(contrat, sinistre) < CARENCE_JOURS:
        motifs.append("sinistre survenu pendant la période de carence")

    delai = jours_entre(sinistre["date_survenance"], sinistre["date_declaration"])
    if delai > delai_declaration_max(sinistre["type"]):
        motifs.append("déclaration hors délai")

    if not formules.couvre(contrat["formule"], sinistre["type"]):
        motifs.append("sinistre non couvert par la formule")

    return motifs


def anciennete_contrat(contrat: dict[str, Any], sinistre: dict[str, Any]) -> int:
    """Jours entre la souscription et la survenance du sinistre (specs_metier.md §3)."""
    return jours_entre(contrat["date_souscription"], sinistre["date_survenance"])
