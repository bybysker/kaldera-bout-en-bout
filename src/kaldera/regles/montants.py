"""Calcul des montants (specs_metier.md §6, et le plafond de §4).

L'ordre compte : franchise **puis** plafond. Le scénario NOM-05 le démontre — 4 200 € déclarés
et justifiés sur une formule à 300 € de franchise et 3 000 € de plafond donnent 3 000 €, et non
2 700 €. Le plafond est un écrêtage du remboursement, pas un critère d'éligibilité.
"""

from __future__ import annotations

from . import formules


def montant_justifie(montants_factures: list[float]) -> float:
    """Somme des factures lisibles."""
    return round(sum(montants_factures), 2)


def montant_retenu(montant_declare: float, justifie: float) -> float:
    """Le plus petit du déclaré et du justifié : l'assureur ne rembourse jamais plus que déclaré."""
    return round(min(float(montant_declare), justifie), 2)


def montant_estime(retenu: float, formule: str) -> float:
    """Montant retenu, diminué de la franchise, sans être négatif, puis écrêté au plafond."""
    apres_franchise = max(0.0, retenu - formules.franchise(formule))
    return round(min(apres_franchise, formules.plafond(formule)), 2)


def estimer(
    montant_declare: float, montants_factures: list[float], formule: str
) -> dict[str, float]:
    """Les trois montants de la section 6, calculés d'un coup."""
    justifie = montant_justifie(montants_factures)
    retenu = montant_retenu(montant_declare, justifie)
    return {
        "montant_justifie": justifie,
        "montant_retenu": retenu,
        "montant_estime": montant_estime(retenu, formule),
    }
