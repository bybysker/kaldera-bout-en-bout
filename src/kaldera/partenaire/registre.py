"""Registre des appels : un seul par dossier (contrat partenaire v2.0, §6).

Ce n'est pas une préférence de conception mais une clause : tout appel en doublon est refusé
(`-32029`) et **signalé à l'assureur comme manquement au contrat**. Un registre coûte trois
lignes ; un manquement contractuel coûte bien plus.

Le registre vit le temps d'une demande, comme tout le reste : aucune structure n'est partagée
entre deux demandes (décision D8).
"""

from __future__ import annotations


class Registre:
    """Les dossiers déjà soumis au partenaire."""

    def __init__(self) -> None:
        self._appeles: set[str] = set()

    def deja_appele(self, reference: str) -> bool:
        return reference in self._appeles

    def marquer(self, reference: str) -> None:
        self._appeles.add(reference)

    @property
    def appels(self) -> int:
        return len(self._appeles)
