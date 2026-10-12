"""Indicateurs de risque F1 à F4 (specs_metier.md §7).

Ces indicateurs décident s'il faut **demander** un avis au partenaire. Ils ne constituent pas
un avis : « l'avis de fraude est émis par le partenaire, jamais en interne » (§2).
"""

from __future__ import annotations

SEUIL_MONTANT = 5_000.0
ANCIENNETE_SENSIBLE_JOURS = 90
FREQUENCE_SENSIBLE = 3
ECART_DECLARATION_MAX = 0.20


def presents(
    montant_declare: float,
    anciennete_jours: int,
    sinistres_12_mois: int,
    montant_justifie: float,
) -> list[str]:
    """Indicateurs déclenchés, dans l'ordre F1 à F4."""
    declenches: list[str] = []
    if montant_declare >= SEUIL_MONTANT:
        declenches.append("F1")
    if anciennete_jours < ANCIENNETE_SENSIBLE_JOURS:
        declenches.append("F2")
    if sinistres_12_mois >= FREQUENCE_SENSIBLE:
        declenches.append("F3")
    if montant_declare > montant_justifie * (1 + ECART_DECLARATION_MAX):
        declenches.append("F4")
    return declenches


def controle_requis(
    montant_declare: float,
    anciennete_jours: int,
    sinistres_12_mois: int,
    montant_justifie: float,
) -> bool:
    """Au moins un indicateur suffit."""
    return bool(presents(montant_declare, anciennete_jours, sinistres_12_mois, montant_justifie))
