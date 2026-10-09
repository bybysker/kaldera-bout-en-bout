"""Les deux aides au gestionnaire — troisième cercle de la doctrine.

Hors du système, au service d'un humain qui décide. Aucune contrainte de service ne s'y
applique, mais deux garanties restent : elles ne décident rien, et elles ne voient pas plus du
dossier que le relecteur.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from demo.agence import assistance
from kaldera import llm
from tests.chantier_2.test_revue import DEMANDE, FICHE, ModeleFictif


def test_sans_modele_les_aides_se_taisent_proprement() -> None:
    """Leur absence est un non-événement : le gestionnaire travaille comme avant."""
    muette = assistance.synthese(FICHE, DEMANDE, fabrique=lambda: None)
    assert not muette["disponible"] and muette["texte"] == ""

    sans = assistance.suggestion(FICHE, DEMANDE, fabrique=lambda: None)
    assert not sans["disponible"] and sans["suite"] is None


def test_une_suggestion_sans_contre_argument_est_ecartee() -> None:
    """Un conseil qui ne dit pas ce qui lui résiste se fait suivre sans être pesé."""
    modele = ModeleFictif(
        {"suite": "accepter", "confiance": "forte", "parce_que": "le dossier est complet"}
    )
    avis = assistance.suggestion(FICHE, DEMANDE, fabrique=modele)
    assert not avis["disponible"]
    assert "contre-argument" in avis["cause"]


def test_une_suite_hors_nomenclature_est_ecartee() -> None:
    modele = ModeleFictif(
        {"suite": "classer", "parce_que": "rien à faire", "contre": "peut-être si"}
    )
    assert not assistance.suggestion(FICHE, DEMANDE, fabrique=modele)["disponible"]


def test_une_suggestion_complete_est_retenue_avec_son_contre() -> None:
    modele = ModeleFictif(
        {
            "suite": "accepter",
            "confiance": "moyenne",
            "parce_que": "Les pièces sont complètes et le montant cohérent.",
            "contre": "L'ancienneté du contrat reste faible pour un sinistre de ce montant.",
        }
    )
    avis = assistance.suggestion(FICHE, DEMANDE, fabrique=modele)
    assert avis["disponible"]
    assert avis["suite"] == "accepter"
    assert avis["confiance"] == "moyenne"
    assert avis["contre"], "le contre-argument accompagne toujours le conseil"


def test_une_confiance_hors_nomenclature_retombe_sur_faible() -> None:
    """Dans le doute, la prudence — pas l'affirmation."""
    modele = ModeleFictif(
        {"suite": "refuser", "confiance": "certaine", "parce_que": "x", "contre": "y"}
    )
    assert assistance.suggestion(FICHE, DEMANDE, fabrique=modele)["confiance"] == "faible"


def test_les_aides_ne_voient_aucune_donnee_personnelle() -> None:
    """Un gestionnaire a besoin du nom de l'assuré ; le modèle qui l'aide, non."""
    for aide in (assistance.synthese, assistance.suggestion):
        modele = ModeleFictif({"suite": "accepter", "parce_que": "x", "contre": "y"})
        aide(FICHE, DEMANDE, fabrique=modele)
        envoye = chr(10).join(contenu for _, contenu in modele.recu)
        interdits = [
            *DEMANDE["assure"].values(),
            DEMANDE["contrat"]["numero"],
            DEMANDE["sinistre"]["description"],
        ]
        fuites = [v for v in interdits if isinstance(v, str) and v and v in envoye]
        assert not fuites, f"{aide.__name__} : {fuites}"


def test_les_aides_ne_modifient_jamais_la_fiche() -> None:
    avant = json.dumps(FICHE, sort_keys=True)
    assistance.synthese(FICHE, DEMANDE, fabrique=ModeleFictif("un résumé"))
    assistance.suggestion(
        FICHE,
        DEMANDE,
        fabrique=ModeleFictif({"suite": "accepter", "parce_que": "x", "contre": "y"}),
    )
    assert json.dumps(FICHE, sort_keys=True) == avant


def test_une_synthese_vide_est_signalee_plutot_que_rendue() -> None:
    """Kimi renvoie parfois une réponse vide sans erreur : ne pas l'afficher comme un résumé."""
    resultat: dict[str, Any] = assistance.synthese(FICHE, DEMANDE, fabrique=ModeleFictif("   "))
    assert not resultat["disponible"]
    assert resultat["cause"] == "réponse vide"


def test_la_suggestion_ne_porte_sur_aucune_suite_par_defaut() -> None:
    """Rien n'est pré-sélectionné : un bouton déjà coché est une décision prise par la machine."""
    sans = assistance.suggestion(FICHE, DEMANDE, fabrique=lambda: None)
    assert sans["suite"] is None


# ------------------------------------------- avec un vrai modèle, et c'est la seule preuve


@pytest.mark.modele
@pytest.mark.skipif(not llm.configure(), reason="aucun modèle configuré")
def test_une_troncature_est_nommee_plutot_que_subie() -> None:
    """Le défaut que l'absence de ce test avait laissé passer.

    Avec un plafond de jetons trop bas, un modèle de raisonnement s'arrête **avant** d'avoir
    fini d'écrire son JSON. L'appelant ne voyait alors qu'un `ValueError` qui ne désignait pas
    la cause — et quatre suggestions sur dix échouaient ainsi, sans que rien ne le dise.
    """
    etriquee = assistance.suggestion(FICHE, DEMANDE, fabrique=lambda: llm.fabriquer(jetons_max=16))
    assert not etriquee["disponible"]
    assert "tronquée" in etriquee["cause"], etriquee["cause"]


@pytest.mark.modele
@pytest.mark.skipif(not llm.configure(), reason="aucun modèle configuré")
def test_les_deux_aides_aboutissent_contre_le_modele_reel() -> None:
    """Mesuré sur 10 appels chacune : 10 sur 10 exploitables, après relèvement du plafond.

    Un double ne peut pas prouver cela : c'est le modèle réel qui décide combien de jetons il
    consomme avant de répondre.
    """
    resume = assistance.synthese(FICHE, DEMANDE)
    assert resume["disponible"], resume["cause"]
    assert resume["texte"].strip()

    conseil = assistance.suggestion(FICHE, DEMANDE)
    assert conseil["disponible"], conseil["cause"]
    assert conseil["suite"] in assistance.SUITES_POSSIBLES
    assert conseil["contre"].strip(), "une suggestion sans contre-argument doit être écartée"
