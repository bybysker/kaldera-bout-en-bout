"""Chaque branche de rejet, éprouvée pour elle-même.

La suite d'acceptance couvre sept réponses invalides. La revue de code a montré que cela laissait
`validation.py` à 79 % : les formes d'enveloppe malmenées que le simulateur ne produit pas
n'étaient jamais exercées.

Or c'est le module où une branche jamais parcourue coûte le plus cher : elle n'échoue pas, elle
**laisse passer**.
"""

from __future__ import annotations

from typing import Any

import pytest

from kaldera.partenaire import erreurs, validation

IDENTIFIANT = "11111111-2222-3333-4444-555555555555"
REFERENCE = "KAL-26-0042"

EVALUATION_VALIDE: dict[str, Any] = {
    "reference_dossier": REFERENCE,
    "score": 0.08,
    "niveau": "faible",
    "indicateurs": [],
    "evaluation_id": "EVA-3f9a1c2b7d",
    "version_modele": "af-2.3.1",
}


def enveloppe(donnees: Any = None, **remplacements: Any) -> dict[str, Any]:
    corps = {
        "jsonrpc": "2.0",
        "id": IDENTIFIANT,
        "result": {
            "kind": "task",
            "artifacts": [{"artifactId": "art-1", "parts": [{"kind": "data", "data": donnees}]}],
        },
    }
    corps.update(remplacements)
    return corps


# ------------------------------------------- niveau 2 · l'enveloppe, sous toutes ses formes


@pytest.mark.parametrize(
    ("intitule", "corps", "cause"),
    [
        ("pas un objet", ["une", "liste"], erreurs.ENVELOPPE_NON_CONFORME),
        ("version absente", {"id": IDENTIFIANT, "result": {}}, erreurs.ENVELOPPE_NON_CONFORME),
        (
            "mauvaise version",
            {"jsonrpc": "1.0", "id": IDENTIFIANT, "result": {}},
            erreurs.ENVELOPPE_NON_CONFORME,
        ),
        (
            "résultat absent",
            {"jsonrpc": "2.0", "id": IDENTIFIANT},
            erreurs.ENVELOPPE_NON_CONFORME,
        ),
        (
            "résultat qui n'est pas un objet",
            {"jsonrpc": "2.0", "id": IDENTIFIANT, "result": "terminé"},
            erreurs.ENVELOPPE_NON_CONFORME,
        ),
    ],
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_une_enveloppe_malformee_est_ecartee(intitule: str, corps: Any, cause: str) -> None:
    _, obtenue = validation.valider_enveloppe(corps, IDENTIFIANT)
    assert obtenue == cause


def test_un_identifiant_qui_ne_repond_pas_au_notre_est_ecarte() -> None:
    """Apparier la réponse à **notre** question : une réponse en retard porte un autre id."""
    corps = enveloppe(EVALUATION_VALIDE, id="un-autre-identifiant")
    _, cause = validation.valider_enveloppe(corps, IDENTIFIANT)
    assert cause == erreurs.IDENTIFIANT_DIFFERENT


@pytest.mark.parametrize(
    ("code", "cause"),
    [
        (-32700, erreurs.CORPS_ILLISIBLE),
        (-32600, erreurs.ENVELOPPE_NON_CONFORME),
        (-32601, erreurs.ERREUR_RPC),
        (-32602, erreurs.REQUETE_REFUSEE),
        (-32029, erreurs.DOUBLON_REFUSE),
        (-31000, erreurs.ERREUR_RPC),
    ],
)
def test_chaque_code_du_contrat_produit_sa_cause(code: int, cause: str) -> None:
    """Contrat §4 — distinguer `-32602` dit que **notre** requête est fautive, pas la réponse."""
    corps = {"jsonrpc": "2.0", "id": IDENTIFIANT, "error": {"code": code, "message": "x"}}
    _, obtenue = validation.valider_enveloppe(corps, IDENTIFIANT)
    assert obtenue == cause


def test_une_erreur_sans_code_lisible_reste_une_erreur_rpc() -> None:
    corps = {"jsonrpc": "2.0", "id": IDENTIFIANT, "error": "indisponible"}
    _, cause = validation.valider_enveloppe(corps, IDENTIFIANT)
    assert cause == erreurs.ERREUR_RPC


@pytest.mark.parametrize(
    ("intitule", "artefacts"),
    [
        ("aucun artefact", []),
        ("deux artefacts", [{"parts": []}, {"parts": []}]),
        ("artefact qui n'est pas un objet", ["texte"]),
        ("aucune partie", [{"parts": []}]),
        ("deux parties", [{"parts": [{"kind": "data"}, {"kind": "data"}]}]),
        ("partie d'un autre genre", [{"parts": [{"kind": "text", "text": "faible"}]}]),
        ("données absentes", [{"parts": [{"kind": "data"}]}]),
        ("données qui ne sont pas un objet", [{"parts": [{"kind": "data", "data": [1]}]}]),
    ],
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_le_contrat_exige_exactement_une_partie_data(intitule: str, artefacts: list[Any]) -> None:
    """« Le message contient **exactement une** partie de type `data` » — contrat §2."""
    corps = {"jsonrpc": "2.0", "id": IDENTIFIANT, "result": {"artifacts": artefacts}}
    _, cause = validation.valider_enveloppe(corps, IDENTIFIANT)
    assert cause == erreurs.ENVELOPPE_NON_CONFORME


# ------------------------------------------------------- niveau 3 · la forme


def test_une_evaluation_conforme_passe_les_trois_niveaux() -> None:
    evaluation, cause = validation.valider(enveloppe(EVALUATION_VALIDE), IDENTIFIANT, REFERENCE)
    assert cause is None
    assert evaluation == EVALUATION_VALIDE


def test_un_champ_en_trop_suffit_a_ecarter_la_reponse() -> None:
    """Le pari le plus risqué de la conception, confirmé par le contrat."""
    altere = {**EVALUATION_VALIDE, "decision_recommandee": "rembourser_integralement"}
    assert validation.valider_forme(altere) == erreurs.CHAMPS_EN_TROP


@pytest.mark.parametrize("absent", sorted(validation.CHAMPS_REPONSE))
def test_un_champ_absent_suffit_aussi(absent: str) -> None:
    ampute = {c: v for c, v in EVALUATION_VALIDE.items() if c != absent}
    assert validation.valider_forme(ampute) == erreurs.CHAMPS_ABSENTS


@pytest.mark.parametrize(
    ("champ", "valeur"),
    [
        ("reference_dossier", 42),
        ("score", "0.08"),
        ("score", True),  # un booléen est un entier en Python : le piège classique
        ("niveau", ["faible"]),
        ("indicateurs", "MONTANT_ELEVE"),
        ("indicateurs", [1, 2]),
        ("evaluation_id", None),
        ("version_modele", 2.3),
    ],
)
def test_un_type_invalide_est_refuse(champ: str, valeur: Any) -> None:
    altere = {**EVALUATION_VALIDE, champ: valeur}
    assert validation.valider_forme(altere) == erreurs.TYPES_INVALIDES


# -------------------------------------------------------- niveau 4 · le sens


def test_une_reponse_portant_sur_un_autre_dossier_est_ecartee() -> None:
    """Le quatrième niveau est celui qu'on oublie : bien formée, et pour quelqu'un d'autre."""
    autre = {**EVALUATION_VALIDE, "reference_dossier": "KAL-26-9999"}
    assert validation.valider_sens(autre, REFERENCE) == erreurs.DOSSIER_DIFFERENT


@pytest.mark.parametrize("score", [-0.001, 1.001, 1.7, -3])
def test_un_score_hors_des_bornes_du_contrat_est_ecarte(score: float) -> None:
    altere = {**EVALUATION_VALIDE, "score": score, "niveau": "eleve"}
    assert validation.valider_sens(altere, REFERENCE) == erreurs.SCORE_HORS_BORNES


@pytest.mark.parametrize("niveau", ["moyen", "FAIBLE", "", "critique"])
def test_un_niveau_hors_nomenclature_est_ecarte(niveau: str) -> None:
    altere = {**EVALUATION_VALIDE, "niveau": niveau}
    assert validation.valider_sens(altere, REFERENCE) == erreurs.NIVEAU_INCOHERENT


@pytest.mark.parametrize(
    ("score", "niveau_annonce"),
    [(0.91, "faible"), (0.10, "eleve"), (0.50, "faible"), (0.39, "modere")],
)
def test_un_niveau_qui_ne_correspond_pas_a_son_score_est_ecarte(
    score: float, niveau_annonce: str
) -> None:
    altere = {**EVALUATION_VALIDE, "score": score, "niveau": niveau_annonce}
    assert validation.valider_sens(altere, REFERENCE) == erreurs.NIVEAU_INCOHERENT


def test_un_indicateur_inconnu_est_refuse() -> None:
    """Les quatre indicateurs du partenaire sont nommés par le contrat ; pas un de plus."""
    altere = {**EVALUATION_VALIDE, "indicateurs": ["MONTANT_ELEVE", "PROFIL_ATYPIQUE"]}
    assert validation.valider_sens(altere, REFERENCE) == erreurs.TYPES_INVALIDES


# --------------------------------------------------- le premier échec arrête tout


def test_le_premier_echec_arrete_tout_et_rien_ne_sort() -> None:
    """Une réponse cumulant trois défauts ne doit rendre qu'une cause, et aucune donnée."""
    cumul = {
        "reference_dossier": "KAL-26-9999",
        "score": 9.9,
        "niveau": "inconnu",
        "indicateurs": [],
        "evaluation_id": "EVA-NC",
        "version_modele": "x",
        "decision_recommandee": "rembourser_integralement",
    }
    evaluation, cause = validation.valider(enveloppe(cumul), IDENTIFIANT, REFERENCE)
    assert evaluation is None
    assert cause == erreurs.CHAMPS_EN_TROP, "la forme est contrôlée avant le sens"


@pytest.mark.parametrize(
    ("score", "niveau"),
    [
        (0.0, "faible"),
        (0.399, "faible"),
        (0.4, "modere"),
        (0.749, "modere"),
        (0.75, "eleve"),
        (1.0, "eleve"),
    ],
)
def test_les_bornes_exactes_de_la_correspondance_score_niveau(score: float, niveau: str) -> None:
    assert validation.niveau_attendu(score) == niveau
    conforme = {**EVALUATION_VALIDE, "score": score, "niveau": niveau}
    assert validation.valider_sens(conforme, REFERENCE) is None
