"""Les sept invariants d'équipe, écrits une fois et appliqués à tous les scénarios (décision D21).

Un invariant est une propriété vraie **après n'importe quelle exécution**, quel que soit le chemin
emprunté. C'est ce qui distingue le test d'une équipe du test d'un agent : on n'y décrit pas un
déroulé attendu, on y décrit ce qui doit rester vrai dans tous les déroulés.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

import kaldera
from kaldera.orchestration import plan as plan_repartiteur

from .harnais_c1 import Partenaire, scenarios, traiter, traiter_lot

SECTIONS_METIER = ("eligibilite", "pieces", "estimation", "avis_fraude", "issue")
VALEURS_REJETEES = ("EVA-NC", "rembourser_integralement")

#: Enchaînements que le plan autorise, hors sortie ordonnée sur borne.
TRANSITIONS = {
    (etape, suivante) for (etape, _), suivante in plan_repartiteur.PLAN.items() if suivante
}


def _lot(scenario: dict[str, Any], partenaire: Partenaire) -> tuple[dict[str, Any], float]:
    partenaire.preparer(scenario["partenaire"])
    return traiter_lot(scenario["demandes"], partenaire)


# ------------------------------------------------------------------------------ I1


@pytest.mark.parametrize("scenario", scenarios())
def test_i1_une_fiche_motivee_par_demande_dans_l_ordre(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    resultat, _ = _lot(scenario, partenaire)
    fiches = resultat["fiches"]
    assert len(fiches) == len(scenario["demandes"])
    for demande, fiche in zip(scenario["demandes"], fiches, strict=True):
        assert fiche["reference"] == demande["reference"], "les fiches ne sont pas dans l'ordre"
        assert fiche["issue"] in ("decision", "escalade")
        assert isinstance(fiche["motif"], str) and fiche["motif"].strip()


# ------------------------------------------------------------------------------ I2


@pytest.mark.parametrize("scenario", scenarios())
def test_i2_aucune_demande_ne_depasse_l_engagement_de_service(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    partenaire.preparer(scenario["partenaire"])
    for demande in scenario["demandes"]:
        _, duree = traiter(demande, partenaire)
        assert duree <= 10.0, f"{demande['reference']} : traitée en {duree:.1f} s"


# ------------------------------------------------------------------------------ I3


@pytest.mark.parametrize("scenario", scenarios())
def test_i3_une_section_un_auteur_et_un_agent_une_section(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    resultat, _ = _lot(scenario, partenaire)
    for fiche in resultat["fiches"]:
        auteurs: dict[str, set[str]] = {}
        for etape in fiche["trace"]:
            for section in etape["ecrit"]:
                auteurs.setdefault(section, set()).add(etape["agent"])
        for section, agents in auteurs.items():
            assert len(agents) == 1, f"« {section} » écrite par {sorted(agents)}"
        sections_par_agent: dict[str, set[str]] = {}
        for section, agents in auteurs.items():
            for agent in agents:
                sections_par_agent.setdefault(agent, set()).add(section)
        for agent, sections in sections_par_agent.items():
            assert len(sections) == 1, f"« {agent} » a écrit {sorted(sections)}"


# ------------------------------------------------------------------------------ I4


@pytest.mark.parametrize("scenario", scenarios())
def test_i4_la_succession_des_agents_suit_le_plan(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    """Aucun enchaînement que le plan du répartiteur n'autorise pas."""
    resultat, _ = _lot(scenario, partenaire)
    for fiche in resultat["fiches"]:
        etapes = [e["action"] for e in fiche["trace"]]
        assert etapes, f"{fiche['reference']} : trace vide"
        assert etapes[0] == plan_repartiteur.PREMIERE_ETAPE, f"commence par « {etapes[0]} »"
        for avant, apres in zip(etapes, etapes[1:], strict=False):
            if apres == plan_repartiteur.DECISION and fiche.get("arret"):
                continue  # sortie ordonnée : depuis n'importe où vers la décision
            assert (avant, apres) in TRANSITIONS, (
                f"{fiche['reference']} : « {avant} » → « {apres} » hors plan"
            )
        assert etapes[-1] == plan_repartiteur.DECISION, "une demande se clôt par la décision"


# ------------------------------------------------------------------------------ I5


@pytest.mark.parametrize("scenario", scenarios())
def test_i5_le_journal_tient_dans_les_bornes_et_tout_arret_est_signale(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    resultat, _ = _lot(scenario, partenaire)
    etapes_max = kaldera.bornes()["etapes_max"]
    for fiche in resultat["fiches"]:
        assert len(fiche["trace"]) <= etapes_max
        arret = fiche.get("arret")
        assert arret is None or (isinstance(arret, dict) and arret.get("borne")), (
            f"{fiche['reference']} : arrêt sans borne nommée ({arret!r})"
        )


# ------------------------------------------------------------------------------ I6


@pytest.mark.parametrize("scenario", scenarios("invalide"))
def test_i6_rien_d_une_reponse_rejetee_ne_ressort(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    """Plus strict que la suite fournie : la trace est examinée elle aussi."""
    resultat, _ = _lot(scenario, partenaire)
    for fiche in resultat["fiches"]:
        serialisee = json.dumps(fiche, ensure_ascii=False)
        for valeur in VALEURS_REJETEES:
            assert valeur not in serialisee, f"{fiche['reference']} : « {valeur} » a fuité"
        assert fiche["avis_fraude"] is None


# ------------------------------------------------------------------------------ I7


@pytest.mark.parametrize("scenario", scenarios())
def test_i7_chaque_agent_a_ses_mesures_et_ses_appels_comptent_ses_etapes(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    resultat, _ = _lot(scenario, partenaire)
    metriques = resultat["metriques"]

    etapes_par_agent: dict[str, int] = {}
    for fiche in resultat["fiches"]:
        for etape in fiche["trace"]:
            etapes_par_agent[etape["agent"]] = etapes_par_agent.get(etape["agent"], 0) + 1

    for agent, nombre in etapes_par_agent.items():
        assert agent in metriques, f"aucune mesure pour « {agent} »"
        for cle in ("appels", "echecs", "latence_ms", "appels_externes"):
            valeur = metriques[agent].get(cle)
            assert isinstance(valeur, (int, float)) and not isinstance(valeur, bool)
        assert metriques[agent]["appels"] == nombre, (
            f"« {agent} » : {metriques[agent]['appels']} appels mesurés pour {nombre} étapes"
        )

    assert set(metriques) == set(etapes_par_agent), (
        "les mesures et le journal ne nomment pas les mêmes agents"
    )
