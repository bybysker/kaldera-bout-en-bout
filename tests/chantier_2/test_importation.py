"""Le dépôt de pièces réelles — et les trois règles qui l'encadrent.

Déposer de vrais fichiers change ce que la démonstration prouve : on ne vérifie plus que le
système traite un cas préparé, mais un dossier qu'on vient de lui donner.

Le risque est symétrique : un dossier d'assurance contient des pièces d'identité, des factures,
des photos d'intérieur. Ces tests gardent le fait que rien de tout cela ne traverse.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from demo.client_externe import courtier, dossiers, importation


def depot_complet(type_sinistre: str = "degat_des_eaux") -> importation.Depot:
    depot = importation.Depot()
    depot.ajouter("facture", "facture-plombier.pdf", 48_000, montant=1400.0)
    if type_sinistre == "vol":
        depot.ajouter("depot_plainte", "plainte.pdf", 32_000)
    else:
        depot.ajouter("photo", "degats-couloir.jpg", 220_000)
    return depot


# ------------------------------------------- rien du contenu ne traverse


def test_une_piece_ne_transmet_ni_son_nom_ni_son_contenu() -> None:
    """La section 3 des spécifications ne prévoit qu'un type, un booléen et un montant."""
    piece = importation.PieceDeposee("facture", "facture-plombier.pdf", 48_000, montant=1400.0)
    produite = piece.en_piece()
    assert set(produite) == {"type", "lisible", "montant"}
    assert "facture-plombier.pdf" not in json.dumps(produite)


def test_une_photo_ne_porte_pas_de_montant() -> None:
    """Seules les factures en portent un : en ajouter un ailleurs serait une donnée inventée."""
    piece = importation.PieceDeposee("photo", "degats.jpg", 220_000)
    assert set(piece.en_piece()) == {"type", "lisible"}


def test_la_demande_construite_ne_porte_que_les_champs_attendus() -> None:
    demande = importation.construire_demande(
        dossiers.DOSSIERS[0], depot_complet(), courtier.traduire
    )
    assert set(demande) == set(courtier.CHAMPS_KALDERA)
    corps = json.dumps(demande, ensure_ascii=False)
    for nom_fichier in ("facture-plombier.pdf", "degats-couloir.jpg"):
        assert nom_fichier not in corps, f"« {nom_fichier} » a traversé"


def test_aucune_donnee_interne_du_courtier_ne_traverse_non_plus() -> None:
    demande = importation.construire_demande(
        dossiers.DOSSIERS[0], depot_complet(), courtier.traduire
    )
    corps = json.dumps(demande, ensure_ascii=False)
    for interne in courtier.CHAMPS_INTERNES:
        assert interne not in corps


# ------------------------------------------- la lisibilité, convention explicable


@pytest.mark.parametrize(
    ("categorie", "nom", "taille", "lisible"),
    [
        ("facture", "facture.pdf", 48_000, True),
        ("facture", "facture.jpg", 48_000, True),
        ("facture", "facture.docx", 48_000, False),
        ("facture", "facture.pdf", 0, False),
        ("facture", "facture.pdf", 100, False),
        ("photo", "degats.png", 220_000, True),
        ("photo", "degats.pdf", 220_000, False),
        ("depot_plainte", "plainte.pdf", 32_000, True),
    ],
)
def test_la_lisibilite_se_decide_sur_le_format_et_la_taille(
    categorie: str, nom: str, taille: int, lisible: bool
) -> None:
    """Une convention vérifiable vaut mieux qu'un jugement que personne ne saurait reproduire."""
    piece = importation.PieceDeposee(
        categorie, nom, taille, motif_illisible=importation.motif_illisible(categorie, nom, taille)
    )
    assert piece.lisible is lisible


def test_une_piece_illisible_dit_pourquoi() -> None:
    """Un « illisible » sans raison oblige l'opérateur à deviner ce qu'il doit refaire."""
    depot = importation.Depot()
    piece = depot.ajouter("facture", "facture.docx", 48_000)
    assert not piece.lisible
    assert "format inattendu" in piece.motif_illisible
    assert ".pdf" in piece.motif_illisible, "il faut dire ce qui est attendu"


def test_une_categorie_inconnue_est_refusee() -> None:
    with pytest.raises(importation.DepotRefuse, match="catégorie inconnue"):
        importation.Depot().ajouter("expertise", "rapport.pdf", 10_000)


# ------------------------------------------- l'aperçu avant dépôt


def test_les_pieces_exigees_dependent_du_type_de_sinistre() -> None:
    """Section 5 : un vol demande un dépôt de plainte, pas une photo."""
    assert importation.pieces_exigees("vol") == ("facture", "depot_plainte")
    for autre in ("degat_des_eaux", "incendie", "bris_de_glace"):
        assert importation.pieces_exigees(autre) == ("facture", "photo")


def test_l_apercu_signale_ce_qui_manque() -> None:
    depot = importation.Depot()
    assert importation.manquantes(depot, "degat_des_eaux") == ["facture", "photo"]
    depot.ajouter("facture", "f.pdf", 48_000, montant=900.0)
    assert importation.manquantes(depot, "degat_des_eaux") == ["photo"]
    depot.ajouter("photo", "p.jpg", 100_000)
    assert importation.manquantes(depot, "degat_des_eaux") == []


def test_une_piece_illisible_ne_comble_pas_un_manque() -> None:
    """C'est le piège : un fichier déposé n'est pas une pièce fournie."""
    depot = importation.Depot()
    depot.ajouter("facture", "facture.docx", 48_000, montant=900.0)
    assert "facture" in importation.manquantes(depot, "degat_des_eaux")


def test_le_montant_des_factures_ignore_les_illisibles() -> None:
    """Même règle que l'estimation : seules les factures lisibles comptent."""
    depot = importation.Depot()
    depot.ajouter("facture", "bonne.pdf", 48_000, montant=1000.0)
    depot.ajouter("facture", "mauvaise.docx", 48_000, montant=5000.0)
    assert depot.montant_des_factures() == 1000.0


def test_une_piece_se_retire() -> None:
    depot = depot_complet()
    assert len(depot.pieces) == 2
    depot.retirer("degats-couloir.jpg")
    assert len(depot.pieces) == 1
    assert importation.manquantes(depot, "degat_des_eaux") == ["photo"]


# ------------------------------------------- de bout en bout, par la porte publique


def test_un_dossier_depose_se_traite_comme_un_autre(partenaire: Any) -> None:
    """Une demande construite depuis des fichiers n'a rien de particulier pour la plateforme."""
    import kaldera

    partenaire.preparer({"mode": "normal"})
    demande = importation.construire_demande(
        dossiers.DOSSIERS[0], depot_complet(), courtier.traduire
    )
    fiche = kaldera.traiter_demande(demande, partenaire_url=partenaire.url)

    assert fiche["issue"] in ("decision", "escalade")
    assert fiche["motif"].strip()


def test_un_dossier_sans_photo_part_en_escalade(partenaire: Any) -> None:
    """`NOM-09` reproduit depuis un dépôt réel : aucune pièce du type demandé, aucun arrêt."""
    import kaldera

    depot = importation.Depot()
    depot.ajouter("facture", "facture.pdf", 48_000, montant=900.0)

    partenaire.preparer({"mode": "normal"})
    demande = importation.construire_demande(dossiers.DOSSIERS[0], depot, courtier.traduire)
    fiche = kaldera.traiter_demande(demande, partenaire_url=partenaire.url)

    assert fiche["issue"] == "escalade"
    assert fiche["file"] == "gestionnaire"
    assert fiche["arret"] is None, "l'absence de pièce est une règle métier, pas une borne"


# ------------------------------------ le mode dégradé, tel que la vue l'annonce


def test_pan_01_laisse_trois_fiches_sur_cinq_non_marquees(partenaire: Any) -> None:
    """La vue « mode dégradé » l'affirme ; ce test garde l'affirmation vraie.

    Une vue qui annonce « trois sur cinq » et qui se trompe est pire qu'une vue absente : elle
    donne l'air d'une preuve.
    """
    import kaldera

    from .harnais_c2 import SCENARIOS

    (scenario,) = [s for s in SCENARIOS if s["id"] == "PAN-01"]
    partenaire.preparer({"mode": "panne"})
    resultat = kaldera.traiter_lot(scenario["demandes"], partenaire_url=partenaire.url)

    marquees = [f["reference"] for f in resultat["fiches"] if f.get("mode_degrade")]
    assert len(resultat["fiches"]) == 5
    assert len(marquees) == 2, f"marquées : {marquees}"

    for fiche in resultat["fiches"]:
        assert fiche["issue"] in ("decision", "escalade"), "aucune ne doit rester sans issue"
        assert fiche["motif"].strip()


def test_le_seuil_du_mode_degrade_separe_bien_les_deux_sorties(partenaire: Any) -> None:
    """≤ 1 500 € la demande continue ; au-delà elle part en cellule anti-fraude."""
    import kaldera

    from .harnais_c2 import SCENARIOS

    (scenario,) = [s for s in SCENARIOS if s["id"] == "PAN-01"]
    partenaire.preparer({"mode": "panne"})
    resultat = kaldera.traiter_lot(scenario["demandes"], partenaire_url=partenaire.url)

    for fiche in resultat["fiches"]:
        if not fiche.get("mode_degrade"):
            continue
        if fiche["issue"] == "escalade":
            assert fiche["file"] == "cellule_fraude", (
                "au-delà du seuil, c'est la cellule anti-fraude, pas le gestionnaire"
            )
        else:
            assert fiche["montant_rembourse"] is not None
            assert fiche["montant_rembourse"] <= 1500.0
