"""Le relecteur — et les trois frontières qui le rendent acceptable.

Le formateur a ouvert le brief : un modèle peut entrer dans le système. La mesure a tranché
*où* : un appel met de 3,5 à 18 secondes selon le dossier, pour un engagement de service de
10 secondes. Le chemin de décision est donc hors de portée, et le relecteur passe **après**.

Ces tests gardent ce qui rend ce choix tenable : la décision ne peut pas dépendre de lui, il ne
se prononce jamais sur la fraude, et il ne transmet pas le récit de l'assuré sans autorisation.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest

import kaldera
from kaldera.revue import charge, relecteur

PAQUET = Path(__file__).resolve().parents[2] / "src" / "kaldera"

DEMANDE: dict[str, Any] = {
    "reference": "KAL-26-0101",
    "assure": {
        "id_client": "CLI-1",
        "nom": "Vasseur",
        "prenom": "Camille",
        "email": "camille@exemple.fr",
        "telephone": "0611223344",
        "iban": "FR7630004000031234567890143",
        "adresse": "8 rue de la Guillotière",
        "code_postal": "69007",
    },
    "contrat": {
        "numero": "POL-1",
        "formule": "confort",
        "date_souscription": "2023-04-01",
        "statut": "actif",
        "cotisations_a_jour": True,
    },
    "sinistre": {
        "type": "degat_des_eaux",
        "date_survenance": "2026-09-12",
        "date_declaration": "2026-09-14",
        "montant_declare": 1400.0,
        "description": "Fuite sous l'évier, parquet gondolé dans le couloir",
    },
    "pieces": [{"type": "facture", "lisible": True, "montant": 1400.0}],
    "historique": {"sinistres_12_mois": 0},
    "espace_assure": {"depots": []},
}

FICHE: dict[str, Any] = {
    "reference": "KAL-26-0101",
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


class ModeleFictif:
    """Un modèle qui rend ce qu'on lui dit de rendre. Aucun appel réseau."""

    def __init__(self, reponse: Any) -> None:
        self.reponse = reponse
        self.recu: list[tuple[str, str]] = []

    def __call__(self) -> ModeleFictif:
        return self

    def invoke(self, messages: list[tuple[str, str]]) -> Any:
        self.recu = messages

        class Reponse:
            content = self.reponse if isinstance(self.reponse, str) else json.dumps(self.reponse)

        return Reponse()


# ======================================== frontière 1 · la décision n'en dépend pas


def test_aucun_agent_n_importe_la_revue() -> None:
    """La garantie structurelle. Sans elle, « hors du chemin » n'est qu'une intention.

    Un import suffirait à mettre plusieurs secondes de latence dans le chemin de décision —
    et à faire dépendre l'engagement de service d'un fournisseur de modèles.
    """
    interdits = []
    for module in PAQUET.rglob("*.py"):
        if module.parts[-2] == "revue" or module.name == "__init__.py":
            continue
        arbre = ast.parse(module.read_text(encoding="utf-8"))
        for noeud in ast.walk(arbre):
            noms = []
            if isinstance(noeud, ast.ImportFrom):
                noms.append(noeud.module or "")
            elif isinstance(noeud, ast.Import):
                noms.extend(a.name for a in noeud.names)
            if any("revue" in n for n in noms):
                interdits.append(module.relative_to(PAQUET).as_posix())
    assert not interdits, f"ces modules importent la revue : {interdits}"


def test_le_repartiteur_ne_connait_pas_la_revue() -> None:
    """Le contrôle le plus direct : la boucle d'orchestration ne la mentionne nulle part."""
    source = (PAQUET / "orchestration" / "repartiteur.py").read_text(encoding="utf-8")
    assert "revue" not in source
    assert "relire" not in source


def test_la_revue_ne_modifie_jamais_la_fiche() -> None:
    """Son avis s'ajoute à côté. Une fiche qui changerait après coup ne serait plus une preuve."""
    avant = json.dumps(FICHE, sort_keys=True)
    kaldera.relire(DEMANDE, FICHE, fabrique=ModeleFictif({"verdict": "conforme", "points": []}))
    assert json.dumps(FICHE, sort_keys=True) == avant


def test_une_revue_indisponible_n_est_pas_un_echec() -> None:
    """Le modèle est un service tiers : son absence doit être un non-événement."""
    avis = kaldera.relire(DEMANDE, FICHE, fabrique=lambda: None)
    assert avis["verdict"] == "non_disponible"
    assert avis["points"] == []
    assert "aucun modèle" in avis["cause"]


def test_un_modele_qui_tombe_rend_un_avis_indisponible() -> None:
    class EnPanne:
        def __call__(self) -> EnPanne:
            return self

        def invoke(self, messages: Any) -> Any:
            raise RuntimeError("service injoignable")

    avis = kaldera.relire(DEMANDE, FICHE, fabrique=EnPanne())
    assert avis["verdict"] == "non_disponible"
    assert "échec" in avis["cause"]


# ===================================== frontière 2 · jamais d'avis de fraude


def test_un_point_evoquant_la_fraude_est_ecarte() -> None:
    """« L'avis de fraude est émis par le partenaire, jamais en interne » — specs §2.

    Le modèle peut déborder ; la réponse est relue, pas corrigée.
    """
    modele = ModeleFictif(
        {
            "verdict": "a_revoir",
            "motif_clair": True,
            "points": [
                "Le montant remboursé dépasse le montant justifié.",
                "Ce dossier présente un risque de fraude manifeste.",
                "Les factures semblent falsifiées.",
            ],
        }
    )
    avis = kaldera.relire(DEMANDE, FICHE, fabrique=modele)
    assert len(avis["points"]) == 1
    assert avis["points_ecartes"] == 2
    corps = json.dumps(avis, ensure_ascii=False).lower()
    assert "fraude" not in corps and "falsifi" not in corps


def test_un_verdict_hors_nomenclature_est_ecarte() -> None:
    """Même principe qu'avec le partenaire : hors contrat, la réponse n'est pas exploitée."""
    modele = ModeleFictif({"verdict": "suspect", "points": ["quelque chose"]})
    avis = kaldera.relire(DEMANDE, FICHE, fabrique=modele)
    assert avis["verdict"] == "non_disponible"
    assert avis["points"] == []


def test_une_reponse_illisible_est_ecartee() -> None:
    avis = kaldera.relire(DEMANDE, FICHE, fabrique=ModeleFictif("je ne sais pas répondre"))
    assert avis["verdict"] == "non_disponible"


def test_au_plus_trois_points_sont_retenus() -> None:
    """Un gestionnaire qui reçoit dix remarques n'en lit aucune."""
    modele = ModeleFictif({"verdict": "a_revoir", "points": [f"remarque {i}" for i in range(10)]})
    avis = kaldera.relire(DEMANDE, FICHE, fabrique=modele)
    assert len(avis["points"]) == 3


# ============================= frontière 3 · la minimisation, fermée par défaut


def test_le_recit_de_l_assure_ne_part_pas() -> None:
    """Tranché par le métier le 12 octobre 2026 : le récit ne part chez aucun modèle *(`D32`)*."""
    dossier = charge.construire(DEMANDE, FICHE)
    assert "recit_assure" not in dossier
    corps = json.dumps(dossier, ensure_ascii=False)
    assert DEMANDE["sinistre"]["description"] not in corps


def test_aucune_donnee_personnelle_n_atteint_le_modele() -> None:
    modele = ModeleFictif({"verdict": "conforme", "points": []})
    kaldera.relire(DEMANDE, FICHE, fabrique=modele)
    envoye = "\n".join(contenu for _, contenu in modele.recu)

    interdits = [
        *DEMANDE["assure"].values(),
        DEMANDE["contrat"]["numero"],
        DEMANDE["sinistre"]["description"],
    ]
    fuites = [v for v in interdits if isinstance(v, str) and v and v in envoye]
    assert not fuites, f"données personnelles transmises au modèle : {fuites}"


def test_aucune_variable_d_environnement_ne_rouvre_le_recit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le drapeau qui ouvrait cette porte a été retiré. Ce test garde qu'il ne revienne pas.

    L'architecture tenait les deux réponses tant que le métier n'avait pas tranché. Il a
    tranché : le récit ne part pas. Un interrupteur laissé en place après coup n'est plus une
    option ouverte, c'est une porte que personne ne surveille.
    """
    for drapeau in ("KALDERA_REVUE_RECIT", "KALDERA_RECIT", "REVUE_RECIT"):
        monkeypatch.setenv(drapeau, "1")
    dossier = charge.construire(DEMANDE, FICHE)
    corps = json.dumps(dossier, ensure_ascii=False)
    assert "recit_assure" not in dossier
    assert DEMANDE["sinistre"]["description"] not in corps
    assert not hasattr(charge, "recit_autorise"), (
        "la porte a été rouverte : `recit_autorise` est de retour dans la charge"
    )


def test_la_charge_se_construit_en_partant_de_rien() -> None:
    """Un champ ajouté demain à la demande ne doit pas partir tout seul."""
    demande = {**DEMANDE, "scoring_interne": {"note": 0.97}}
    demande["assure"] = {**DEMANDE["assure"], "profession": "architecte"}
    dossier = charge.construire(demande, FICHE)
    assert set(dossier) <= set(charge.CHAMPS_STRUCTURES)
    corps = json.dumps(dossier, ensure_ascii=False)
    assert "architecte" not in corps and "scoring_interne" not in corps


# ========================================================= ce qu'il sait faire


def test_une_decision_coherente_est_jugee_conforme() -> None:
    modele = ModeleFictif({"verdict": "conforme", "motif_clair": True, "points": []})
    avis = kaldera.relire(DEMANDE, FICHE, fabrique=modele)
    assert avis["verdict"] == "conforme"
    assert avis["motif_clair"]
    assert avis["points"] == []


def test_un_motif_juge_obscur_est_signale() -> None:
    """C'est l'usage le plus utile : un motif exact qu'un assuré ne comprendra pas."""
    modele = ModeleFictif(
        {
            "verdict": "a_revoir",
            "motif_clair": False,
            "points": ["Le libellé est incompréhensible pour un assuré non spécialiste."],
        }
    )
    avis = kaldera.relire(DEMANDE, FICHE, fabrique=modele)
    assert not avis["motif_clair"]
    assert len(avis["points"]) == 1


def test_l_avis_porte_toujours_les_memes_cles() -> None:
    """Une forme stable est ce qui permet de l'afficher sans tester chaque cas."""
    attendues = {
        "verdict",
        "motif_clair",
        "coherence_pieces",
        "points",
        "cause",
        "duree_ms",
        "points_ecartes",
    }
    for fabrique in (
        lambda: None,
        ModeleFictif({"verdict": "conforme", "points": []}),
        ModeleFictif("illisible"),
    ):
        avis = kaldera.relire(DEMANDE, FICHE, fabrique=fabrique)
        assert set(avis) == attendues
        assert avis["verdict"] in relecteur.NIVEAUX


# ========================================= à l'épreuve d'un modèle réel


@pytest.mark.modele
@pytest.mark.skipif(not relecteur.Relecteur().disponible(), reason="aucun modèle configuré")
def test_le_relecteur_detecte_une_incoherence_flagrante() -> None:
    """Mesuré, pas supposé : un remboursement sans rapport avec le dossier doit le réveiller."""
    incoherente = {
        **FICHE,
        "montant_rembourse": 99_000.0,
        "motif": "Remboursement accordé : 99000.00 €",
    }
    avis = kaldera.relire(DEMANDE, incoherente)
    assert avis["verdict"] == "a_revoir", avis
    assert avis["points"], "un écart pareil mérite au moins une remarque"


@pytest.mark.modele
@pytest.mark.skipif(not relecteur.Relecteur().disponible(), reason="aucun modèle configuré")
def test_un_appel_reel_depasse_largement_le_budget_du_chemin_de_decision() -> None:
    """La mesure qui fonde l'arbitrage. Si elle devenait fausse, il faudrait le rouvrir."""
    avis = kaldera.relire(DEMANDE, FICHE)
    assert avis["verdict"] in ("conforme", "a_revoir"), avis
    assert avis["duree_ms"] > 500, (
        f"{avis['duree_ms']:.0f} ms — le modèle est devenu assez rapide pour qu'on "
        "reconsidère sa place dans le chemin de décision"
    )


# ============================ la cohérence des pièces, consultative et sans effet


def test_la_coherence_des_pieces_est_relue_comme_le_reste() -> None:
    """Hors nomenclature, elle retombe sur « indéterminable » — jamais sur une supposition."""
    for rendu, attendu in (
        ("plausible", "plausible"),
        ("douteuse", "douteuse"),
        ("indeterminable", "indeterminable"),
        ("suspecte", "indeterminable"),
        (None, "indeterminable"),
    ):
        modele = ModeleFictif({"verdict": "conforme", "points": [], "coherence_pieces": rendu})
        avis = kaldera.relire(DEMANDE, FICHE, fabrique=modele)
        assert avis["coherence_pieces"] == attendu


def test_une_coherence_douteuse_ne_change_aucune_decision() -> None:
    """C'est ce qui permet de poser une question dont le critère métier n'existe pas encore.

    Tant qu'aucune décision n'en dépend, aucun assuré ne subit un jugement que personne ne
    saurait lui expliquer. Le jour où le métier définira le critère, la question sera déjà
    posée et mesurée.
    """
    modele = ModeleFictif(
        {
            "verdict": "conforme",
            "points": [],
            "coherence_pieces": "douteuse",
        }
    )
    avant = json.dumps(FICHE, sort_keys=True)
    avis = kaldera.relire(DEMANDE, FICHE, fabrique=modele)

    assert avis["coherence_pieces"] == "douteuse"
    assert json.dumps(FICHE, sort_keys=True) == avant, "la fiche n'a pas bougé"
    assert FICHE["decision"] == "acceptee", "la décision non plus"


def test_sans_le_recit_la_coherence_reste_structurelle() -> None:
    """Juger la cohérence « avec la déclaration » suppose de voir la déclaration.

    Elle est fermée par défaut : le modèle ne peut donc juger que des types de pièces et des
    montants au regard de la nature du sinistre. C'est moins, et c'est dit.
    """
    modele = ModeleFictif({"verdict": "conforme", "points": [], "coherence_pieces": "plausible"})
    kaldera.relire(DEMANDE, FICHE, fabrique=modele)
    envoye = chr(10).join(contenu for _, contenu in modele.recu)
    assert DEMANDE["sinistre"]["description"] not in envoye
    assert "pieces" in envoye and "type_sinistre" in envoye
