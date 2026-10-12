"""Bornes d'exécution et noms d'arrêt (décisions D6, D11 ; interface.md).

Deux natures, à ne pas confondre :

- une **borne métier** fait partie du service rendu — le nombre de chances laissées à un assuré ;
- un **garde-fou** ne doit jamais se déclencher. S'il le fait, c'est un défaut à corriger, pas un
  réglage à desserrer.
"""

from __future__ import annotations

from typing import Any

#: Bornes publiées par ``kaldera.bornes()``.
BORNES: dict[str, Any] = {
    "etapes_max": 10,  # garde-fou ; 7 au pire cas prévu, 1 réservée pour la sortie
    "duree_max_s": 8,  # garde-fou ; la sortie ordonnée est déclenchée à 6 s
    "pieces_tentatives_max": 3,  # borne métier
    "partenaire_delai_s": 3,  # fixé par le contrat partenaire v2.0
    "etape_duree_max_s": 1,  # garde-fou, hors attente d'un service extérieur
}

#: Seuil de déclenchement de la sortie ordonnée, sous la borne publiée.
SORTIE_ORDONNEE_S = 6.0

# ------------------------------------------------------------------ noms d'arrêt

PIECES_TENTATIVES_EPUISEES = "pieces_tentatives_epuisees"
PIECES_SANS_DEPOT_RESTANT = "pieces_sans_depot_restant"
ETAPES_MAX_ATTEINT = "etapes_max_atteint"
DUREE_MAX_ATTEINTE = "duree_max_atteinte"
CLOTURE_MANQUANTE = "cloture_manquante"
AGENT_DEFAILLANT = "agent_defaillant"

#: Motif d'escalade associé à chaque borne. Toute escalade sur borne part au gestionnaire (D11).
MOTIFS: dict[str, str] = {
    PIECES_TENTATIVES_EPUISEES: "Pièces illisibles après relance : contrôle manuel nécessaire",
    PIECES_SANS_DEPOT_RESTANT: "Pièces illisibles après relance : contrôle manuel nécessaire",
    ETAPES_MAX_ATTEINT: "Traitement interrompu : nombre d'étapes épuisé",
    DUREE_MAX_ATTEINTE: "Traitement interrompu : durée maximale atteinte",
    CLOTURE_MANQUANTE: "Traitement interrompu : aucune issue produite",
    AGENT_DEFAILLANT: "Traitement interrompu : incident technique, reprise manuelle",
}


def publiees() -> dict[str, Any]:
    """Copie des bornes en vigueur."""
    return dict(BORNES)


def motif(borne: str) -> str:
    return MOTIFS.get(borne, "Traitement interrompu")
