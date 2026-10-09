"""Un seul appel par dossier — contrat partenaire v2.0, §6.

Ce n'est pas une préférence de conception : *« tout appel en doublon est refusé (-32029) et
signalé à l'assureur comme manquement au contrat »*. Le simulateur applique la clause, donc une
régression se verrait — mais seulement si quelqu'un la cherche. C'est ce que ces tests font.
"""

from __future__ import annotations

from typing import Any

import kaldera
from kaldera.partenaire import Passerelle, erreurs
from kaldera.partenaire.registre import Registre

from .harnais_c2 import SCENARIOS, Partenaire, traiter_lot


def _demande(identifiant: str) -> dict[str, Any]:
    (scenario,) = [s for s in SCENARIOS if s["id"] == identifiant]
    return scenario["demandes"][0]


def test_le_registre_retient_un_dossier_deja_soumis() -> None:
    registre = Registre()
    assert not registre.deja_appele("KAL-26-0201")
    registre.marquer("KAL-26-0201")
    assert registre.deja_appele("KAL-26-0201")
    assert registre.appels == 1


def test_un_second_appel_sur_le_meme_dossier_est_refuse(partenaire: Partenaire) -> None:
    """La passerelle n'émet même pas le doublon : elle rend un verdict et s'arrête.

    Émettre puis se faire refuser serait déjà un manquement : le contrat compte les appels
    reçus, pas les appels exploités.
    """
    partenaire.preparer({"mode": "normal"})
    demande = _demande("AF-01")
    passerelle = Passerelle(partenaire.url)

    premier = passerelle.consulter(demande)
    assert premier["avis"] is not None, "le premier appel doit aboutir"

    second = passerelle.consulter(demande)
    assert second["avis"] is None
    assert second["cause"] == erreurs.APPEL_DEJA_FAIT

    recus = [e for e in partenaire.journal() if e.get("reference") == demande["reference"]]
    assert len(recus) == 1, f"{len(recus)} appels reçus par le partenaire — un seul autorisé"


def test_aucun_scenario_ne_produit_de_doublon(partenaire: Partenaire) -> None:
    """Sur les sept scénarios anti-fraude, aucun dossier ne doit être soumis deux fois."""
    for scenario in [s for s in SCENARIOS if s["categorie"] in ("antifraude", "invalide", "panne")]:
        partenaire.preparer(scenario["partenaire"])
        traiter_lot(scenario["demandes"], partenaire)
        journal = partenaire.journal()
        for demande in scenario["demandes"]:
            recus = [e for e in journal if e.get("reference") == demande["reference"]]
            assert len(recus) <= 1, (
                f"{scenario['id']} / {demande['reference']} : {len(recus)} appels"
            )
            assert not any(e.get("doublon") for e in recus), (
                f"{scenario['id']} : le partenaire a signalé un doublon"
            )


def test_le_registre_ne_traverse_pas_les_demandes(partenaire: Partenaire) -> None:
    """Décision D8 — rien n'est partagé entre deux demandes, pas même le registre.

    Si le registre était commun au lot, la deuxième demande à risque ne serait jamais évaluée.
    """
    partenaire.preparer({"mode": "normal"})
    demandes = [_demande("AF-01"), _demande("AF-02")]
    resultat = kaldera.traiter_lot(demandes, partenaire_url=partenaire.url)

    avis = [f["avis_fraude"] for f in resultat["fiches"]]
    assert all(a is not None for a in avis), "chaque demande à risque doit obtenir son propre avis"
