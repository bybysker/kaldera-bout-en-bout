"""S12 à S18 — ce que les 28 scénarios fournis ne mettent pas à l'épreuve.

S15 et S16 entrent par le répartiteur plutôt que par la porte publique : la question avait été
laissée ouverte en conception — publier le motif de refus de réception, ou l'accepter comme un
contrôle interne. **Tranché pour le contrôle interne** : publier un motif de refus de réception
dans la fiche reviendrait à exposer à un gestionnaire une défaillance de code qui ne le concerne
pas, et le contrat d'intégration ne prévoit pas ce champ.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

import kaldera
from kaldera.dossier import Dossier, SectionDejaPubliee
from kaldera.orchestration import bornes, plan
from kaldera.orchestration.repartiteur import ReceptionRefusee, Repartiteur
from kaldera.partenaire import validation

from .harnais_c2 import SCENARIOS, Partenaire, traiter_lot


def _scenario(identifiant: str) -> dict[str, Any]:
    (trouve,) = [s for s in SCENARIOS if s["id"] == identifiant]
    return trouve


# ------------------------------------- S12 · les demandes d'un lot sont indépendantes


def test_s12_une_demande_lente_ne_retarde_pas_les_autres(partenaire: Partenaire) -> None:
    """specs §12 — « le traitement d'une demande n'est jamais retardé par celui d'une autre ».

    Le harnais fourni accorde 10 s par demande du lot : un traitement séquentiel passerait sans
    rien démontrer. Ce test borne le lot entier, pas chaque demande.
    """
    scenario = _scenario("PAN-02")  # partenaire lent à 5 s, trois demandes
    partenaire.preparer(scenario["partenaire"])
    debut = time.perf_counter()
    resultat, _ = traiter_lot(scenario["demandes"], partenaire)
    duree = time.perf_counter() - debut

    assert len(resultat["fiches"]) == len(scenario["demandes"])
    plafond = bornes.BORNES["duree_max_s"] * len(scenario["demandes"])
    assert duree <= plafond, (
        f"lot de {len(scenario['demandes'])} demandes traité en {duree:.1f} s "
        f"(plafond {plafond} s) — l'abandon à {bornes.BORNES['partenaire_delai_s']} s "
        "ne tient pas, ou une demande en attend une autre"
    )


def test_s12_bis_aucune_demande_n_attend_au_dela_du_delai_d_abandon(
    partenaire: Partenaire,
) -> None:
    """Le partenaire est lent à 5 s ; nous abandonnons à 3. Chaque demande doit le faire seule."""
    scenario = _scenario("PAN-02")
    partenaire.preparer(scenario["partenaire"])
    for demande in scenario["demandes"]:
        debut = time.perf_counter()
        kaldera.traiter_demande(demande, partenaire_url=partenaire.url)
        duree = time.perf_counter() - debut
        assert duree < 5.0, f"{demande['reference']} a attendu {duree:.1f} s"


# ------------------------------- S13-S14 · la borne des trois tentatives de pièces


def test_s13_la_borne_de_tentatives_est_publiee_et_vaut_trois() -> None:
    """C'est une borne **métier** : le nombre de chances laissées à un assuré."""
    assert kaldera.bornes()["pieces_tentatives_max"] == 3


def test_s14_un_assure_qui_redepose_sans_fin_ne_boucle_pas(partenaire: Partenaire) -> None:
    """Dix dépôts illisibles : le traitement s'arrête, et l'arrêt est nommé."""
    scenario = _scenario("BCL-01")
    demande = dict(scenario["demandes"][0])
    illisible = {"type": "facture", "lisible": False, "montant": 500.0}
    demande["espace_assure"] = {"depots": [dict(illisible) for _ in range(10)]}

    partenaire.preparer(scenario["partenaire"])
    fiche = kaldera.traiter_demande(demande, partenaire_url=partenaire.url)

    assert fiche["issue"] == "escalade"
    assert fiche["arret"] is not None
    assert fiche["arret"]["borne"] in (
        bornes.PIECES_TENTATIVES_EPUISEES,
        bornes.PIECES_SANS_DEPOT_RESTANT,
    )
    etapes_pieces = [e for e in fiche["trace"] if e["action"] == plan.PIECES]
    assert len(etapes_pieces) <= kaldera.bornes()["pieces_tentatives_max"], (
        f"{len(etapes_pieces)} passages par le contrôle des pièces"
    )


# ------------------------------------------ S15 · un agent qui sort de sa frontière


class AgentHorsFrontiere:
    """Un agent qui tente d'écrire une section dont il n'est pas l'auteur."""

    NOM = "eligibilite"
    SECTION = "eligibilite"

    @staticmethod
    def traiter(entrees: dict[str, Any]) -> dict[str, Any]:
        return {
            "section": "issue",  # ce n'est pas la sienne
            "contenu": {"issue": "decision", "decision": "acceptee"},
            "verdict": "recevable",
            "travail": {},
        }


def test_s15_une_section_rendue_par_le_mauvais_agent_est_refusee(
    partenaire: Partenaire,
) -> None:
    """La réception est stricte : la partie attendue, et rien d'autre.

    Sans ce contrôle, un agent pourrait conclure une demande à la place de l'agent de décision,
    et la trace le montrerait comme auteur de deux sections — `EX-2` tomberait silencieusement.
    """
    repartiteur = Repartiteur(partenaire.url)
    with pytest.raises(ReceptionRefusee):
        repartiteur._receptionner(AgentHorsFrontiere, AgentHorsFrontiere.traiter({}))


def test_s15_bis_une_section_ne_peut_etre_publiee_deux_fois() -> None:
    """Le dossier refuse l'écrasement : c'est ce qui rend « un auteur par section » vrai."""
    dossier = Dossier({"reference": "KAL-26-0001"})
    dossier.publier("eligibilite", {"eligible": True, "motifs": []}, "eligibilite")
    with pytest.raises(SectionDejaPubliee):
        dossier.publier("eligibilite", {"eligible": False, "motifs": ["x"]}, "decision")


# --------------------------------------------------- S16 · un agent qui tombe en panne


class AgentDefaillant:
    """Un agent dont le code lève une exception."""

    NOM = "estimation"
    SECTION = "estimation"

    @staticmethod
    def traiter(entrees: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("défaillance simulée de l'agent")


def test_s16_un_agent_defaillant_ne_prive_pas_la_demande_de_son_issue(
    partenaire: Partenaire, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`EX-1` — « une demande ne reste jamais sans issue ».

    Un agent qui lève une exception est un défaut de code, pas un cas métier. Mais la demande
    d'un assuré ne doit pas disparaître pour autant : elle doit ressortir par la porte, avec une
    escalade motivée, pour qu'un humain la reprenne.
    """
    from kaldera.orchestration import repartiteur as module_repartiteur

    scenario = _scenario("NOM-01")
    partenaire.preparer(scenario["partenaire"])
    monkeypatch.setitem(module_repartiteur.AGENTS, plan.ESTIMATION, AgentDefaillant)

    fiche = kaldera.traiter_demande(scenario["demandes"][0], partenaire_url=partenaire.url)

    assert fiche["issue"] in ("decision", "escalade")
    assert isinstance(fiche["motif"], str) and fiche["motif"].strip()
    assert fiche["arret"] is not None, "une défaillance doit être signalée comme un arrêt"


# ---------------------------------- S17 · une réponse qui arrive juste sous le délai


def test_s17_une_reponse_juste_sous_le_delai_est_exploitee(partenaire: Partenaire) -> None:
    """Le partenaire répond en 2,5 s, nous abandonnons à 3 : l'avis doit être retenu."""
    scenario = _scenario("AF-01")
    partenaire.preparer({"mode": "lent", "delai_s": 2.5})
    fiche = kaldera.traiter_demande(scenario["demandes"][0], partenaire_url=partenaire.url)
    assert fiche["avis_fraude"] is not None, "un avis arrivé à temps ne doit pas être perdu"
    assert fiche["mode_degrade"] is False


def test_s17_bis_une_reponse_juste_au_dela_du_delai_est_abandonnee(
    partenaire: Partenaire,
) -> None:
    """À 3,5 s, l'avis est réputé indisponible — et la demande ressort quand même."""
    scenario = _scenario("AF-01")
    partenaire.preparer({"mode": "lent", "delai_s": 3.5})
    fiche = kaldera.traiter_demande(scenario["demandes"][0], partenaire_url=partenaire.url)
    assert fiche["avis_fraude"] is None
    assert fiche["mode_degrade"] is True
    assert fiche["issue"] in ("decision", "escalade")


# ------------------------------------------- S18 · le score aux limites exactes


@pytest.mark.parametrize(
    ("score", "niveau"),
    [
        (0.0, "faible"),
        (0.399, "faible"),
        (0.40, "modere"),
        (0.749, "modere"),
        (0.75, "eleve"),
        (1.0, "eleve"),
    ],
)
def test_s18_la_correspondance_score_niveau_tient_aux_bornes(score: float, niveau: str) -> None:
    """Contrat §3 — `faible` si < 0,40 ; `modere` si 0,40 ≤ s < 0,75 ; `eleve` si ≥ 0,75."""
    assert validation.niveau_attendu(score) == niveau


@pytest.mark.parametrize("score", [-0.01, 1.01, 1.7])
def test_s18_bis_un_score_hors_bornes_fait_ecarter_la_reponse(score: float) -> None:
    """Le contrat borne le score à [0 ; 1] : au-delà, la réponse n'engage pas le partenaire."""
    evaluation = {
        "reference_dossier": "KAL-26-0001",
        "score": score,
        "niveau": "eleve",
        "indicateurs": [],
        "evaluation_id": "EVA-1",
        "version_modele": "af-2.3.1",
    }
    assert validation.valider_sens(evaluation, "KAL-26-0001") is not None
