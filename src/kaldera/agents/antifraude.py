"""Agent « anti-fraude » — auteur de la section ``avis_fraude``, ou d'aucune.

Il calcule les quatre indicateurs de risque et décide s'il faut **demander** un avis. Les
indicateurs ne sont pas un avis : « l'avis de fraude est émis par le partenaire, jamais en
interne » (specs §2). Quand aucun contrôle n'est requis, ou quand l'avis n'est pas obtenu,
il ne publie rien.

Seul cet agent touche au paquet ``partenaire``. Il ne connaît ni l'adresse, ni le jeton, ni la
forme du message : il demande un avis et reçoit un verdict.
"""

from __future__ import annotations

from typing import Any

from ..partenaire import Passerelle
from ..regles import indicateurs as regles_indicateurs

NOM = "antifraude"
SECTION = "avis_fraude"


def entrees(
    demande: dict[str, Any],
    partie_estimation: dict[str, Any],
    anciennete_jours: int,
    passerelle: Passerelle,
) -> dict[str, Any]:
    return {
        "demande": demande,
        "montant_declare": demande["sinistre"]["montant_declare"],
        "anciennete_jours": anciennete_jours,
        "sinistres_12_mois": demande.get("historique", {}).get("sinistres_12_mois", 0),
        "montant_justifie": partie_estimation["montant_justifie"],
        "passerelle": passerelle,
    }


def traiter(entrees: dict[str, Any]) -> dict[str, Any]:
    declencheurs = regles_indicateurs.presents(
        entrees["montant_declare"],
        entrees["anciennete_jours"],
        entrees["sinistres_12_mois"],
        entrees["montant_justifie"],
    )

    if not declencheurs:
        return _rien_a_publier(controle_requis=False, cause=None, declencheurs=[])

    verdict = entrees["passerelle"].consulter(entrees["demande"])
    if verdict["avis"] is None:
        return _rien_a_publier(
            controle_requis=True, cause=verdict["cause"], declencheurs=declencheurs
        )

    return {
        "section": SECTION,
        "contenu": verdict["avis"],
        "verdict": "termine",
        "travail": {
            "controle_requis": True,
            "partenaire_indisponible": False,
            "indicateurs_declenches": declencheurs,
            # Conservé pour l'audit, dans la zone de travail : il ne ressort pas dans la fiche.
            "evaluation_id": verdict["evaluation_id"],
        },
        "appels_externes": 1,
    }


def _rien_a_publier(
    *, controle_requis: bool, cause: str | None, declencheurs: list[str]
) -> dict[str, Any]:
    return {
        "section": None,
        "contenu": None,
        "verdict": "termine",
        "travail": {
            "controle_requis": controle_requis,
            "partenaire_indisponible": controle_requis,
            "indicateurs_declenches": declencheurs,
            "cause_indisponibilite": cause,
        },
        "appels_externes": 1 if controle_requis else 0,
        "echec": controle_requis,
        "cause": cause,
    }
