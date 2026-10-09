"""Agent « pièces » — auteur de la section ``pieces``.

Deux situations qui se ressemblent et n'ont rien à voir :

- **aucun dépôt du type demandé** : c'est une règle métier (specs §5), la demande part au
  gestionnaire **sans** signalement d'arrêt. C'est le scénario nominal ``NOM-09`` ;
- **des dépôts ont été examinés et il n'en reste aucun** : c'est une borne, la demande part au
  gestionnaire **avec** signalement d'arrêt. C'est le scénario ``BCL-01``.

Les confondre ferait marquer un arrêt sur un cas nominal, ou l'inverse.
"""

from __future__ import annotations

from typing import Any

from .. import espace_assure
from ..regles import pieces as regles_pieces

NOM = "pieces"
SECTION = "pieces"


def entrees(demande: dict[str, Any], travail: dict[str, Any]) -> dict[str, Any]:
    return {
        "demande": demande,
        "type_sinistre": demande["sinistre"]["type"],
        "pieces_deposees": list(demande.get("pieces", [])),
        "complements": list(travail.get("complements", [])),
        "tentatives": dict(travail.get("tentatives", {})),
    }


def traiter(entrees: dict[str, Any]) -> dict[str, Any]:
    recues = entrees["pieces_deposees"] + entrees["complements"]
    manquantes = regles_pieces.manquantes(entrees["type_sinistre"], recues)

    if not manquantes:
        return _publier(recues, manquantes=[], verdict="completes")

    sans_aucun_depot = [
        type_piece
        for type_piece in manquantes
        if not regles_pieces.depots_disponibles(entrees["demande"], type_piece)
    ]
    if sans_aucun_depot:
        return _publier(recues, manquantes, verdict="sans_depot")

    complements, tentatives = _demander(entrees, manquantes)
    if not complements:
        return _publier(recues, manquantes, verdict="epuise")

    return {
        "section": None,
        "contenu": None,
        "verdict": "reprise",
        "travail": {
            "complements": entrees["complements"] + complements,
            "tentatives": tentatives,
        },
    }


def _demander(
    entrees: dict[str, Any], manquantes: list[str]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Demande un complément pour chaque type manquant ; rend les dépôts nouvellement obtenus."""
    tentatives = dict(entrees["tentatives"])
    obtenus: list[dict[str, Any]] = []
    for type_piece in manquantes:
        rang = tentatives.get(type_piece, 0)
        disponibles = regles_pieces.depots_disponibles(entrees["demande"], type_piece)
        if rang >= len(disponibles):
            continue  # l'assuré n'a plus rien de nouveau à transmettre pour ce type
        depot = espace_assure.demander_piece(entrees["demande"], type_piece, rang)
        tentatives[type_piece] = rang + 1
        if depot is not None:
            obtenus.append(depot)
    return obtenus, tentatives


def _publier(recues: list[dict[str, Any]], manquantes: list[str], verdict: str) -> dict[str, Any]:
    return {
        "section": SECTION,
        "contenu": {
            "conformes": not manquantes,
            "a_redemander": list(manquantes),
            "factures": regles_pieces.montants_factures(recues),
        },
        "verdict": verdict,
        "travail": {},
    }
