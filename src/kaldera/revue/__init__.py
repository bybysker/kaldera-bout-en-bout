"""La revue de fond : un relecteur qui passe **après** la décision.

Le formateur a ouvert le brief : un modèle de langage peut entrer dans le système. La question
devient donc « à quel degré, et à quel endroit », et elle se tranche avec des mesures.

**Ce que les mesures disent.** Un appel au modèle met de 5,6 à 12,8 secondes sur ce poste pour une revue — mesuré sur dix
appels — pour
un engagement de service de 10 secondes par demande. Les cinq agents du chemin de décision
traitent une demande complète en 0,04 ms. Placer un modèle dans ce chemin reviendrait à faire
dépendre la tenue de l'engagement d'un service tiers dont la latence varie du simple au triple.

**D'où le choix** : un sixième agent, mais **hors du chemin**. Il relit ce qui est déjà décidé
et signale ce qui mérite un œil humain. La décision ne l'attend pas, et ne peut pas en dépendre.

Un test d'architecture garantit qu'aucun agent, ni l'orchestration, ni le répartiteur n'importe
ce paquet.
"""

from __future__ import annotations

from . import charge
from .relecteur import DELAI_MAX_S, NIVEAUX, Relecteur, relire

__all__ = ["DELAI_MAX_S", "NIVEAUX", "Relecteur", "charge", "relire"]
