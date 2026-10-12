"""Règles de décision et fabriques d'issues (specs_metier.md §8 à §11).

Les motifs sont produits par gabarit déterministe : la spécification les fournit déjà, et une
rédaction assistée devrait se justifier par une mesure, pas par principe (décision D9).
"""

from __future__ import annotations

from typing import Any

SEUIL_DELEGATION = 10_000.0
SEUIL_MODE_DEGRADE = 1_500.0

GESTIONNAIRE = "gestionnaire"
CELLULE_FRAUDE = "cellule_fraude"


def decision(nature: str, montant_rembourse: float, motif: str) -> dict[str, Any]:
    """Une issue qui conclut la demande : ``acceptee`` ou ``refusee``."""
    return {
        "issue": "decision",
        "decision": nature,
        "montant_rembourse": round(float(montant_rembourse), 2),
        "motif": motif,
        "file": None,
    }


def escalade(file: str, motif: str) -> dict[str, Any]:
    """Une issue qui confie la demande à une file humaine."""
    return {
        "issue": "escalade",
        "decision": None,
        "montant_rembourse": None,
        "motif": motif,
        "file": file,
    }


# ----------------------------------------------------------------------- gabarits


def refus_non_eligible(motifs: list[str]) -> dict[str, Any]:
    return decision("refusee", 0.0, "Demande non éligible : " + ", ".join(motifs))


def escalade_pieces_manquantes(types_manquants: list[str]) -> dict[str, Any]:
    return escalade(GESTIONNAIRE, "Pièces manquantes : " + ", ".join(types_manquants))


def refus_sous_franchise() -> dict[str, Any]:
    return decision("refusee", 0.0, "Dommage inférieur ou égal à la franchise")


def escalade_controle_renforce() -> dict[str, Any]:
    return escalade(GESTIONNAIRE, "Contrôle renforcé : risque de fraude modéré")


def escalade_suspicion_fraude() -> dict[str, Any]:
    return escalade(CELLULE_FRAUDE, "Suspicion de fraude")


def escalade_antifraude_manuel() -> dict[str, Any]:
    return escalade(CELLULE_FRAUDE, "Contrôle anti-fraude manuel : avis du partenaire indisponible")


def escalade_seuil_delegation() -> dict[str, Any]:
    return escalade(GESTIONNAIRE, "Seuil de délégation dépassé")


def acceptation(montant: float) -> dict[str, Any]:
    return decision("acceptee", montant, f"Remboursement accordé : {montant:.2f} €")


def escalade_sur_borne(motif: str) -> dict[str, Any]:
    """Sortie ordonnée après qu'une borne d'exécution a été atteinte (décision D11)."""
    return escalade(GESTIONNAIRE, motif)
