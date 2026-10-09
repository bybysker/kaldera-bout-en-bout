"""Les bornes publiées sont des décisions, pas des réglages.

Sans ce test, desserrer une borne pour faire passer un scénario ne ferait tomber aucune
vérification : l'invariant « le journal tient dans la borne » resterait vrai, puisque la borne
aurait grandi. L'épreuve des mutations l'a montré.

Une borne peut changer — mais alors ce fichier change avec elle, et le mouvement se voit dans le
diff. C'est la décision D24 : un garde-fou ne se relève pas pour faire passer un scénario, il se
recalcule si une donnée de son calcul change, et l'ajustement se consigne.
"""

from __future__ import annotations

import pytest

import kaldera
from kaldera.orchestration import bornes as module_bornes

#: Les valeurs décidées en conception, et leur nature.
ATTENDUES = {
    "etapes_max": (10, "garde-fou"),
    "duree_max_s": (8, "garde-fou"),
    "pieces_tentatives_max": (3, "borne métier"),
    "partenaire_delai_s": (3, "contrat partenaire v2.0"),
    "etape_duree_max_s": (1, "garde-fou"),
}


def test_les_bornes_publiees_sont_celles_qui_ont_ete_decidees() -> None:
    publiees = kaldera.bornes()
    assert set(publiees) == set(ATTENDUES), (
        f"bornes publiées : {sorted(publiees)}, attendues : {sorted(ATTENDUES)}"
    )
    for nom, (valeur, nature) in ATTENDUES.items():
        assert publiees[nom] == valeur, (
            f"« {nom} » ({nature}) vaut {publiees[nom]}, décidé à {valeur} — "
            "si le changement est voulu, le consigner et mettre ce test à jour"
        )


def test_la_borne_de_duree_tient_dans_l_engagement_de_service() -> None:
    """specs_metier.md §12 — une issue en 10 secondes au plus."""
    assert 0 < kaldera.bornes()["duree_max_s"] <= 10


def test_la_sortie_ordonnee_se_declenche_avant_la_borne_publiee() -> None:
    """Il faut du temps pour écrire l'issue : la sortie part avant que la borne ne soit atteinte."""
    assert module_bornes.SORTIE_ORDONNEE_S < kaldera.bornes()["duree_max_s"], (
        "la sortie ordonnée doit laisser de la marge sous la borne publiée"
    )


@pytest.mark.parametrize("nom", sorted(ATTENDUES))
def test_chaque_borne_a_un_nom_d_arret_ou_une_raison_d_exister(nom: str) -> None:
    """Une borne sans effet observable serait un chiffre décoratif."""
    publiees = kaldera.bornes()
    assert isinstance(publiees[nom], (int, float)) and publiees[nom] > 0


def test_chaque_nom_d_arret_a_son_motif() -> None:
    """Toute borne atteinte doit produire une escalade lisible par un gestionnaire."""
    noms = (
        module_bornes.PIECES_TENTATIVES_EPUISEES,
        module_bornes.PIECES_SANS_DEPOT_RESTANT,
        module_bornes.ETAPES_MAX_ATTEINT,
        module_bornes.DUREE_MAX_ATTEINTE,
        module_bornes.CLOTURE_MANQUANTE,
    )
    for nom in noms:
        motif = module_bornes.motif(nom)
        assert isinstance(motif, str) and len(motif.strip()) >= 3, f"« {nom} » sans motif"
