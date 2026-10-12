"""Mesures par agent (interface.md, exigence EX-6).

Chaque demande tient ses propres compteurs ; l'agrégation d'un lot se fait **après coup**, une fois
toutes les demandes traitées. Agréger pendant réintroduirait l'état partagé entre demandes que la
conception écarte (décision D8).
"""

from __future__ import annotations

from typing import Any

CLES = ("appels", "echecs", "latence_ms", "appels_externes")


class Compteurs:
    """Les mesures d'une seule demande, agent par agent."""

    def __init__(self) -> None:
        self._par_agent: dict[str, dict[str, float]] = {}

    def enregistrer(
        self, agent: str, duree_ms: float, *, echec: bool = False, appels_externes: int = 0
    ) -> None:
        entree = self._par_agent.setdefault(
            agent, {"appels": 0, "echecs": 0, "duree_ms": 0.0, "appels_externes": 0}
        )
        entree["appels"] += 1
        entree["duree_ms"] += duree_ms
        if echec:
            entree["echecs"] += 1
        entree["appels_externes"] += appels_externes

    def brut(self) -> dict[str, dict[str, float]]:
        """Les sommes, telles quelles — c'est ce qui s'additionne entre demandes."""
        return {agent: dict(valeurs) for agent, valeurs in self._par_agent.items()}


def agreger(compteurs: list[dict[str, dict[str, float]]]) -> dict[str, dict[str, Any]]:
    """Additionne les compteurs de plusieurs demandes et calcule la latence moyenne."""
    cumul: dict[str, dict[str, float]] = {}
    for mesures_demande in compteurs:
        for agent, valeurs in mesures_demande.items():
            entree = cumul.setdefault(
                agent, {"appels": 0, "echecs": 0, "duree_ms": 0.0, "appels_externes": 0}
            )
            for cle, valeur in valeurs.items():
                entree[cle] += valeur

    resultat: dict[str, dict[str, Any]] = {}
    for agent, valeurs in cumul.items():
        appels = int(valeurs["appels"])
        resultat[agent] = {
            "appels": appels,
            "echecs": int(valeurs["echecs"]),
            "latence_ms": round(valeurs["duree_ms"] / appels, 2) if appels else 0.0,
            "appels_externes": int(valeurs["appels_externes"]),
        }
    return resultat


#: Bornes qui ne devraient jamais se declencher — leur part est un signal d'alerte.
GARDE_FOUS = frozenset(
    {"etapes_max_atteint", "duree_max_atteinte", "cloture_manquante", "pieces_tentatives_epuisees"}
)


def observer(fiche: dict[str, Any], cause_indisponibilite: str | None) -> dict[str, Any]:
    """Ce qu'une demande apprend sur le fonctionnement de l'équipe, au-delà de son issue."""
    from .partenaire import erreurs

    borne = (fiche.get("arret") or {}).get("borne")
    return {
        "etapes": len(fiche.get("trace", [])),
        "mode_degrade": bool(fiche.get("mode_degrade")),
        "rejet_de_forme": cause_indisponibilite in erreurs.REJET_DE_FORME,
        "garde_fou": borne in GARDE_FOUS,
    }


def signaux(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Les quatre signaux ajoutés aux mesures imposées (exigence EX-6).

    Le troisième est le plus utile et le moins évident : **si la part rejetée pour la forme
    monte, c'est notre lecture du contrat qui dérive**, pas le partenaire qui tombe. Sans lui,
    on chercherait la panne du mauvais côté.
    """
    total = len(observations)
    if not total:
        return {
            "demandes": 0,
            "etapes_par_demande": 0.0,
            "part_mode_degrade": 0.0,
            "part_rejet_de_forme": 0.0,
            "part_garde_fou": 0.0,
        }
    return {
        "demandes": total,
        "etapes_par_demande": round(sum(o["etapes"] for o in observations) / total, 2),
        "part_mode_degrade": round(sum(o["mode_degrade"] for o in observations) / total, 3),
        "part_rejet_de_forme": round(sum(o["rejet_de_forme"] for o in observations) / total, 3),
        "part_garde_fou": round(sum(o["garde_fou"] for o in observations) / total, 3),
    }
