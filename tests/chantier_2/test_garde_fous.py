"""Les garde-fous, enfin éprouvés.

C'était la dette la plus ancienne du projet, signalée dès la fin du chantier 1 : **quatre des
cinq noms d'arrêt étaient du code que la recette n'atteignait jamais.** La mesure de couverture
l'a confirmée sans détour.

Un garde-fou non éprouvé est pire qu'un garde-fou absent : il donne l'impression d'une
protection. Ces tests les déclenchent un par un, en resserrant les bornes plutôt qu'en
fabriquant des situations invraisemblables — resserrer une borne de 10 étapes à 2 est le moyen
le plus court d'arriver au même endroit qu'une demande pathologique.
"""

from __future__ import annotations

from typing import Any

import pytest

import kaldera
from kaldera.orchestration import bornes, plan
from kaldera.orchestration import repartiteur as module_repartiteur
from kaldera.partenaire import Passerelle, erreurs

from .harnais_c2 import SCENARIOS, Partenaire


def _demande(identifiant: str) -> dict[str, Any]:
    (scenario,) = [s for s in SCENARIOS if s["id"] == identifiant]
    return scenario["demandes"][0]


# ------------------------------------------------------- les bornes d'exécution


def test_etapes_max_atteint_produit_une_sortie_ordonnee(
    partenaire: Partenaire, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le garde-fou le plus brutal : plus d'étapes disponibles, et pourtant une issue."""
    monkeypatch.setitem(bornes.BORNES, "etapes_max", 2)
    partenaire.preparer({"mode": "normal"})
    fiche = kaldera.traiter_demande(_demande("NOM-01"), partenaire_url=partenaire.url)

    assert fiche["issue"] == "escalade", "jamais d'erreur en guise de résultat"
    assert fiche["file"] == "gestionnaire"
    assert fiche["arret"]["borne"] == bornes.ETAPES_MAX_ATTEINT
    assert len(fiche["trace"]) <= 2
    assert fiche["motif"].strip()


def test_duree_max_atteinte_produit_une_sortie_ordonnee(
    partenaire: Partenaire, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La sortie se déclenche avant la borne publiée : il faut du temps pour écrire l'issue."""
    monkeypatch.setattr(bornes, "SORTIE_ORDONNEE_S", 0.0)
    partenaire.preparer({"mode": "normal"})
    fiche = kaldera.traiter_demande(_demande("NOM-01"), partenaire_url=partenaire.url)

    assert fiche["issue"] == "escalade"
    assert fiche["arret"]["borne"] == bornes.DUREE_MAX_ATTEINTE
    assert fiche["motif"].strip()


def test_pieces_tentatives_epuisees_est_une_borne_metier(
    partenaire: Partenaire, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Le nombre de chances laissées à un assuré engage le service rendu, pas la technique."""
    monkeypatch.setitem(bornes.BORNES, "pieces_tentatives_max", 1)
    scenario = _demande("BCL-01")
    demande = dict(scenario)
    demande["espace_assure"] = {
        "depots": [{"type": "facture", "lisible": False, "montant": 500.0} for _ in range(5)]
    }
    partenaire.preparer({"mode": "normal"})
    fiche = kaldera.traiter_demande(demande, partenaire_url=partenaire.url)

    assert fiche["arret"]["borne"] == bornes.PIECES_TENTATIVES_EPUISEES
    passages = [e for e in fiche["trace"] if e["action"] == plan.PIECES]
    assert len(passages) <= 1


# ------------------------------------------------- le filet de dernier recours


class DecisionMuette:
    """Un agent de décision qui ne publie rien — le défaut que `cloture_manquante` rattrape."""

    NOM = "decision"
    SECTION = "issue"

    @staticmethod
    def traiter(entrees: dict[str, Any]) -> dict[str, Any]:
        return {"section": None, "contenu": None, "verdict": "close", "travail": {}}


def test_cloture_manquante_rattrape_une_demande_sans_issue(
    partenaire: Partenaire, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`EX-1` tient même quand l'agent chargé de conclure ne conclut pas.

    Ce cas ne devrait jamais se produire — c'est un défaut de code. Mais la demande d'un assuré
    ne disparaît pas pour un défaut de code : elle ressort avec une escalade de secours.
    """
    monkeypatch.setitem(module_repartiteur.AGENTS, plan.DECISION, DecisionMuette)
    partenaire.preparer({"mode": "normal"})
    fiche = kaldera.traiter_demande(_demande("NOM-01"), partenaire_url=partenaire.url)

    assert fiche["issue"] == "escalade"
    assert fiche["arret"]["borne"] == bornes.CLOTURE_MANQUANTE
    assert fiche["motif"].strip()
    secours = [e for e in fiche["trace"] if e["action"] == "secours"]
    assert secours and secours[0]["statut"] == "echec", (
        "le secours doit être visible dans la trace, pas silencieux"
    )


@pytest.mark.parametrize(
    "nom",
    [
        bornes.PIECES_TENTATIVES_EPUISEES,
        bornes.PIECES_SANS_DEPOT_RESTANT,
        bornes.ETAPES_MAX_ATTEINT,
        bornes.DUREE_MAX_ATTEINTE,
        bornes.CLOTURE_MANQUANTE,
        bornes.AGENT_DEFAILLANT,
    ],
)
def test_chaque_nom_d_arret_porte_un_motif_lisible_par_un_gestionnaire(nom: str) -> None:
    motif = bornes.motif(nom)
    assert len(motif) > 20
    assert "exception" not in motif.lower() and "error" not in motif.lower(), (
        "un gestionnaire n'a pas à lire un vocabulaire technique"
    )


# ----------------------------------------- le transport, de chaque côté du mur


def test_un_jeton_refuse_est_une_cause_distincte(
    partenaire: Partenaire, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HTTP 401 — contrat §4. La distinguer d'une panne évite de chercher au mauvais endroit.

    Le simulateur lit la même variable d'environnement que la passerelle : la changer
    désaccorderait les deux côtés en même temps, et le jeton resterait valide. On ne désaccorde
    donc que le client.
    """
    from kaldera.partenaire import passerelle as module_passerelle

    monkeypatch.setattr(module_passerelle, "_jeton", lambda: "jeton-qui-ne-vaut-rien")
    partenaire.preparer({"mode": "normal"})
    verdict = Passerelle(partenaire.url).consulter(_demande("AF-01"))

    assert verdict["avis"] is None
    assert verdict["cause"] == erreurs.AUTHENTIFICATION_REFUSEE


def test_une_adresse_injoignable_est_une_erreur_reseau() -> None:
    """Aucune relance, dans aucun cas : la demande continue en mode dégradé."""
    verdict = Passerelle("http://127.0.0.1:9").consulter(_demande("AF-01"))
    assert verdict["avis"] is None
    assert verdict["cause"] in (erreurs.ERREUR_RESEAU, erreurs.DELAI_DEPASSE)


def test_un_partenaire_trop_lent_rend_la_main_au_delai_prevu(
    partenaire: Partenaire,
) -> None:
    partenaire.preparer({"mode": "lent", "delai_s": 4.0})
    verdict = Passerelle(partenaire.url).consulter(_demande("AF-01"))
    assert verdict["cause"] == erreurs.DELAI_DEPASSE


def test_un_service_indisponible_est_signale_comme_tel(partenaire: Partenaire) -> None:
    partenaire.preparer({"mode": "panne"})
    verdict = Passerelle(partenaire.url).consulter(_demande("AF-01"))
    assert verdict["cause"] == erreurs.SERVICE_INDISPONIBLE


def test_toute_cause_se_rattache_a_un_niveau_de_validation() -> None:
    """Sans niveau, une cause ne dit pas de quel côté chercher."""
    causes = [v for c, v in vars(erreurs).items() if c.isupper() and isinstance(v, str)]
    for cause in causes:
        assert cause in erreurs.NIVEAU, f"« {cause} » n'a pas de niveau"
