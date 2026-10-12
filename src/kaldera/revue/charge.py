"""Ce que le relecteur reçoit — et ce qu'il ne reçoit pas.

Un modèle hébergé est un tiers. Le contrat anti-fraude interdit déjà de transmettre l'identité,
l'IBAN et la description libre à un partenaire ; savoir si un modèle de langage relève de la
même règle n'était pas une question technique, elle engageait la conformité.

**Le métier a tranché le 12 octobre 2026 : le récit de l'assuré ne part chez aucun modèle
hébergé** *(`D32`)*. Il n'y a donc plus de drapeau pour l'ouvrir. Un interrupteur qu'on garde
« au cas où » après une décision contraire n'est plus une option laissée au métier : c'est une
porte que personne ne surveille.

Seuls les champs listés ci-dessous partent, écrits un par un. Conséquence assumée : la
cohérence des pièces ne se juge que sur la **structure** — types et montants au regard de la
nature du sinistre.
"""

from __future__ import annotations

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

    return dossier


def _section(fiche: dict[str, Any], nom: str) -> dict[str, Any]:
    """Une section publiée, retrouvée depuis la trace — la fiche ne les porte pas toutes."""
    if nom == "estimation" and fiche.get("montant_rembourse") is not None:
        return {"montant_estime": fiche["montant_rembourse"]}
    return {}
