"""Les écrits de l'agence, et ce qu'un gestionnaire en fait.

La plateforme rend une fiche de décision : une issue, un motif, une file. Ce n'est pas ce qu'on
envoie à quelqu'un dont la salle de bain a été inondée. Ces tests gardent trois choses : le
courrier à l'assuré ne fuit pas le fonctionnement interne, la fiche du gestionnaire répond à ses
trois questions, et une décision manuelle reste vérifiable.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from demo.agence import gestionnaire, redaction
from demo.client_externe import courtier, dossiers

AUJOURDHUI = date(2026, 10, 9)


def _demande() -> dict[str, Any]:
    return courtier.traduire(dossiers.DOSSIERS[0])


def _fiche(**remplacements: Any) -> dict[str, Any]:
    base = {
        "reference": "KAL-26-7001",
        "issue": "decision",
        "decision": "acceptee",
        "montant_rembourse": 1250.0,
        "motif": "Remboursement accordé : 1250.00 €",
        "file": None,
        "avis_fraude": None,
        "mode_degrade": False,
        "arret": None,
        "trace": [],
    }
    return {**base, **remplacements}


# ------------------------------------------- le courrier à l'assuré


def test_le_courrier_ne_dit_rien_du_fonctionnement_interne() -> None:
    """Un assuré n'a pas à connaître les agents, les bornes ni le partenaire pour comprendre."""
    courrier = redaction.courrier_assure(
        _fiche(mode_degrade=True, avis_fraude={"niveau": "faible", "score": 0.1}),
        _demande(),
        AUJOURDHUI,
    )
    interdits = (
        "agent",
        "borne",
        "partenaire",
        "anti-fraude",
        "antifraude",
        "escalade",
        "mode dégradé",
        "cellule",
        "trace",
        "estimation",
    )
    minuscule = courrier.lower()
    presents = [mot for mot in interdits if mot in minuscule]
    assert not presents, f"vocabulaire interne dans le courrier : {presents}"


def test_le_courrier_nomme_l_assure_et_sa_reference() -> None:
    courrier = redaction.courrier_assure(_fiche(), _demande(), AUJOURDHUI)
    assure = _demande()["assure"]
    assert assure["nom"] in courrier
    assert "KAL-26-7001" in courrier
    assert "09/10/2026" in courrier


def test_une_acceptation_annonce_le_virement_et_son_montant() -> None:
    courrier = redaction.courrier_assure(_fiche(), _demande(), AUJOURDHUI)
    assert "1250.00 €" in courrier
    assert "virement" in courrier.lower()


def test_un_refus_rappelle_le_delai_de_reclamation() -> None:
    """Refuser sans dire comment contester, c'est refuser deux fois."""
    courrier = redaction.courrier_assure(
        _fiche(
            decision="refusee",
            montant_rembourse=0.0,
            motif="Demande non éligible : contrat non actif",
        ),
        _demande(),
        AUJOURDHUI,
    )
    assert str(redaction.DELAI_RECLAMATION_JOURS) in courrier
    assert "aucun versement" in courrier.lower()


def test_une_escalade_ne_demande_rien_a_l_assure() -> None:
    """Sauf s'il manque des pièces : alors il faut lui dire quoi faire."""
    courrier = redaction.courrier_assure(
        _fiche(
            issue="escalade",
            decision=None,
            montant_rembourse=None,
            motif="Contrôle renforcé : risque de fraude modéré",
            file="gestionnaire",
        ),
        _demande(),
        AUJOURDHUI,
    )
    assert "sans démarche de votre part" in courrier

    complement = redaction.courrier_assure(
        _fiche(
            issue="escalade",
            decision=None,
            montant_rembourse=None,
            motif="Pièces manquantes : photo",
            file="gestionnaire",
        ),
        _demande(),
        AUJOURDHUI,
    )
    assert "espace en ligne" in complement


@pytest.mark.parametrize(("debut", "_"), redaction.EXPLICATIONS)
def test_chaque_motif_de_la_plateforme_a_son_explication(debut: str, _: str) -> None:
    """Un motif sans explication produirait un courrier vide de sens."""
    assert redaction.explication(f"{debut} : détail") != "Votre demande est en cours d'examen."


def test_le_courrier_est_identique_pour_une_situation_identique() -> None:
    """Décision D9 — par gabarit. Deux assurés dans la même situation reçoivent le même texte."""
    premier = redaction.courrier_assure(_fiche(), _demande(), AUJOURDHUI)
    for _ in range(3):
        assert redaction.courrier_assure(_fiche(), _demande(), AUJOURDHUI) == premier


# ------------------------------------------- la fiche du gestionnaire


def test_la_fiche_repond_aux_trois_questions_dans_l_ordre() -> None:
    """De quoi s'agit-il, pourquoi m'arrive-t-il, que dois-je faire."""
    fiche_texte = redaction.fiche_gestionnaire(
        _fiche(
            issue="escalade",
            decision=None,
            montant_rembourse=None,
            motif="Contrôle renforcé : risque de fraude modéré",
            file="gestionnaire",
        ),
        _demande(),
        AUJOURDHUI,
    )
    position_motif = fiche_texte.index("POURQUOI CE DOSSIER VOUS ARRIVE")
    position_faire = fiche_texte.index("À FAIRE")
    position_assure = fiche_texte.index("L'ASSURÉ")
    assert position_motif < position_faire < position_assure, (
        "le contexte doit venir après l'action à mener"
    )


def test_la_fiche_signale_l_absence_d_avis_anti_fraude() -> None:
    """Un dossier sans contrôle automatique doit le dire : c'est ce qui change le travail."""
    fiche_texte = redaction.fiche_gestionnaire(
        _fiche(
            issue="escalade",
            decision=None,
            montant_rembourse=None,
            motif="Contrôle anti-fraude manuel : avis du partenaire indisponible",
            file="cellule_fraude",
            mode_degrade=True,
        ),
        _demande(),
        AUJOURDHUI,
    )
    assert "NON OBTENU" in fiche_texte
    assert "aucun contrôle automatique" in fiche_texte


def test_la_fiche_rappelle_qu_un_avis_est_consultatif() -> None:
    fiche_texte = redaction.fiche_gestionnaire(
        _fiche(
            issue="escalade",
            file="gestionnaire",
            motif="Contrôle renforcé : risque de fraude modéré",
            avis_fraude={"niveau": "modere", "score": 0.52},
        ),
        _demande(),
        AUJOURDHUI,
    )
    assert "consultatif" in fiche_texte
    assert "0.52" in fiche_texte


def test_la_fiche_signale_un_traitement_interrompu() -> None:
    fiche_texte = redaction.fiche_gestionnaire(
        _fiche(
            issue="escalade",
            file="gestionnaire",
            motif="Pièces illisibles après relance : contrôle manuel nécessaire",
            arret={"borne": "pieces_sans_depot_restant"},
        ),
        _demande(),
        AUJOURDHUI,
    )
    assert "TRAITEMENT INTERROMPU" in fiche_texte
    assert "pieces_sans_depot_restant" in fiche_texte


def test_la_consigne_differe_selon_la_file() -> None:
    """Un dossier en cellule anti-fraude ne se traite pas comme un dossier ordinaire."""
    assert "Ne pas contacter l'assuré" in redaction.CONSIGNES["cellule_fraude"]
    assert "Ne pas contacter" not in redaction.CONSIGNES["gestionnaire"]


# ------------------------------------------- la décision manuelle


def test_accepter_sans_montant_est_refuse() -> None:
    with pytest.raises(gestionnaire.MontantManquant):
        gestionnaire.decider("KAL-26-7001", "accepter", "M. Berthier")


def test_une_decision_est_signee() -> None:
    """Une décision manuelle engage quelqu'un : elle porte son nom."""
    with pytest.raises(ValueError, match="gestionnaire doit être nommé"):
        gestionnaire.decider("KAL-26-7001", "refuser", "   ")


def test_une_suite_inconnue_est_refusee() -> None:
    with pytest.raises(gestionnaire.SuiteInconnue):
        gestionnaire.decider("KAL-26-7001", "classer_sans_suite", "M. Berthier")


def test_la_decision_manuelle_garde_la_forme_d_une_fiche() -> None:
    """C'est ce qui permet de réutiliser la rédaction sans la dupliquer."""
    initiale = _fiche(
        issue="escalade",
        decision=None,
        montant_rembourse=None,
        motif="Contrôle renforcé : risque de fraude modéré",
        file="gestionnaire",
    )
    decision = gestionnaire.decider(
        "KAL-26-7001", "accepter", "M. Berthier", montant=1100.0, aujourdhui=AUJOURDHUI
    )
    apres = decision.en_fiche(initiale)

    assert apres["issue"] == "decision"
    assert apres["decision"] == "acceptee"
    assert apres["montant_rembourse"] == 1100.0
    assert apres["decide_par"] == "M. Berthier"
    assert apres["decide_le"] == "2026-10-09"

    courrier = redaction.courrier_assure(apres, _demande(), AUJOURDHUI)
    assert "1100.00 €" in courrier


def test_un_refus_manuel_met_le_montant_a_zero() -> None:
    decision = gestionnaire.decider(
        "KAL-26-7001", "refuser", "M. Berthier", precision="dommage antérieur au contrat"
    )
    apres = decision.en_fiche(_fiche(issue="escalade", file="gestionnaire"))
    assert apres["decision"] == "refusee"
    assert apres["montant_rembourse"] == 0.0
    assert "dommage antérieur" in apres["motif"]


def test_la_file_met_les_dossiers_sensibles_devant() -> None:
    """Cellule anti-fraude d'abord, puis ceux que personne n'a encore contrôlés."""
    fiches = [
        _fiche(reference="A", issue="escalade", file="gestionnaire", mode_degrade=False),
        _fiche(reference="B", issue="escalade", file="cellule_fraude", mode_degrade=False),
        _fiche(reference="C", issue="escalade", file="gestionnaire", mode_degrade=True),
        _fiche(reference="D", issue="decision", decision="acceptee"),
    ]
    ordre = [f["reference"] for f in gestionnaire.file_d_attente(fiches)]
    assert ordre == ["B", "C", "A"], "les décisions closes ne sont pas dans la file"
