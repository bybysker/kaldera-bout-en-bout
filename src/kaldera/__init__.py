"""Kaldera — traitement des demandes de remboursement d'assurance par une équipe d'agents.

La porte publique du système, telle que ``docs/interface.md`` la fixe. Tout ce qui est observable
de l'extérieur passe par ces trois fonctions : c'est aussi par elles que la suite d'acceptance
entre, et c'est volontaire — on teste une équipe, pas un agent.
"""

from __future__ import annotations

from typing import Any

from . import mesures
from . import revue as _revue
from .orchestration import bornes as _bornes
from .orchestration import Repartiteur

__all__ = ["bornes", "relire", "traiter_demande", "traiter_lot"]


def traiter_demande(
    demande: dict[str, Any], *, partenaire_url: str | None = None
) -> dict[str, Any]:
    """Traite une demande et retourne sa fiche de décision."""
    fiche, _ = Repartiteur(partenaire_url).traiter(demande)
    return fiche


def traiter_lot(
    demandes: list[dict[str, Any]], *, partenaire_url: str | None = None
) -> dict[str, Any]:
    """Traite un lot ; retourne les fiches dans l'ordre des demandes, et les mesures par agent.

    Chaque demande a son propre dossier et ses propres compteurs : aucune ne lit l'état d'une
    autre pendant son traitement. Les mesures ne sont additionnées qu'une fois le lot terminé.
    """
    repartiteur = Repartiteur(partenaire_url)
    fiches: list[dict[str, Any]] = []
    compteurs: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for demande in demandes:
        fiche, releve = repartiteur.traiter(demande)
        fiches.append(fiche)
        compteurs.append(releve["compteurs"])
        observations.append(releve["observation"])
    return {
        "fiches": fiches,
        "metriques": mesures.agreger(compteurs),
        "signaux": mesures.signaux(observations),
    }


def bornes() -> dict[str, Any]:
    """Les bornes d'exécution en vigueur (``docs/interface.md``)."""
    return _bornes.publiees()


def relire(demande: dict[str, Any], fiche: dict[str, Any], fabrique: Any = None) -> dict[str, Any]:
    """Relit une décision **déjà prise**, et dit si elle mérite un œil humain.

    Hors du chemin de décision, et c'est tout l'arbitrage : un appel au modèle met plusieurs
    secondes là où les cinq agents en mettent 0,04 ms. Appelée après `traiter_demande`, cette
    relecture ne coûte rien au service rendu ; appelée pendant, elle mangerait l'engagement.

    Elle ne modifie jamais la fiche : son avis s'ajoute à côté.
    """
    return _revue.relire(demande, fiche, fabrique)
