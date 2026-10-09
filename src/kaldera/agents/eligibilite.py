"""Agent « éligibilité » — auteur de la section ``eligibilite``.

Il dit si le contrat couvre ce sinistre. **Il ne chiffre rien**, pas même le plafond de garantie :
le plafond modifie un montant, il appartient donc à l'estimation (décisions C3 et D3).
"""

from __future__ import annotations

from typing import Any

from ..regles import eligibilite as regles_eligibilite

NOM = "eligibilite"
SECTION = "eligibilite"


def entrees(demande: dict[str, Any]) -> dict[str, Any]:
    """Ce dont l'agent a besoin — et rien de plus."""
    return {"contrat": demande["contrat"], "sinistre": demande["sinistre"]}


def traiter(entrees: dict[str, Any]) -> dict[str, Any]:
    motifs = regles_eligibilite.motifs_non_eligibilite(entrees["contrat"], entrees["sinistre"])
    anciennete = regles_eligibilite.anciennete_contrat(entrees["contrat"], entrees["sinistre"])
    return {
        "section": SECTION,
        "contenu": {"eligible": not motifs, "motifs": motifs},
        "verdict": "recevable" if not motifs else "non_recevable",
        "travail": {"anciennete_contrat_jours": anciennete},
    }
