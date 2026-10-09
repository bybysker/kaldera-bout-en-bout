"""Agent « estimation » — auteur de la section ``estimation``.

Il chiffre, et ne se prononce ni sur l'éligibilité ni sur la fraude. C'est lui qui applique le
plafond de garantie, **après** la franchise : le plafond modifie un montant, il relève donc de
l'estimation même si la spécification l'écrit dans la section « Éligibilité » (décisions C3, D3).
"""

from __future__ import annotations

from typing import Any

from ..regles import montants as regles_montants

NOM = "estimation"
SECTION = "estimation"


def entrees(demande: dict[str, Any], partie_pieces: dict[str, Any]) -> dict[str, Any]:
    return {
        "montant_declare": demande["sinistre"]["montant_declare"],
        "formule": demande["contrat"]["formule"],
        "factures": list(partie_pieces.get("factures", [])),
    }


def traiter(entrees: dict[str, Any]) -> dict[str, Any]:
    chiffres = regles_montants.estimer(
        entrees["montant_declare"], entrees["factures"], entrees["formule"]
    )
    contenu = {
        "montant_justifie": chiffres["montant_justifie"],
        "montant_estime": chiffres["montant_estime"],
    }
    verdict = "montant_positif" if chiffres["montant_estime"] > 0 else "montant_nul"
    return {
        "section": SECTION,
        "contenu": contenu,
        "verdict": verdict,
        "travail": {"montant_retenu": chiffres["montant_retenu"]},
    }
