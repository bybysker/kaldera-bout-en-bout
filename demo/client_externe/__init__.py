"""Un client externe : le cabinet de courtage qui dépose des demandes chez Kaldera.

Ce paquet **n'appartient pas** au système. Il vit dans `demo/`, n'importe que la porte publique
de `kaldera`, et sert à éprouver l'intégration du point de vue de celui qui l'utilise.

Il n'est pas demandé par le brief : il le challenge. Ce qu'il montre, et que les 28 scénarios
de recette ne montrent pas :

- **la minimisation est une chaîne**, pas un filtre unique. Sur les dossiers du catalogue, le
  cabinet détient 32 à 34 valeurs, Kaldera en reçoit 23 à 26, le partenaire anti-fraude en
  reçoit **sept**, tous plats et sans identité. Sept champs commerciaux — conseiller, taux de
  commission, valeur client, notes internes — ne franchissent jamais la première frontière ;
- **la porte publique suffit à intégrer la plateforme.** Si le courtier avait besoin de la trace
  ou de l'état interne, `docs/interface.md` n'exposerait pas assez ;
- **une fiche de décision se traduit en action**, pour quelqu'un dont ce n'est pas le métier de
  lire un code d'escalade.
"""

from __future__ import annotations

from . import courtier, depot, dossiers, importation, recits, saisie
from .depot import deposer, deposer_lot, donnees_non_transmises

__all__ = [
    "courtier",
    "deposer",
    "deposer_lot",
    "depot",
    "donnees_non_transmises",
    "dossiers",
    "importation",
    "recits",
    "saisie",
]
