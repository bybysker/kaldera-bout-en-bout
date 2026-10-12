"""Le journal d'exploitation, et la règle qui prime sur son utilité.

Un journal survit à la demande, se copie, s'exporte vers un service de supervision. Y laisser un
nom ou un IBAN ruine `EX-3` plus sûrement qu'une passerelle mal filtrée — celle-ci est au moins
éprouvée à chaque exécution.

Ces tests gardent trois propriétés : aucune donnée personnelle n'entre, chaque demande est
traçable de bout en bout, et ce qui ne devrait pas arriver est signalé comme tel.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest

import kaldera
from kaldera import observabilite

from .harnais_c2 import SCENARIOS, Partenaire


@pytest.fixture
def journal_capture(tmp_path) -> Any:
    """Installe le journal dans un fichier temporaire et rend les événements lus."""
    fichier = tmp_path / "kaldera.jsonl"
    observabilite.configurer(fichier=str(fichier), console=False)

    def lire() -> list[dict[str, Any]]:
        for poignee in observabilite.journal().handlers:
            poignee.flush()
        if not fichier.exists():
            return []
        return [
            json.loads(ligne)
            for ligne in fichier.read_text(encoding="utf-8").splitlines()
            if ligne.strip()
        ]

    yield lire
    observabilite.configurer(niveau=logging.CRITICAL)


def _demande(identifiant: str) -> dict[str, Any]:
    (scenario,) = [s for s in SCENARIOS if s["id"] == identifiant]
    return scenario["demandes"][0]


# ------------------------------------- aucune donnée personnelle, jamais


@pytest.mark.parametrize("champ", observabilite.CHAMPS_INTERDITS)
def test_un_champ_personnel_est_refuse_a_l_entree(champ: str) -> None:
    """Échouer bruyamment vaut mieux qu'écrire discrètement un IBAN dans un fichier conservé."""
    with pytest.raises(observabilite.ChampInterdit):
        observabilite.noter("essai", **{champ: "valeur"})


@pytest.mark.parametrize("identifiant", ["NOM-01", "AF-05", "INV-02", "BCL-01"])
def test_aucune_valeur_personnelle_n_apparait_dans_le_journal(
    identifiant: str, partenaire: Partenaire, journal_capture: Any
) -> None:
    """Le contrôle porte sur les valeurs réelles des scénarios, pas sur les noms de champs."""
    (scenario,) = [s for s in SCENARIOS if s["id"] == identifiant]
    partenaire.preparer(scenario["partenaire"])
    demande = scenario["demandes"][0]
    kaldera.traiter_demande(demande, partenaire_url=partenaire.url)

    corps = json.dumps(journal_capture(), ensure_ascii=False)
    interdits = [
        *demande["assure"].values(),
        demande["contrat"]["numero"],
        demande["sinistre"]["description"],
    ]
    fuites = [v for v in interdits if isinstance(v, str) and v and v in corps]
    assert not fuites, f"données personnelles dans le journal : {fuites}"


def test_la_reference_du_dossier_est_le_seul_identifiant_retenu(
    partenaire: Partenaire, journal_capture: Any
) -> None:
    """Sans elle, un journal est inexploitable ; et elle ne désigne personne hors du système."""
    partenaire.preparer({"mode": "normal"})
    demande = _demande("NOM-01")
    kaldera.traiter_demande(demande, partenaire_url=partenaire.url)
    evenements = journal_capture()
    assert evenements
    assert all(e.get("reference") == demande["reference"] for e in evenements)


# ------------------------------------------- une demande traçable de bout en bout


def test_une_demande_produit_un_debut_des_etapes_et_une_fin(
    partenaire: Partenaire, journal_capture: Any
) -> None:
    partenaire.preparer({"mode": "normal"})
    fiche = kaldera.traiter_demande(_demande("NOM-01"), partenaire_url=partenaire.url)
    evenements = journal_capture()
    noms = [e["evenement"] for e in evenements]

    assert noms[0] == "demande.debut"
    assert noms[-1] == "demande.fin"
    assert noms.count("etape") == len(fiche["trace"]), (
        "chaque étape du parcours doit laisser une ligne de journal"
    )

    fin = evenements[-1]
    assert fin["issue"] == fiche["issue"]
    assert fin["etapes"] == len(fiche["trace"])
    assert isinstance(fin["duree_ms"], (int, float))


# -------------------------------------- ce qui ne devrait pas arriver est signalé


def test_l_indisponibilite_du_partenaire_est_signalee_avec_sa_cause(
    partenaire: Partenaire, journal_capture: Any
) -> None:
    """La cause et son niveau de validation : c'est ce qui dit de quel côté chercher la panne."""
    partenaire.preparer({"mode": "panne"})
    kaldera.traiter_demande(_demande("AF-05"), partenaire_url=partenaire.url)

    alertes = [e for e in journal_capture() if e["niveau"] == "warning"]
    indisponibles = [e for e in alertes if e["evenement"] == "partenaire.indisponible"]
    assert indisponibles, "une panne du partenaire doit être signalée"
    assert indisponibles[0]["cause"] == "service_indisponible"
    assert indisponibles[0]["niveau_validation"] == 1


def test_une_reponse_ecartee_est_signalee_au_niveau_ou_elle_tombe(
    partenaire: Partenaire, journal_capture: Any
) -> None:
    """Savoir qu'une réponse est tombée au niveau 3 plutôt qu'au 1 change le diagnostic."""
    (scenario,) = [s for s in SCENARIOS if s["id"] == "INV-02"]  # niveau incohérent avec le score
    partenaire.preparer(scenario["partenaire"])
    kaldera.traiter_demande(scenario["demandes"][0], partenaire_url=partenaire.url)

    ecartees = [e for e in journal_capture() if e["evenement"] == "partenaire.reponse_ecartee"]
    assert ecartees, "une réponse non conforme doit être signalée"
    assert ecartees[0]["niveau_validation"] == 4, "elle tombe au niveau du sens"


def test_une_borne_atteinte_est_signalee(partenaire: Partenaire, journal_capture: Any) -> None:
    (scenario,) = [s for s in SCENARIOS if s["id"] == "BCL-01"]
    partenaire.preparer(scenario["partenaire"])
    kaldera.traiter_demande(scenario["demandes"][0], partenaire_url=partenaire.url)

    bornes = [e for e in journal_capture() if e["evenement"] == "borne.atteinte"]
    assert bornes and bornes[0]["niveau"] == "warning"
    assert bornes[0]["borne"] == "pieces_sans_depot_restant"


# --------------------------------------------------- le journal reste discret


def test_sans_configuration_la_bibliotheque_n_ecrit_nulle_part(
    partenaire: Partenaire, capsys: pytest.CaptureFixture[str]
) -> None:
    """Une bibliothèque qui écrit sans qu'on le lui demande finit par être réduite au silence."""
    observabilite.journal().handlers.clear()
    observabilite.journal().addHandler(logging.NullHandler())
    partenaire.preparer({"mode": "normal"})
    kaldera.traiter_demande(_demande("NOM-01"), partenaire_url=partenaire.url)
    capture = capsys.readouterr()
    assert not capture.out and not capture.err


def test_chaque_ligne_est_un_objet_json_autonome(
    partenaire: Partenaire, journal_capture: Any
) -> None:
    """Un journal qu'un outil ne sait pas lire n'est qu'un fichier de plus."""
    partenaire.preparer({"mode": "normal"})
    kaldera.traiter_demande(_demande("NOM-01"), partenaire_url=partenaire.url)
    for evenement in journal_capture():
        assert {"horodatage", "niveau", "evenement"} <= set(evenement)
