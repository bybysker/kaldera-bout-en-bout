"""Référentiel métier : des fonctions pures, qui ne dépendent de rien du paquet.

C'est le cœur déterministe. Aucun module de ``regles`` n'importe un agent, l'orchestration
ou le dossier : des valeurs entrent, des valeurs sortent. C'est ce qui permet de rejouer
une règle isolément, sans monter le système.
"""

from __future__ import annotations

from . import eligibilite, formules, indicateurs, issues, montants, pieces
from .calendrier import jours_entre

__all__ = [
    "eligibilite",
    "formules",
    "indicateurs",
    "issues",
    "jours_entre",
    "montants",
    "pieces",
]
