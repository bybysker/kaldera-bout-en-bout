"""Le client externe — ce qu'il démontre, et ce qu'il ne doit jamais faire.

Ce client n'est pas demandé par le brief. Il le challenge : il éprouve l'intégration du point de
vue de celui qui l'utilise, et met en scène la **chaîne** de minimisation — courtier, puis
Kaldera, puis le partenaire.

Ces tests gardent trois propriétés : il n'accède qu'à la porte publique, il transmet strictement
ce que le format Kaldera attend, et il n'est jamais sur le chemin de la recette.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

from demo.client_externe import courtier, depot, dossiers

from .harnais_c2 import Partenaire

RACINE = Path(__file__).resolve().parents[2]


def compter_champs(valeur: Any, ignorer: set[str] | None = None) -> int:
    """Nombre de champs feuilles — un objet imbriqué compte pour ce qu'il contient."""
    ignorer = ignorer or set()
    if isinstance(valeur, dict):
        return sum(compter_champs(v) for c, v in valeur.items() if c not in ignorer)
    if isinstance(valeur, list):
        return sum(compter_champs(v) for v in valeur)
    return 1


CLIENT = RACINE / "demo" / "client_externe"


# ------------------------------------------- il n'accède qu'à la porte publique


def test_le_client_n_importe_que_la_porte_publique() -> None:
    """S'il avait besoin de la trace ou de l'état interne, la plateforme n'exposerait pas assez."""
    interdits = {"orchestration", "agents", "dossier", "mesures", "partenaire", "regles"}
    for module in CLIENT.glob("*.py"):
        arbre = ast.parse(module.read_text(encoding="utf-8"))
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.ImportFrom) and (noeud.module or "").startswith("kaldera"):
                suite = (noeud.module or "").removeprefix("kaldera").lstrip(".")
                assert not suite, f"{module.name} importe `kaldera.{suite}`"
            if isinstance(noeud, ast.Import):
                for alias in noeud.names:
                    reste = alias.name.removeprefix("kaldera.").split(".")[0]
                    if alias.name.startswith("kaldera.") and reste in interdits:
                        pytest.fail(f"{module.name} importe `{alias.name}`")


def test_le_client_ne_lit_que_les_champs_qui_le_concernent() -> None:
    """Un courtier n'a que faire de la trace interne ni de l'arrêt sur borne."""
    assert "trace" not in depot.CHAMPS_UTILES
    assert "arret" not in depot.CHAMPS_UTILES
    assert "avis_fraude" not in depot.CHAMPS_UTILES


# ------------------------------------------------- la traduction part de rien


def test_la_traduction_ne_laisse_passer_aucun_champ_interne() -> None:
    """Décision D14 appliquée au premier échange : on écrit les champs, on ne filtre pas."""
    for dossier in dossiers.DOSSIERS:
        demande = courtier.traduire(dossier)
        assert set(demande) == set(courtier.CHAMPS_KALDERA)
        corps = json.dumps(demande, ensure_ascii=False)
        for interne in courtier.CHAMPS_INTERNES:
            assert interne not in corps, f"« {interne} » a traversé la traduction"


def test_un_champ_ajoute_au_format_courtier_ne_part_pas_tout_seul() -> None:
    dossier = {**dossiers.DOSSIERS[0], "score_appetence": 0.91, "campagne": "automne-2026"}
    demande = courtier.traduire(dossier)
    assert set(demande) == set(courtier.CHAMPS_KALDERA)
    assert "score_appetence" not in json.dumps(demande, ensure_ascii=False)


def test_les_donnees_internes_restent_chez_le_courtier() -> None:
    retenu = depot.donnees_non_transmises(dossiers.DOSSIERS[0])
    assert "taux_commission" in retenu
    assert "notes_internes" in retenu
    demande = courtier.traduire(dossiers.DOSSIERS[0])
    assert not set(retenu) & set(json.dumps(demande, ensure_ascii=False).split('"'))


@pytest.mark.parametrize(
    ("identifiant", "attendu"),
    [("CAB-26-7001", "KAL-26-7001"), ("CAB-26-7002", "KAL-26-7002")],
)
def test_la_reference_est_traduite_au_format_que_le_contrat_impose(
    identifiant: str, attendu: str
) -> None:
    """Le partenaire valide `KAL-AA-NNNN` par expression régulière : la traduction doit tenir."""
    assert courtier.reference_kaldera(identifiant) == attendu


def test_un_identifiant_courtier_inexploitable_est_refuse_avant_tout_depot() -> None:
    with pytest.raises(courtier.TraductionImpossible):
        courtier.reference_kaldera("DOSSIER-A")


def test_un_dossier_incomplet_est_refuse_avec_une_cause_lisible() -> None:
    with pytest.raises(courtier.TraductionImpossible, match="police"):
        courtier.traduire({"id_dossier": "CAB-26-7009", "client": {}, "evenement": {}})


# ------------------------------------------------ le dépôt, de bout en bout


def test_les_trois_dossiers_mènent_a_trois_issues_differentes(partenaire: Partenaire) -> None:
    """Une démonstration qui répète trois fois le même parcours ne démontre rien."""
    partenaire.preparer({"mode": "normal"})
    resultat = depot.deposer_lot(dossiers.DOSSIERS, partenaire_url=partenaire.url)
    retours = [r["retour"] for r in resultat["retours"]]

    assert retours[0]["decision"] == "acceptee"
    assert retours[1]["issue"] == "escalade"
    assert retours[2]["issue"] == "escalade"
    assert retours[1]["motif"] != retours[2]["motif"], (
        "les deux escalades doivent avoir des causes distinctes"
    )
    for retour in retours:
        assert isinstance(retour["motif"], str) and retour["motif"].strip()


def test_chaque_retour_porte_une_suite_a_donner(partenaire: Partenaire) -> None:
    """Un courtier agit sur une fiche ; lire un nom de file n'est pas son métier."""
    partenaire.preparer({"mode": "normal"})
    resultat = depot.deposer_lot(dossiers.DOSSIERS, partenaire_url=partenaire.url)
    for retour in resultat["retours"]:
        assert isinstance(retour["suite"], str) and len(retour["suite"]) > 20


def test_la_chaine_de_minimisation_se_resserre_a_chaque_frontiere(
    partenaire: Partenaire,
) -> None:
    """Courtier → Kaldera → partenaire : chaque passage retire des données, aucun n'en ajoute."""
    from kaldera.partenaire import charge

    partenaire.preparer({"mode": "normal"})
    dossier = dossiers.par_identifiant("CAB-26-7002")  # celui qui déclenche l'anti-fraude
    resultat = depot.deposer(dossier, partenaire_url=partenaire.url)

    # Les champs feuilles, pas les clés de premier niveau : `assure` compte pour huit.
    # `intitule` et `attendu` servent à la démonstration et ne font pas partie du format.
    demonstration = {"intitule", "attendu"}
    chez_le_courtier = compter_champs(dossier, ignorer=demonstration)
    chez_kaldera = compter_champs(resultat["demande_transmise"])
    chez_le_partenaire = len(charge.CHAMPS_AUTORISES)

    assert chez_le_courtier > chez_kaldera > chez_le_partenaire, (
        f"la chaîne ne se resserre pas : {chez_le_courtier} → {chez_kaldera} → {chez_le_partenaire}"
    )

    appels = [
        e for e in partenaire.journal() if e.get("reference") == resultat["retour"]["reference"]
    ]
    assert appels, "ce dossier doit déclencher une consultation"
    recu = appels[0].get("corps_brut") or ""
    client = dossier["client"]
    for valeur in (client["nom"], client["iban"], client["courriel"], client["adresse"]):
        assert valeur not in recu, f"« {valeur} » est arrivé chez le partenaire"
    for interne in courtier.CHAMPS_INTERNES:
        assert interne not in recu


# ----------------------------------- il n'est jamais sur le chemin de la recette


def test_la_suite_d_acceptance_n_importe_jamais_le_client_externe() -> None:
    """Les tests fournis entrent par la porte publique, directement. Le client reste à côté."""
    for module in (RACINE / "tests" / "acceptance").glob("*.py"):
        source = module.read_text(encoding="utf-8")
        assert "client_externe" not in source, f"{module.name} dépend du client externe"


def test_le_paquet_kaldera_ignore_l_existence_du_client() -> None:
    """La dépendance ne va que dans un sens : le client consomme, il n'est pas consommé."""
    for module in (RACINE / "src" / "kaldera").rglob("*.py"):
        assert "client_externe" not in module.read_text(encoding="utf-8")
