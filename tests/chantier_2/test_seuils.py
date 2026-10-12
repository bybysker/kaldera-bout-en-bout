"""S1 à S9 — trois valeurs par seuil : en dessous, **exacte**, au-dessus.

La mesure de sensibilité menée en conception a montré qu'aucun des 28 scénarios fournis ne
détecterait une erreur sur ces trois seuils tant qu'elle reste dans un intervalle large : la
carence pouvait valoir de 17 à 60 jours, l'ancienneté sensible de 72 à 1 263, le délai de
déclaration d'un vol de 2 à 365. Ce sont les trois moins bien tenus.

La valeur **exacte** est celle qui compte : c'est là que se joue la différence entre `<` et `<=`.
"""

from __future__ import annotations

import pytest

from kaldera.regles import eligibilite, indicateurs

# --------------------------------------------------- S1-S3 · la carence, 30 jours

CONTRAT = {
    "statut": "actif",
    "cotisations_a_jour": True,
    "formule": "confort",
    "date_souscription": "2026-01-01",
}


def _sinistre(survenance: str, declaration: str, type_sinistre: str = "degat_des_eaux") -> dict:
    return {
        "type": type_sinistre,
        "date_survenance": survenance,
        "date_declaration": declaration,
        "montant_declare": 1000.0,
    }


@pytest.mark.parametrize(
    ("jours", "attendu_en_carence"),
    [(29, True), (30, False), (31, False)],
    ids=["S1 · 29 jours — en carence", "S2 · 30 jours — exactement", "S3 · 31 jours"],
)
def test_carence_le_sinistre_doit_survenir_au_moins_30_jours_apres(
    jours: int, attendu_en_carence: bool
) -> None:
    """« Le sinistre est survenu **au moins** 30 jours après la souscription » : 30 passe."""
    from datetime import date, timedelta

    survenance = (date(2026, 1, 1) + timedelta(days=jours)).isoformat()
    motifs = eligibilite.motifs_non_eligibilite(CONTRAT, _sinistre(survenance, survenance))
    en_carence = any("carence" in m for m in motifs)
    assert en_carence is attendu_en_carence


# ------------------------------------- S4-S6 · l'ancienneté sensible, 90 jours (F2)


@pytest.mark.parametrize(
    ("anciennete", "attendu_declenche"),
    [(89, True), (90, False), (91, False)],
    ids=["S4 · 89 jours — sensible", "S5 · 90 jours — exactement", "S6 · 91 jours"],
)
def test_f2_l_anciennete_declenche_strictement_en_dessous_de_90_jours(
    anciennete: int, attendu_declenche: bool
) -> None:
    """« Ancienneté du contrat **inférieure à** 90 jours » : 90 ne déclenche pas."""
    presents = indicateurs.presents(
        montant_declare=1000.0,
        anciennete_jours=anciennete,
        sinistres_12_mois=0,
        montant_justifie=1000.0,
    )
    assert ("F2" in presents) is attendu_declenche


# --------------------------------- S7-S9 · le délai de déclaration d'un vol, 5 jours


@pytest.mark.parametrize(
    ("jours", "attendu_hors_delai"),
    [(4, False), (5, False), (6, True)],
    ids=["S7 · 4 jours", "S8 · 5 jours — exactement", "S9 · 6 jours — hors délai"],
)
def test_delai_de_declaration_d_un_vol_au_plus_tard_5_jours_apres(
    jours: int, attendu_hors_delai: bool
) -> None:
    """« Déclaré **au plus tard** 5 jours après » : 5 passe, 6 non."""
    from datetime import date, timedelta

    survenance = date(2026, 6, 1)
    declaration = (survenance + timedelta(days=jours)).isoformat()
    motifs = eligibilite.motifs_non_eligibilite(
        CONTRAT, _sinistre(survenance.isoformat(), declaration, "vol")
    )
    assert any("hors délai" in m for m in motifs) is attendu_hors_delai


def test_le_delai_d_un_vol_est_bien_distinct_du_delai_ordinaire() -> None:
    """Un seul délai pour tous les sinistres serait une erreur qu'aucun scénario fourni ne voit."""
    assert eligibilite.delai_declaration_max("vol") == 5
    for autre in ("degat_des_eaux", "incendie", "bris_de_glace"):
        assert eligibilite.delai_declaration_max(autre) == 30
