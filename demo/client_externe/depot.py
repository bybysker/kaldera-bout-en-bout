"""Le dépôt d'une demande par le courtier, et ce qu'il en reçoit en retour.

Le courtier n'a accès qu'à la **porte publique** : `traiter_demande`, `traiter_lot`, `bornes`.
C'est la contrainte qui donne son sens à l'exercice — s'il avait besoin d'autre chose, ce serait
le signe que la plateforme n'expose pas assez pour être intégrée par un tiers.

Il ne voit donc ni la trace interne, ni la zone de travail : il reçoit une fiche de décision,
exactement comme un système d'information partenaire la recevrait.
"""

from __future__ import annotations

from typing import Any

import kaldera

from . import courtier

#: Ce qu'un courtier a besoin de lire dans une fiche. Le reste ne le regarde pas.
CHAMPS_UTILES = (
    "reference",
    "issue",
    "decision",
    "montant_rembourse",
    "motif",
    "file",
    "mode_degrade",
)


def deposer(dossier: dict[str, Any], *, partenaire_url: str | None = None) -> dict[str, Any]:
    """Traduit un dossier courtier, le dépose, et rend ce que le courtier en apprend."""
    demande = courtier.traduire(dossier)
    fiche = kaldera.traiter_demande(demande, partenaire_url=partenaire_url)
    return {
        "id_dossier": dossier["id_dossier"],
        "demande_transmise": demande,
        "retour": {cle: fiche.get(cle) for cle in CHAMPS_UTILES},
        "suite": suite_a_donner(fiche),
    }


def deposer_lot(
    dossiers: list[dict[str, Any]], *, partenaire_url: str | None = None
) -> dict[str, Any]:
    """Dépose plusieurs dossiers d'un coup, comme le ferait un cabinet en fin de journée."""
    demandes = [courtier.traduire(d) for d in dossiers]
    resultat = kaldera.traiter_lot(demandes, partenaire_url=partenaire_url)
    retours = []
    for dossier, demande, fiche in zip(dossiers, demandes, resultat["fiches"], strict=True):
        retours.append(
            {
                "id_dossier": dossier["id_dossier"],
                "demande_transmise": demande,
                "retour": {cle: fiche.get(cle) for cle in CHAMPS_UTILES},
                "suite": suite_a_donner(fiche),
            }
        )
    return {"retours": retours, "signaux": resultat.get("signaux", {})}


def suite_a_donner(fiche: dict[str, Any]) -> str:
    """Ce que le courtier doit faire, traduit depuis l'issue — c'est son métier, pas le nôtre."""
    if fiche.get("issue") == "decision":
        if fiche.get("decision") == "acceptee":
            return "Informer le client du remboursement accordé."
        return "Expliquer le refus au client, et vérifier s'il y a matière à réclamation."
    if fiche.get("file") == "cellule_fraude":
        return "Dossier en contrôle approfondi : ne pas relancer, attendre le retour de l'assureur."
    return "Dossier confié à un gestionnaire : prévenir le client du délai supplémentaire."


def donnees_non_transmises(dossier: dict[str, Any]) -> dict[str, Any]:
    """Ce que le courtier détient et que Kaldera ne reçoit pas.

    C'est la démonstration que la minimisation ne commence pas à la passerelle anti-fraude :
    elle commence au premier échange entre deux systèmes.
    """
    return courtier.retenu_par_le_courtier(dossier)
