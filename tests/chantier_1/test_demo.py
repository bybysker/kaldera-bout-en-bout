"""La démonstration doit dire la vérité sur ce qu'elle montre.

Un schéma qui se trompe de branche, ou qui n'allume rien parce qu'un motif lui échappe, serait
pire qu'une absence de schéma : il donnerait l'air d'une preuve. Ces tests éprouvent les vues sur
les fiches réellement produites par les 28 scénarios.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from demo import vues

from .harnais_c1 import Partenaire, scenarios, traiter_lot

RACINE = Path(__file__).resolve().parents[2]


def _fiches(scenario: dict[str, Any], partenaire: Partenaire) -> list[dict[str, Any]]:
    partenaire.preparer(scenario["partenaire"])
    resultat, _ = traiter_lot(scenario["demandes"], partenaire)
    return list(resultat["fiches"])


@pytest.mark.parametrize("scenario", scenarios())
def test_chaque_fiche_se_rattache_a_une_regle_de_la_section_10(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    """Aucun motif ne doit échapper à la lecture : sinon l'arbre de décision n'allumerait rien."""
    attendues = {numero for numero, *_ in vues.REGLES_SECTION_10} | {"borne"}
    for fiche in _fiches(scenario, partenaire):
        regle = vues.regle_appliquee(fiche)
        assert regle in attendues, (
            f"{fiche['reference']} : motif « {fiche['motif']} » rattaché à aucune règle"
        )


@pytest.mark.parametrize("scenario", scenarios())
def test_le_schema_couvre_toutes_les_etapes_de_toutes_les_traces(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    """Une étape absente du schéma disparaîtrait silencieusement de la démonstration."""
    for fiche in _fiches(scenario, partenaire):
        for etape in fiche["trace"]:
            assert etape["agent"] in vues.ETAPES_SCHEMA, f"« {etape['agent']} » hors schéma"
            assert etape["agent"] in vues.COULEUR_AGENT
            assert etape["agent"] in vues.LIBELLE_AGENT


@pytest.mark.parametrize("scenario", scenarios())
def test_la_vue_animee_se_rend_a_chaque_instant_du_parcours(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    """Dérouler le parcours ne doit jamais échouer, quel que soit l'instant choisi."""
    for fiche in _fiches(scenario, partenaire):
        for instant in range(1, len(fiche["trace"]) + 1):
            rendu = vues.vue_animee(fiche["trace"], fiche, instant)
            assert isinstance(rendu, str) and rendu.strip()
            assert "None" not in rendu, "une valeur manquante s'est glissée dans le rendu"


def test_l_arbre_n_allume_la_branche_qu_une_fois_le_parcours_acheve() -> None:
    """Tant que le parcours se déroule, l'issue n'est pas connue : rien ne doit être désigné."""
    fiche = {"motif": "Remboursement accordé : 830.00 €", "arret": None}
    assert "#0E7C7B" not in vues.arbre_decision(fiche, visible=False)
    assert "#0E7C7B" in vues.arbre_decision(fiche, visible=True)


def test_la_conformite_se_juge_sur_les_champs_que_la_recette_donne() -> None:
    """Un champ absent de l'attendu n'est pas vérifié — c'est la règle de la suite d'acceptance."""
    fiche = {
        "reference": "KAL-26-0101",
        "issue": "decision",
        "decision": "acceptee",
        "montant_rembourse": 830.0,
        "file": None,
        "mode_degrade": False,
        "arret": None,
    }
    assert vues.conforme(fiche, {"issue": "decision"})
    assert vues.conforme(fiche, {"montant_rembourse": 830.0})
    assert not vues.conforme(fiche, {"montant_rembourse": 831.0})
    assert not vues.conforme(fiche, {"decision": "refusee"})
    assert not vues.conforme(fiche, {"arret": True})


# ------------------------------------------------- la page elle-même doit s'exécuter

ECHANTILLON = ("NOM-01", "NOM-09", "AF-05", "INV-02", "PAN-01", "BCL-01")


@pytest.mark.parametrize("identifiant", ECHANTILLON)
def test_la_page_s_execute_sans_exception(identifiant: str) -> None:
    """Un scénario qui fait planter la page ne doit pas se découvrir en soutenance.

    L'échantillon couvre une catégorie chacun : nominal simple, escalade sans arrêt, anti-fraude,
    réponse invalide, panne sur un lot, et piège à boucle.
    """
    from streamlit.testing.v1 import AppTest

    page = AppTest.from_file(str(RACINE / "demo" / "app.py"), default_timeout=180)
    page.session_state["scenario"] = identifiant
    page.run()

    assert not page.exception, f"{identifiant} : {[e.value for e in page.exception]}"
    assert page.session_state["scenario"] == identifiant
    # 3 espaces racine + 3 vues assuré + 3 vues gestionnaire + 9 vues techniques
    assert len(page.tabs) == 18


def test_la_page_se_charge_dans_les_conditions_reelles_de_streamlit() -> None:
    """`streamlit run` exécute le script avec SON dossier en tête de ``sys.path``, pas la racine.

    Le harnais `AppTest`, lui, hérite du ``sys.path`` de pytest, qui contient la racine : il ne
    voit donc pas les imports qui ne résoudraient qu'ici. Ce test reproduit la condition réelle —
    c'est elle qui a laissé passer un `ModuleNotFoundError` affiché en pleine page.
    """
    import subprocess
    import sys

    chemins = [str(RACINE / "demo")] + [
        chemin for chemin in sys.path if chemin not in ("", ".", str(RACINE))
    ]
    code = (
        "import sys, runpy;"
        f"sys.path = {chemins!r};"
        f"runpy.run_path({str(RACINE / 'demo' / 'app.py')!r}, run_name='__main__')"
    )
    acheve = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=RACINE, timeout=180
    )
    sortie = acheve.stdout + acheve.stderr
    for faute in ("ModuleNotFoundError", "ImportError", "NameError", "SyntaxError"):
        assert faute not in sortie, f"{faute} au chargement de la page :\n{sortie[-800:]}"


# ------------------------------------------------- les composants d'observabilité


def test_la_chronologie_signale_les_etapes_en_echec() -> None:
    """Une étape en échec doit se distinguer visuellement, pas seulement dans le texte."""
    trace = [
        {"agent": "eligibilite", "action": "eligibilite", "duree_ms": 0.01, "statut": "ok"},
        {"agent": "antifraude", "action": "antifraude", "duree_ms": 320.0, "statut": "echec"},
    ]
    rendu = vues.chronologie(trace)
    assert "repeating-linear-gradient" in rendu, "l'échec doit être hachuré"
    assert "320" in rendu and "total" in rendu


def test_la_chronologie_ne_divise_jamais_par_zero() -> None:
    """Des étapes instantanées sont le cas courant, pas un cas limite."""
    trace = [{"agent": "decision", "action": "decision", "duree_ms": 0.0, "statut": "ok"}]
    assert vues.chronologie(trace)
    assert vues.chronologie([])


def test_la_jauge_alerte_au_dela_du_seuil() -> None:
    """Une part rejetée pour la forme, même faible, doit se voir."""
    assert "#C8432B" in vues.jauge(0.05, "rejet", alerte_au_dessus=0.0)
    assert "#C8432B" not in vues.jauge(0.0, "rejet", alerte_au_dessus=0.0)


def test_la_jauge_reste_dans_ses_bornes() -> None:
    for part in (-1.0, 0.0, 0.5, 1.0, 2.0):
        rendu = vues.jauge(part, "essai")
        assert "width:-" not in rendu


def test_les_barres_tiennent_sans_valeur() -> None:
    assert vues.barres({})
    assert "100.0%" in vues.barres({"a": 5, "b": 1})


# ------------------------------------------- l'arbre du plan conditionnel


def test_l_arbre_allume_la_branche_empruntee_et_laisse_voir_les_autres() -> None:
    """Montrer ce qui ne s'est pas passé est ce qui donne son sens à ce qui s'est passé."""
    trace = [
        {
            "agent": "eligibilite",
            "action": "eligibilite",
            "duree_ms": 0.01,
            "statut": "ok",
            "verdict": "recevable",
        },
        {
            "agent": "pieces",
            "action": "pieces",
            "duree_ms": 0.01,
            "statut": "ok",
            "verdict": "completes",
        },
    ]
    rendu = vues.arbre_orchestration(trace, len(trace))
    assert "━▶ recevable" in rendu, "la branche empruntée doit être marquée"
    assert "─▶ non recevable" in rendu, "la branche non prise doit rester visible"
    assert "Estimation" in rendu, "les étapes jamais atteintes figurent quand même"


def test_l_arbre_montre_les_deux_verdicts_d_une_etape_reprise() -> None:
    """`BCL-01` passe deux fois par les pièces : « reprise » puis « épuisé ». Les deux comptent."""
    trace = [
        {
            "agent": "eligibilite",
            "action": "eligibilite",
            "duree_ms": 0.01,
            "statut": "ok",
            "verdict": "recevable",
        },
        {
            "agent": "pieces",
            "action": "pieces",
            "duree_ms": 0.01,
            "statut": "ok",
            "verdict": "reprise",
        },
        {
            "agent": "pieces",
            "action": "pieces",
            "duree_ms": 0.01,
            "statut": "ok",
            "verdict": "epuise",
        },
    ]
    rendu = vues.arbre_orchestration(trace, len(trace))
    assert "━▶ reprise" in rendu and "━▶ dépôts épuisés" in rendu
    assert "×2" in rendu, "le compteur de passages doit se voir"


def test_l_arbre_couvre_toutes_les_transitions_du_plan() -> None:
    """Si le plan gagnait une branche, le schéma la tairait sans que rien ne le signale."""
    from kaldera.orchestration import plan

    du_schema = {(etape, verdict) for etape, sorties in vues.BRANCHES for verdict, _, _ in sorties}
    du_plan = {cle for cle in plan.PLAN if cle[0] != "decision"}
    assert du_schema == du_plan, f"le schéma et le plan divergent : {du_plan ^ du_schema}"


def test_l_arbre_tient_sans_aucune_etape() -> None:
    assert vues.arbre_orchestration([], 0)


# ------------------------------------------- la structure en trois espaces


def test_la_page_s_organise_en_trois_espaces() -> None:
    """Un courrier d'assuré et un journal d'exploitation n'ont pas le même lecteur.

    La première version mettait les dix vues sur le même plan. Ce test garde la séparation :
    si elle disparaissait, l'interface redeviendrait une interface d'auteur.
    """
    from streamlit.testing.v1 import AppTest

    page = AppTest.from_file(str(RACINE / "demo" / "app.py"), default_timeout=240).run()
    assert not page.exception, [e.value for e in page.exception]

    # `page.tabs` aplatit les onglets imbriqués : on cherche les espaces par leur libellé,
    # et on vérifie leur ordre relatif plutôt que leur position.
    libelles = [onglet.label for onglet in page.tabs]
    espaces = ["Espace assuré", "Espace gestionnaire", "Espace technique"]
    for espace in espaces:
        assert espace in libelles, f"« {espace} » a disparu de l'interface"
    positions = [libelles.index(e) for e in espaces]
    assert positions == sorted(positions), "les espaces ne sont plus dans l'ordre"

    # Chaque espace a ses propres vues : l'assuré ne voit pas le journal d'exploitation.
    for vue in ("Ma déclaration", "Mes pièces", "Ma décision"):
        assert vue in libelles
    for vue in ("Ma file", "Le dossier", "Décider"):
        assert any(v.startswith(vue) for v in libelles), vue
    for vue in ("Le flux", "L'échange A2A", "Observabilité", "Les modèles"):
        assert vue in libelles


def test_le_socle_se_teste_sans_streamlit() -> None:
    """Le partenaire simulé, le chargement et le traitement vivent hors de l'interface.

    C'est ce qui permet de les éprouver : une panne de démarrage ne doit pas se découvrir
    devant un jury.
    """
    from demo import socle

    scenarios = socle.scenarios()
    assert len(scenarios) == 28
    assert all({"id", "demandes", "attendu", "partenaire"} <= set(s) for s in scenarios)


def test_la_conformite_ne_juge_que_sur_ce_que_la_recette_dit() -> None:
    from demo import socle

    fiche = {
        "reference": "KAL-26-0101",
        "issue": "decision",
        "decision": "acceptee",
        "montant_rembourse": 830.0,
        "file": None,
        "mode_degrade": False,
        "arret": None,
    }
    assert socle.conforme(fiche, {})
    assert socle.conforme(fiche, {"issue": "decision"})
    assert not socle.conforme(fiche, {"decision": "refusee"})
    assert not socle.conforme(fiche, {"arret": True})


def test_les_chiffres_affiches_sont_ceux_que_la_suite_produit() -> None:
    """Un chiffre écrit à la main dans une démonstration se périme en silence.

    Celui-ci est confronté au nombre réellement collecté par pytest. S'ils divergent, c'est
    ici que cela se voit — pas devant un jury.
    """
    import re
    import subprocess
    import sys

    from demo.app import MUTATIONS_DETECTEES, TESTS_ACCEPTANCE, TESTS_REPRODUCTIBLES

    from .epreuve_mutations import MUTATIONS

    acheve = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=RACINE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    trouve = re.search(r"([0-9]+)(?:/[0-9]+)? tests? collected", acheve.stdout)
    assert trouve is not None, acheve.stdout[-800:] + acheve.stderr[-400:]
    assert int(trouve.group(1)) == TESTS_REPRODUCTIBLES, (
        f"la démonstration annonce {TESTS_REPRODUCTIBLES} tests, la suite en collecte "
        f"{trouve.group(1)} — mettre à jour `demo.app.TESTS_REPRODUCTIBLES`"
    )

    acceptance = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/acceptance",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=RACINE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    trouve = re.search(r"([0-9]+)(?:/[0-9]+)? tests? collected", acceptance.stdout)
    assert trouve is not None, acceptance.stdout[-800:]
    assert int(trouve.group(1)) == TESTS_ACCEPTANCE, (
        f"la démonstration annonce {TESTS_ACCEPTANCE} tests d'acceptance, il y en a "
        f"{trouve.group(1)}"
    )

    assert len(MUTATIONS) == MUTATIONS_DETECTEES, (
        f"la démonstration annonce {MUTATIONS_DETECTEES} mutations, l'épreuve en définit "
        f"{len(MUTATIONS)}"
    )
