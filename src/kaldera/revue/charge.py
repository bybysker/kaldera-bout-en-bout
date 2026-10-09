"""Ce que le relecteur reçoit — et ce qu'il ne reçoit pas.

Un modèle hébergé est un tiers. Le contrat anti-fraude interdit déjà de transmettre l'identité,
l'IBAN et la description libre à un partenaire ; la question de savoir si un modèle de langage
relève de la même règle **n'est pas technique**, elle engage la conformité.

Tant que le métier n'a pas tranché, ce module applique **la règle la plus stricte** : seuls des
champs structurés partent, jamais le récit de l'assuré. Un drapeau permet d'ouvrir, et il est
fermé par défaut — l'inverse serait un choix pris par omission.

    KALDERA_REVUE_RECIT=1   # le métier a tranché : la description peut partir
"""

from __future__ import annotations

import os
from typing import Any

#: Les champs du dossier que le relecteur voit toujours. Aucun ne désigne une personne.
CHAMPS_STRUCTURES = (
    "reference",
    "type_sinistre",
    "montant_declare",
    "montant_estime",
    "formule",
    "statut_contrat",
    "cotisations_a_jour",
    "anciennete_contrat_jours",
    "delai_declaration_jours",
    "sinistres_12_mois",
    "pieces",
    "issue",
    "decision",
    "montant_rembourse",
    "motif",
    "file",
    "mode_degrade",
)

VARIABLE_RECIT = "KALDERA_REVUE_RECIT"


def recit_autorise() -> bool:
    """Le métier a-t-il autorisé la transmission de la description libre ?

    Fermé par défaut. Une donnée personnelle qui part parce que personne n'a dit non est une
    donnée personnelle qui part sans décision.
    """
    return os.environ.get(VARIABLE_RECIT, "").strip() in ("1", "true", "oui")


def construire(demande: dict[str, Any], fiche: dict[str, Any]) -> dict[str, Any]:
    """Le dossier tel que le relecteur le voit, construit en partant de rien.

    Même principe que la charge envoyée au partenaire : les champs sont écrits un par un. Un
    champ ajouté demain à la demande ne partira pas tout seul.
    """
    from ..regles.calendrier import jours_entre

    contrat, sinistre = demande["contrat"], demande["sinistre"]
    estimation = _section(fiche, "estimation")

    dossier: dict[str, Any] = {
        "reference": fiche["reference"],
        "type_sinistre": sinistre["type"],
        "montant_declare": sinistre["montant_declare"],
        "montant_estime": estimation.get("montant_estime"),
        "formule": contrat["formule"],
        "statut_contrat": contrat["statut"],
        "cotisations_a_jour": contrat["cotisations_a_jour"],
        "anciennete_contrat_jours": jours_entre(
            contrat["date_souscription"], sinistre["date_survenance"]
        ),
        "delai_declaration_jours": jours_entre(
            sinistre["date_survenance"], sinistre["date_declaration"]
        ),
        "sinistres_12_mois": demande.get("historique", {}).get("sinistres_12_mois", 0),
        "pieces": [
            {"type": p["type"], "lisible": bool(p.get("lisible")), "montant": p.get("montant")}
            for p in demande.get("pieces", [])
        ],
        "issue": fiche["issue"],
        "decision": fiche.get("decision"),
        "montant_rembourse": fiche.get("montant_rembourse"),
        "motif": fiche["motif"],
        "file": fiche.get("file"),
        "mode_degrade": bool(fiche.get("mode_degrade")),
    }

    if recit_autorise() and sinistre.get("description"):
        dossier["recit_assure"] = sinistre["description"]

    return dossier


def _section(fiche: dict[str, Any], nom: str) -> dict[str, Any]:
    """Une section publiée, retrouvée depuis la trace — la fiche ne les porte pas toutes."""
    if nom == "estimation" and fiche.get("montant_rembourse") is not None:
        return {"montant_estime": fiche["montant_rembourse"]}
    return {}
