"""Validation d'une réponse du partenaire, en quatre niveaux (décision D18).

Le protocole sécurise le canal, pas le sens : une liaison peut être parfaitement établie et le
contenu faux. Le quatrième niveau est celui qu'on oublie — une réponse peut être bien formée,
authentifiée, dans les délais, et porter sur le dossier du voisin.

**Le premier échec arrête tout.** Rien du contenu rejeté ne ressort : seule la cause sort.
"""

from __future__ import annotations

from typing import Any

from . import erreurs

CHAMPS_REPONSE = frozenset(
    {"reference_dossier", "score", "niveau", "indicateurs", "evaluation_id", "version_modele"}
)

NIVEAUX_RISQUE = ("faible", "modere", "eleve")
INDICATEURS_CONNUS = frozenset(
    {"MONTANT_ELEVE", "SINISTRE_PRECOCE", "FREQUENCE_ELEVEE", "TYPE_SENSIBLE"}
)

SEUIL_MODERE = 0.40
SEUIL_ELEVE = 0.75


def niveau_attendu(score: float) -> str:
    """Correspondance score / niveau, fixée par le contrat §3."""
    if score < SEUIL_MODERE:
        return "faible"
    if score < SEUIL_ELEVE:
        return "modere"
    return "eleve"


def valider_enveloppe(
    corps: Any, identifiant_envoye: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Niveau 2 — lisibilité : enveloppe JSON-RPC conforme, et une seule partie de type data."""
    if not isinstance(corps, dict):
        return None, erreurs.ENVELOPPE_NON_CONFORME
    if corps.get("jsonrpc") != "2.0":
        return None, erreurs.ENVELOPPE_NON_CONFORME
    if "error" in corps:
        # Le contrat §4 associe un code a chaque situation : les distinguer permet de savoir si
        # c'est notre requete qui est fautive (-32602) ou le partenaire qui refuse (-32029).
        erreur = corps["error"]
        code = erreur.get("code") if isinstance(erreur, dict) else None
        return None, erreurs.cause_rpc(code)
    if corps.get("id") != identifiant_envoye:
        return None, erreurs.IDENTIFIANT_DIFFERENT

    resultat = corps.get("result")
    if not isinstance(resultat, dict):
        return None, erreurs.ENVELOPPE_NON_CONFORME

    artefacts = resultat.get("artifacts")
    if not isinstance(artefacts, list) or len(artefacts) != 1:
        return None, erreurs.ENVELOPPE_NON_CONFORME
    parties = artefacts[0].get("parts") if isinstance(artefacts[0], dict) else None
    if not isinstance(parties, list) or len(parties) != 1:
        return None, erreurs.ENVELOPPE_NON_CONFORME
    partie = parties[0]
    if not isinstance(partie, dict) or partie.get("kind") != "data":
        return None, erreurs.ENVELOPPE_NON_CONFORME

    donnees = partie.get("data")
    if not isinstance(donnees, dict):
        return None, erreurs.ENVELOPPE_NON_CONFORME
    return donnees, None


def valider_forme(evaluation: dict[str, Any]) -> str | None:
    """Niveau 3 — forme : **exactement** les six champs attendus, aux bons types.

    Validation stricte : un champ en trop suffit à écarter la réponse. Le contrat le dit
    lui-même — une réponse non conforme « n'engage pas le partenaire ».
    """
    presents = set(evaluation)
    if presents - CHAMPS_REPONSE:
        return erreurs.CHAMPS_EN_TROP
    if CHAMPS_REPONSE - presents:
        return erreurs.CHAMPS_ABSENTS

    if not isinstance(evaluation["reference_dossier"], str):
        return erreurs.TYPES_INVALIDES
    score = evaluation["score"]
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return erreurs.TYPES_INVALIDES
    if not isinstance(evaluation["niveau"], str):
        return erreurs.TYPES_INVALIDES
    indicateurs = evaluation["indicateurs"]
    if not isinstance(indicateurs, list) or not all(isinstance(i, str) for i in indicateurs):
        return erreurs.TYPES_INVALIDES
    if not isinstance(evaluation["evaluation_id"], str):
        return erreurs.TYPES_INVALIDES
    if not isinstance(evaluation["version_modele"], str):
        return erreurs.TYPES_INVALIDES
    return None


def valider_sens(evaluation: dict[str, Any], reference_envoyee: str) -> str | None:
    """Niveau 4 — sens : la réponse est-elle plausible, et porte-t-elle sur notre dossier ?"""
    if evaluation["reference_dossier"] != reference_envoyee:
        return erreurs.DOSSIER_DIFFERENT
    score = float(evaluation["score"])
    if not 0.0 <= score <= 1.0:
        return erreurs.SCORE_HORS_BORNES
    if evaluation["niveau"] not in NIVEAUX_RISQUE:
        return erreurs.NIVEAU_INCOHERENT
    if evaluation["niveau"] != niveau_attendu(score):
        return erreurs.NIVEAU_INCOHERENT
    if not set(evaluation["indicateurs"]) <= INDICATEURS_CONNUS:
        return erreurs.TYPES_INVALIDES
    return None


def valider(
    corps: Any, identifiant_envoye: str, reference_envoyee: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Les niveaux 2 à 4 enchaînés. Le niveau 1 est tenu par la passerelle, au transport.

    Rend l'évaluation retenue, ou ``None`` et la cause du rejet. Jamais les deux.
    """
    evaluation, cause = valider_enveloppe(corps, identifiant_envoye)
    if cause is not None or evaluation is None:
        return None, cause

    cause = valider_forme(evaluation)
    if cause is not None:
        return None, cause

    cause = valider_sens(evaluation, reference_envoyee)
    if cause is not None:
        return None, cause

    return evaluation, None
