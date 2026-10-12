"""S10 et S11 — ce qui part réellement chez le partenaire.

Aucun des 28 scénarios fournis ne regarde la charge sortante : ils vérifient l'issue, pas ce que
le système a transmis pour y parvenir. Un filtre peut donc laisser fuir une donnée pendant des
mois sans qu'un seul test ne tombe.

`EX-3` et le contrat partenaire §2.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from kaldera.partenaire import charge

from .harnais_c2 import Partenaire, scenarios, traiter

DEMANDE_TEMOIN: dict[str, Any] = {
    "reference": "KAL-26-0042",
    "assure": {
        "id_client": "CLI-99887",
        "nom": "Temoin",
        "prenom": "Alex",
        "email": "alex.temoin@exemple.fr",
        "telephone": "0600000000",
        "iban": "FR7630001007941234567890185",
        "adresse": "12 rue des Essais",
        "code_postal": "69003",
    },
    "contrat": {
        "numero": "CTR-778801",
        "formule": "confort",
        "date_souscription": "2024-01-15",
        "statut": "actif",
        "cotisations_a_jour": True,
    },
    "sinistre": {
        "type": "degat_des_eaux",
        "date_survenance": "2026-08-14",
        "date_declaration": "2026-08-16",
        "montant_declare": 1850.0,
        "description": "Fuite sous l'evier, parquet gondole dans la cuisine",
    },
    "pieces": [],
    "historique": {"sinistres_12_mois": 0},
    "espace_assure": {"depots": []},
}


# ------------------------------------------------- S10 · la liste exacte des champs


def test_s10_la_charge_porte_exactement_les_sept_champs_du_contrat() -> None:
    """Ni un de plus — le partenaire refuse tout champ inconnu — ni un de moins."""
    produite = charge.construire(DEMANDE_TEMOIN)
    assert set(produite) == set(charge.CHAMPS_AUTORISES)
    assert produite == {
        "reference_dossier": "KAL-26-0042",
        "type_sinistre": "degat_des_eaux",
        "montant_declare": 1850.0,
        "date_survenance": "2026-08-14",
        "anciennete_contrat_jours": 942,
        "sinistres_12_mois": 0,
        "departement": "69",
    }


def test_s10_bis_un_champ_ajoute_a_la_demande_ne_part_pas_tout_seul() -> None:
    """La charge se construit en partant de rien (D14) : un filtre laisserait passer ce champ."""
    demande = {**DEMANDE_TEMOIN, "scoring_interne": {"note": 0.97}}
    demande["sinistre"] = {**DEMANDE_TEMOIN["sinistre"], "commentaire_gestionnaire": "a surveiller"}
    produite = charge.construire(demande)
    assert set(produite) == set(charge.CHAMPS_AUTORISES)


# ------------------------------------------- S11 · aucune valeur personnelle témoin


def test_s11_aucune_donnee_personnelle_ne_figure_dans_la_charge_serialisee() -> None:
    """Le contrat les interdit « sous quelque forme que ce soit » — y compris en sous-chaîne."""
    corps = json.dumps(charge.construire(DEMANDE_TEMOIN), ensure_ascii=False)
    interdits = [
        *DEMANDE_TEMOIN["assure"].values(),
        DEMANDE_TEMOIN["contrat"]["numero"],
        DEMANDE_TEMOIN["sinistre"]["description"],
    ]
    fuites = [valeur for valeur in interdits if str(valeur) in corps]
    assert not fuites, f"données personnelles dans la charge : {fuites}"


def test_s11_bis_le_departement_ne_recopie_jamais_le_code_postal() -> None:
    """Le code postal complet fait partie des coordonnées interdites."""
    for code_postal, attendu in (
        ("69003", "69"),
        ("13008", "13"),
        ("97400", "974"),
        ("20137", "2A"),
        ("20620", "2B"),
    ):
        produit = charge.departement(code_postal)
        assert produit == attendu
        assert code_postal not in produit


@pytest.mark.parametrize("scenario", scenarios("antifraude"))
def test_s11_ter_sur_les_scenarios_reels_rien_de_personnel_n_atteint_le_partenaire(
    scenario: dict[str, Any], partenaire: Partenaire
) -> None:
    """Le contrôle précédent porte sur une demande témoin ; celui-ci sur les demandes du brief."""
    partenaire.preparer(scenario["partenaire"])
    for demande in scenario["demandes"]:
        traiter(demande, partenaire)
        appels = [e for e in partenaire.journal() if e.get("reference") == demande["reference"]]
        assert appels, f"{demande['reference']} : aucun appel reçu"
        for appel in appels:
            corps = appel.get("corps_brut") or ""
            interdits = [
                *demande["assure"].values(),
                demande["contrat"]["numero"],
                demande["sinistre"]["description"],
            ]
            fuites = [v for v in interdits if isinstance(v, str) and v and v in corps]
            assert not fuites, f"{demande['reference']} : {fuites}"
            assert set(appel["champs"]) == set(charge.CHAMPS_AUTORISES)
