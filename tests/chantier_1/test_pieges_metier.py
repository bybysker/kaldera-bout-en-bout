"""Les pièges que la conception a identifiés, et qu'aucun test fourni ne vérifie directement.

Trois d'entre eux sont des erreurs que nous avons nous-mêmes commises avant de les corriger :
confondre les deux situations de pièces manquantes, traiter le plafond comme un refus, et laisser
le répartiteur devenir l'auteur des sections.
"""

from __future__ import annotations

from typing import Any

import pytest

from .harnais_c1 import SCENARIOS, Partenaire, scenarios, traiter, traiter_lot


def _scenario(identifiant: str) -> dict[str, Any]:
    (trouve,) = [s for s in SCENARIOS if s["id"] == identifiant]
    return trouve


def _fiche_unique(identifiant: str, partenaire: Partenaire) -> dict[str, Any]:
    scenario = _scenario(identifiant)
    partenaire.preparer(scenario["partenaire"])
    fiche, _ = traiter(scenario["demandes"][0], partenaire)
    return fiche


# ------------------------------------------- les deux situations de pièces manquantes


def test_nom_09_aucun_depot_est_une_regle_metier_sans_arret(partenaire: Partenaire) -> None:
    """L'assuré n'a jamais rien déposé de ce type : c'est la règle de la section 5, pas une borne.

    Marquer un arrêt ici ferait passer un cas nominal pour un incident d'exécution.
    """
    fiche = _fiche_unique("NOM-09", partenaire)
    assert fiche["issue"] == "escalade"
    assert fiche["file"] == "gestionnaire"
    assert fiche["arret"] is None, f"NOM-09 ne doit porter aucun arrêt (reçu {fiche['arret']!r})"


def test_bcl_01_depots_epuises_est_une_borne_avec_arret(partenaire: Partenaire) -> None:
    """Des dépôts ont été examinés et il n'en reste aucun : c'est une borne, elle se signale."""
    fiche = _fiche_unique("BCL-01", partenaire)
    assert fiche["issue"] == "escalade"
    assert fiche["file"] == "gestionnaire"
    assert fiche["arret"] is not None, "BCL-01 doit signaler son arrêt"
    assert fiche["arret"]["borne"] == "pieces_sans_depot_restant"


# ------------------------------------------------------------------------ le plafond


def test_nom_05_le_plafond_ecrete_le_remboursement_au_lieu_de_refuser(
    partenaire: Partenaire,
) -> None:
    """4 200 € déclarés et justifiés, franchise 300 €, plafond 3 000 € → 3 000 €.

    Le plafond s'applique **après** la franchise : dans l'autre ordre, le résultat serait 2 700 €.
    """
    fiche = _fiche_unique("NOM-05", partenaire)
    assert fiche["issue"] == "decision"
    assert fiche["decision"] == "acceptee"
    assert fiche["montant_rembourse"] == pytest.approx(3_000.0)


# ------------------------------------------------- aucun défaut de clôture nulle part


@pytest.mark.parametrize("scenario", scenarios())
def test_aucune_demande_ne_sort_sur_une_cloture_manquante(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    """``cloture_manquante`` est une escalade de secours **et** un défaut : la recette doit tomber.

    Elle existe pour qu'aucune demande ne reste sans issue, pas pour être empruntée.
    """
    partenaire.preparer(scenario["partenaire"])
    resultat, _ = traiter_lot(scenario["demandes"], partenaire)
    for fiche in resultat["fiches"]:
        arret = fiche.get("arret") or {}
        assert arret.get("borne") != "cloture_manquante", (
            f"{fiche['reference']} : le flux s'est achevé sans issue — c'est un défaut"
        )


# ------------------------------------------------------- la zone de travail ne sort pas


@pytest.mark.parametrize("scenario", scenarios())
def test_la_zone_de_travail_n_apparait_pas_dans_la_fiche(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    """Compteurs, constat d'indisponibilité, journal de routage : rien de tout cela ne se publie."""
    partenaire.preparer(scenario["partenaire"])
    resultat, _ = traiter_lot(scenario["demandes"], partenaire)
    attendus = {
        "reference",
        "issue",
        "decision",
        "montant_rembourse",
        "motif",
        "file",
        "avis_fraude",
        "mode_degrade",
        "trace",
        "arret",
    }
    for fiche in resultat["fiches"]:
        en_trop = set(fiche) - attendus
        assert not en_trop, f"{fiche['reference']} : champs hors contrat dans la fiche {en_trop}"


# ---------------------------------------------- le répartiteur n'est pas dans le journal


@pytest.mark.parametrize("scenario", scenarios())
def test_le_repartiteur_n_apparait_pas_au_journal_de_bord(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    """Décision D12 — le journal de bord dit qui a fait quoi ; le greffier n'y a pas sa place."""
    partenaire.preparer(scenario["partenaire"])
    resultat, _ = traiter_lot(scenario["demandes"], partenaire)
    for fiche in resultat["fiches"]:
        agents = {etape["agent"] for etape in fiche["trace"]}
        assert "repartiteur" not in agents, (
            f"{fiche['reference']} : le répartiteur s'est journalisé"
        )
