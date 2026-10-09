"""Agent « décision » — auteur de la section ``issue``.

Seul agent qui conclut une demande. Il applique l'ordre des règles de ``specs_metier.md`` §10 :
la première qui s'applique fixe l'issue. C'est aussi lui qui écrit la sortie ordonnée quand une
borne d'exécution a été atteinte — jamais d'erreur technique en guise de résultat (décision D6).
"""

from __future__ import annotations

from typing import Any

from ..regles import issues

NOM = "decision"
SECTION = "issue"


def entrees(
    parties: dict[str, Any], travail: dict[str, Any], motif_borne: str | None
) -> dict[str, Any]:
    return {
        "eligibilite": parties.get("eligibilite"),
        "pieces": parties.get("pieces"),
        "estimation": parties.get("estimation"),
        "avis_fraude": parties.get("avis_fraude"),
        "controle_requis": bool(travail.get("controle_requis", False)),
        "partenaire_indisponible": bool(travail.get("partenaire_indisponible", False)),
        "motif_borne": motif_borne,
    }


def traiter(entrees: dict[str, Any]) -> dict[str, Any]:
    issue, mode_degrade = _issue(entrees)
    return {
        "section": SECTION,
        "contenu": {**issue, "mode_degrade": mode_degrade},
        "verdict": "close",
        "travail": {},
    }


def _issue(e: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Rend l'issue et le marquage « mode dégradé », dans l'ordre de la section 10.

    Le motif de borne arrive déjà rédigé : cet agent n'a pas à connaître les noms des bornes,
    qui relèvent de l'orchestration.
    """
    # Sortie ordonnée : une borne a interrompu le traitement avant sa conclusion normale.
    if e["motif_borne"]:
        return issues.escalade_sur_borne(e["motif_borne"]), False

    # 1 — demande non éligible
    eligibilite = e["eligibilite"] or {}
    if not eligibilite.get("eligible", False):
        return issues.refus_non_eligible(eligibilite.get("motifs", [])), False

    # 2 — pièces manquantes
    pieces = e["pieces"] or {}
    if not pieces.get("conformes", False):
        return issues.escalade_pieces_manquantes(pieces.get("a_redemander", [])), False

    # 3 — montant estimé nul
    montant = (e["estimation"] or {}).get("montant_estime", 0.0)
    if montant <= 0:
        return issues.refus_sous_franchise(), False

    # 4 — contrôle anti-fraude
    avis = e["avis_fraude"]
    mode_degrade = False
    if avis is not None:
        niveau = avis.get("niveau")
        if niveau == "modere":
            return issues.escalade_controle_renforce(), False
        if niveau == "eleve":
            return issues.escalade_suspicion_fraude(), False
    elif e["controle_requis"] and e["partenaire_indisponible"]:
        # Mode dégradé : il ne marque que les demandes qui requéraient un contrôle.
        mode_degrade = True
        if montant > issues.SEUIL_MODE_DEGRADE:
            return issues.escalade_antifraude_manuel(), True

    # 5 — seuil de délégation
    if montant > issues.SEUIL_DELEGATION:
        return issues.escalade_seuil_delegation(), mode_degrade

    # 6 — acceptée
    return issues.acceptation(montant), mode_degrade
