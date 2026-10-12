"""Le plan conditionnel du répartiteur (décision D5).

Transcription de l'ordre des règles de ``specs_metier.md`` §10. Le répartiteur lit le verdict que
l'agent vient de lui rendre et en déduit l'étape suivante — sans autre interprétation. Aucun agent
ne connaît ce plan : c'est ce qui les empêche de se renvoyer le travail.
"""

from __future__ import annotations

ELIGIBILITE = "eligibilite"
PIECES = "pieces"
ESTIMATION = "estimation"
ANTIFRAUDE = "antifraude"
DECISION = "decision"

PREMIERE_ETAPE = ELIGIBILITE

#: (étape achevée, verdict rendu) → étape suivante. ``None`` termine le traitement.
PLAN: dict[tuple[str, str], str | None] = {
    (ELIGIBILITE, "non_recevable"): DECISION,
    (ELIGIBILITE, "recevable"): PIECES,
    (PIECES, "completes"): ESTIMATION,
    (PIECES, "sans_depot"): DECISION,
    (PIECES, "reprise"): PIECES,
    (PIECES, "epuise"): DECISION,
    (ESTIMATION, "montant_nul"): DECISION,
    (ESTIMATION, "montant_positif"): ANTIFRAUDE,
    (ANTIFRAUDE, "termine"): DECISION,
    (DECISION, "close"): None,
}

#: Verdicts qui signalent qu'une borne a été atteinte, et le nom d'arrêt correspondant.
VERDICTS_SUR_BORNE: dict[tuple[str, str], str] = {
    (PIECES, "epuise"): "pieces_sans_depot_restant",
}


class VerdictInconnu(RuntimeError):
    """Un agent a rendu un verdict que le plan ne prévoit pas."""


def etape_suivante(etape: str, verdict: str) -> str | None:
    """L'étape à confier ensuite, d'après le plan seul."""
    cle = (etape, verdict)
    if cle not in PLAN:
        raise VerdictInconnu(f"verdict « {verdict} » inattendu après l'étape « {etape} »")
    return PLAN[cle]


def borne_atteinte(etape: str, verdict: str) -> str | None:
    """Nom de la borne si ce verdict en signale une, sinon ``None``."""
    return VERDICTS_SUR_BORNE.get((etape, verdict))
