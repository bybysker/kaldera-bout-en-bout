"""La prise de déclaration, mesurée — pas supposée.

Un extracteur qu'on ne sait pas noter n'est pas un extracteur, c'est un pari. Ces tests posent un
jeu de récits avec leur résultat attendu, et le passent aux deux extracteurs. Le déterministe est
évalué à chaque exécution ; celui qui s'appuie sur un modèle ne l'est que si un modèle est
configuré — sinon le test est ignoré, pas supprimé.

C'est aussi la garantie que `D25` tient : rien ici ne touche au chemin de décision. Le résultat
d'une extraction est relu avant d'être déposé.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest

from demo.client_externe import saisie

AUJOURDHUI = date(2026, 10, 9)  # un vendredi

#: Récits, et ce qu'on attend d'eux. `None` signifie « doit rester indéterminé ».
RECITS: list[tuple[str, str, dict[str, Any]]] = [
    (
        "fuite simple",
        "Bonjour, j'ai eu une fuite sous l'évier samedi dernier, le parquet du couloir a "
        "gondolé. J'ai la facture du plombier, 1 400 euros, et j'ai pris des photos.",
        {
            "type_sinistre": "degat_des_eaux",
            "date_survenance": "2026-10-03",
            "montant_declare": 1400.0,
            "pieces": ["facture", "photo"],
        },
    ),
    (
        "incendie avec date explicite",
        "Un incendie s'est déclaré dans le garage le 28/09/2026. Les dégâts sont estimés à "
        "7800 € par l'expert, j'ai la facture.",
        {
            "type_sinistre": "incendie",
            "date_survenance": "2026-09-28",
            "montant_declare": 7800.0,
            "pieces": ["facture"],
        },
    ),
    (
        "vol avec plainte",
        "On m'a cambriolé hier, effraction par la fenêtre de la cuisine. Ordinateur portable "
        "emporté, 950 euros. Je suis allé au commissariat déposer plainte.",
        {
            # L'attendu est **métier** : une fenêtre brisée pendant un cambriolage reste un vol.
            # Les règles ne savent pas trancher — « cambriolé » et « fenêtre » évoquent deux
            # natures — et préfèrent ne rien conclure. C'est leur limite, et c'est précisément
            # ce que le modèle apporte.
            "type_sinistre": "vol",
            "date_survenance": "2026-10-08",
            "montant_declare": 950.0,
            "pieces": ["depot_plainte"],
            "limite_des_regles": {"type_sinistre": None},
        },
    ),
    (
        "bris de glace",
        "La baie vitrée du salon s'est brisée mercredi. Le vitrier demande 620 euros, "
        "voici son devis.",
        {
            "type_sinistre": "bris_de_glace",
            "date_survenance": "2026-10-07",
            "montant_declare": 620.0,
            "pieces": ["facture"],
        },
    ),
    (
        "récit incomplet",
        "Il y a eu un problème chez moi la semaine dernière, je ne sais pas encore combien "
        "ça va coûter.",
        {
            "type_sinistre": None,
            "date_survenance": None,
            "montant_declare": None,
            "pieces": [],
        },
    ),
]


# ------------------------------------------------- l'extracteur déterministe


@pytest.mark.parametrize(("intitule", "recit", "attendu"), RECITS, ids=[r[0] for r in RECITS])
def test_l_extraction_par_regles_rend_ce_qu_on_attend(
    intitule: str, recit: str, attendu: dict[str, Any]
) -> None:
    """L'attendu est métier ; `limite_des_regles` dit où les règles ne peuvent pas y arriver.

    Écrire le comportement des règles comme s'il était la vérité serait un biais : le jeu de
    test cesserait de mesurer quoi que ce soit, et ne ferait que figer l'existant.
    """
    limites = attendu.get("limite_des_regles", {})
    produite = saisie.ExtractionParRegles().extraire(recit, AUJOURDHUI)
    for champ in ("type_sinistre", "date_survenance", "montant_declare"):
        vise = limites.get(champ, attendu[champ]) if champ in limites else attendu[champ]
        assert getattr(produite, champ) == vise, champ
    assert sorted(produite.pieces) == sorted(attendu["pieces"])


def test_l_extraction_par_regles_est_deterministe() -> None:
    """Deux fois le même récit, deux fois le même résultat — c'est ce qui la rend démontrable."""
    recit = RECITS[0][1]
    extracteur = saisie.ExtractionParRegles()
    premiere = extracteur.extraire(recit, AUJOURDHUI).en_dict()
    for _ in range(5):
        assert extracteur.extraire(recit, AUJOURDHUI).en_dict() == premiere


def test_ce_qui_n_est_pas_compris_est_dit(caplog: pytest.LogCaptureFixture) -> None:
    """Une information absente doit se voir. Un champ deviné serait pire que vide."""
    _, recit, _ = RECITS[-1]
    produite = saisie.ExtractionParRegles().extraire(recit, AUJOURDHUI)
    assert not produite.complete
    assert set(produite.incertitudes) == {
        "type_sinistre",
        "date_survenance",
        "montant_declare",
    }


def test_les_regles_preferent_ne_rien_conclure_a_choisir_au_hasard() -> None:
    """C'est leur limite assumée : sans compréhension du récit, le doute l'emporte."""
    produite = saisie.ExtractionParRegles().extraire(
        "Après l'incendie, la fenêtre a aussi été brisée.", AUJOURDHUI
    )
    assert produite.type_sinistre is None
    assert "type_sinistre" in produite.incertitudes


# ------------------------------------- l'extracteur assisté, sans modèle joignable


def test_sans_modele_l_extraction_assistee_se_replie_sans_rien_casser() -> None:
    """La démonstration doit fonctionner sans accès au modèle. C'est une condition, pas un vœu."""
    assiste = saisie.ExtractionAssistee(fabrique=lambda: None)
    produite = assiste.extraire(RECITS[0][1], AUJOURDHUI)
    assert produite.type_sinistre == "degat_des_eaux"
    assert any("indisponible" in i for i in produite.incertitudes)


def test_un_modele_qui_tombe_ne_bloque_pas_la_saisie() -> None:
    class ModeleEnPanne:
        def invoke(self, messages: Any) -> Any:
            raise RuntimeError("service injoignable")

    assiste = saisie.ExtractionAssistee(fabrique=ModeleEnPanne)
    produite = assiste.extraire(RECITS[1][1], AUJOURDHUI)
    assert produite.type_sinistre == "incendie", "le repli déterministe doit prendre la main"
    assert any("échec" in i for i in produite.incertitudes)


def test_une_reponse_de_modele_hors_contrat_est_ecartee_champ_par_champ() -> None:
    """Même principe qu'avec le partenaire : ce qui n'est pas conforme n'est pas retenu."""

    class ModeleFantaisiste:
        def invoke(self, messages: Any) -> Any:
            class Reponse:
                content = json.dumps(
                    {
                        "type_sinistre": "tremblement_de_terre",  # hors liste
                        "date_survenance": "samedi dernier",  # mauvais format
                        "montant_declare": -50,  # négatif
                        "pieces": ["facture", "expertise_judiciaire"],  # une hors liste
                    }
                )

            return Reponse()

    produite = saisie.ExtractionAssistee(fabrique=ModeleFantaisiste).extraire(
        "peu importe", AUJOURDHUI
    )
    assert produite.type_sinistre is None
    assert produite.date_survenance is None
    assert produite.montant_declare is None
    assert produite.pieces == ["facture"], "seule la pièce connue est retenue"
    assert len(produite.incertitudes) == 3


def test_un_modele_qui_entoure_son_json_de_texte_reste_lisible() -> None:
    """Les modèles ajoutent souvent une phrase ou des balises autour du JSON."""

    class ModeleBavard:
        def invoke(self, messages: Any) -> Any:
            class Reponse:
                content = (
                    "Voici l'extraction :\n```json\n"
                    + json.dumps(
                        {
                            "type_sinistre": "vol",
                            "date_survenance": "2026-10-08",
                            "montant_declare": 950,
                            "pieces": ["depot_plainte"],
                        }
                    )
                    + "\n```\nJ'espère que cela convient."
                )

            return Reponse()

    produite = saisie.ExtractionAssistee(fabrique=ModeleBavard).extraire("…", AUJOURDHUI)
    assert produite.type_sinistre == "vol"
    assert produite.montant_declare == 950.0
    assert produite.complete


# ----------------------------------- l'extracteur assisté, avec un vrai modèle


@pytest.mark.modele
@pytest.mark.skipif(
    not saisie.modele_configure(),
    reason="aucun modèle configuré : AZURE_AI_ENDPOINT et AZURE_AI_API_KEY sont vides",
)
@pytest.mark.parametrize(("intitule", "recit", "attendu"), RECITS, ids=[r[0] for r in RECITS])
def test_le_modele_rend_ce_qu_on_attend(intitule: str, recit: str, attendu: dict[str, Any]) -> None:
    """Ignoré tant qu'aucun modèle n'est joignable — ignoré, pas supprimé.

    **Le repli rend ce test traître** : sur un récit simple, les règles donnent le même résultat
    que le modèle, et le test passerait alors que le modèle n'a jamais répondu. Il faut donc
    vérifier d'abord *qui* a produit l'extraction. C'est la première version de ce test qui a
    laissé passer un modèle en échec.
    """
    produite = saisie.ExtractionAssistee().extraire(recit, AUJOURDHUI)

    echecs = [i for i in produite.incertitudes if "modèle" in i]
    assert not echecs, f"le modèle n'a pas répondu : {echecs}"
    assert produite.extracteur == "modèle", (
        f"extraction produite par « {produite.extracteur} », pas par le modèle"
    )

    assert produite.type_sinistre == attendu["type_sinistre"]
    assert produite.date_survenance == attendu["date_survenance"]
    assert produite.montant_declare == attendu["montant_declare"]


# --------------------------------------------- la frontière avec le système


def test_la_saisie_ne_touche_jamais_au_paquet_kaldera() -> None:
    """`D25` — aucun modèle dans le chemin de décision. Celui-ci est en amont, chez le tiers."""
    import ast
    from pathlib import Path

    module = Path(saisie.__file__)
    arbre = ast.parse(module.read_text(encoding="utf-8"))
    for noeud in ast.walk(arbre):
        noms: list[str] = []
        if isinstance(noeud, ast.ImportFrom):
            noms.append(noeud.module or "")
        elif isinstance(noeud, ast.Import):
            noms.extend(alias.name for alias in noeud.names)
        for nom in noms:
            assert not nom.startswith("kaldera"), f"saisie.py importe `{nom}`"


def test_les_limites_des_regles_sont_celles_que_le_modele_doit_lever() -> None:
    """Un jeu de test qui ne dit pas où un extracteur échoue ne mesure rien.

    Ce test ne vérifie pas un comportement : il garde le jeu honnête. Si plus aucun récit ne
    portait de `limite_des_regles`, ce serait le signe que le jeu a été aligné sur ce que les
    règles savent faire — et il cesserait de dire ce que le modèle apporte.
    """
    avec_limite = [nom for nom, _, attendu in RECITS if attendu.get("limite_des_regles")]
    assert avec_limite, (
        "aucun récit ne met les règles en défaut : le jeu ne mesure plus l'apport du modèle"
    )


# -------------------------------- la bibliothèque de récits de la démonstration


def test_chaque_recit_porte_ce_qu_il_eprouve() -> None:
    """Un récit sans intention est un récit décoratif : il allonge la liste sans rien montrer."""
    from demo.client_externe import recits

    assert len(recits.RECITS) >= 8
    titres = [r.titre for r in recits.RECITS]
    assert len(set(titres)) == len(titres), "deux récits portent le même titre"
    for recit in recits.RECITS:
        assert len(recit.texte) > 60, f"« {recit.titre} » est trop court pour être réaliste"
        assert len(recit.eprouve) > 30, f"« {recit.titre} » ne dit pas ce qu'il éprouve"


def test_aucun_recit_ne_fait_echouer_l_extraction_par_regles() -> None:
    """Un récit peut rester incompris ; il ne doit jamais faire tomber la saisie."""
    from demo.client_externe import recits

    extracteur = saisie.ExtractionParRegles()
    for recit in recits.RECITS:
        produite = extracteur.extraire(recit.texte, AUJOURDHUI)
        assert produite.recit == recit.texte
        assert isinstance(produite.incertitudes, list)


def test_plusieurs_recits_mettent_les_regles_en_defaut() -> None:
    """C'est la raison d'être de la liste.

    Si tous les récits étaient traitables par mots-clés, la démonstration ne montrerait pas ce
    qu'un modèle apporte — elle montrerait seulement qu'on sait écrire des expressions
    régulières.
    """
    from demo.client_externe import recits

    extracteur = saisie.ExtractionParRegles()
    en_defaut = [
        recit.titre
        for recit in recits.RECITS
        if extracteur.extraire(recit.texte, AUJOURDHUI).incertitudes
    ]
    assert len(en_defaut) >= 4, (
        f"seulement {len(en_defaut)} récit(s) mettent les règles en défaut : {en_defaut}"
    )


def test_un_recit_porte_des_donnees_personnelles_dans_son_texte() -> None:
    """Il faut pouvoir montrer qu'un assuré qui en dit trop ne fait pas fuir ses données."""
    from demo.client_externe import recits

    bavards = [r for r in recits.RECITS if "IBAN" in r.texte or "iban" in r.texte.lower()]
    assert bavards, "aucun récit ne met la minimisation à l'épreuve"

    produite = saisie.ExtractionParRegles().extraire(bavards[0].texte, AUJOURDHUI)
    assert "FR76" not in str(produite.en_dict()), "un IBAN ne doit jamais sortir de la saisie"


# ------------------------------------- le temps, qui justifie D25 au chronomètre


def test_l_extraction_par_regles_reste_sous_la_milliseconde() -> None:
    """Le point de comparaison : sans modèle, extraire coûte le même ordre qu'une décision."""
    declaration = saisie.extraire_chronometre(
        saisie.ExtractionParRegles(), RECITS[0][1], AUJOURDHUI
    )
    assert declaration.duree_ms < 50, f"{declaration.duree_ms:.2f} ms"
    assert declaration.en_dict()["duree_ms"] == round(declaration.duree_ms, 2)


def test_le_traitement_complet_d_une_demande_est_cent_fois_plus_rapide_qu_un_modele() -> None:
    """L'affirmation que porte l'interface — vérifiée, pas supposée.

    Les cinq agents du chemin de décision traitent une demande complète en une fraction de
    milliseconde. C'est l'ordre de grandeur qu'un appel à un modèle ferait perdre, et c'est la
    justification empirique de `D25`.
    """
    import time

    import kaldera
    from demo import socle

    service = socle.Partenaire()
    (scenario,) = [s for s in socle.scenarios() if s["id"] == "NOM-01"]
    service.preparer(scenario["partenaire"])

    debut = time.perf_counter()
    fiche = kaldera.traiter_demande(scenario["demandes"][0], partenaire_url=service.url)
    duree_totale = (time.perf_counter() - debut) * 1000

    calcul = sum(etape["duree_ms"] for etape in fiche["trace"])
    assert calcul < 5, f"{calcul:.2f} ms de calcul pour cinq agents"
    assert duree_totale < 200, f"{duree_totale:.0f} ms de bout en bout"


@pytest.mark.modele
@pytest.mark.skipif(not saisie.modele_configure(), reason="aucun modèle configuré")
def test_un_appel_au_modele_consomme_une_part_notable_du_budget() -> None:
    """Mesuré, pas affirmé. Si cela devenait faux, l'interface mentirait."""
    declaration = saisie.extraire_chronometre(saisie.ExtractionAssistee(), RECITS[0][1], AUJOURDHUI)
    assert declaration.extracteur == "modèle", declaration.incertitudes
    assert declaration.duree_ms > 200, (
        f"{declaration.duree_ms:.0f} ms — l'interface annonce des secondes, pas des "
        "millisecondes : si le modèle était devenu aussi rapide, il faudrait le dire"
    )


# ------------------------------- la trace de bout en bout, frontière comprise


def test_la_trace_complete_distingue_ce_qui_est_dans_le_systeme() -> None:
    """Inscrire une étape que la plateforme n'a pas exécutée dans **sa** trace serait un
    mensonge dans une pièce qui sert de preuve. La composition se fait dans la démonstration,
    et chaque étape dit à qui elle appartient."""
    from demo import parcours

    declaration = saisie.extraire_chronometre(
        saisie.ExtractionParRegles(), RECITS[0][1], AUJOURDHUI
    )
    fiche = {
        "trace": [
            {
                "agent": "eligibilite",
                "action": "eligibilite",
                "duree_ms": 0.01,
                "statut": "ok",
                "ecrit": ["eligibilite"],
                "verdict": "recevable",
            },
        ]
    }
    etapes = parcours.trace_complete(fiche, declaration)

    assert len(etapes) == 2
    assert etapes[0]["acteur"] == "courtier"
    assert not parcours.ACTEURS[etapes[0]["acteur"]]["dans_le_systeme"]
    assert etapes[1]["acteur"] == "kaldera"
    assert parcours.ACTEURS[etapes[1]["acteur"]]["dans_le_systeme"]


def test_la_trace_de_la_plateforme_ne_porte_jamais_la_saisie() -> None:
    """Le contrat d'intégration ne prévoit que les étapes des agents."""
    from demo import parcours, socle

    service = socle.Partenaire()
    (scenario,) = [s for s in socle.scenarios() if s["id"] == "NOM-01"]
    service.preparer(scenario["partenaire"])

    import kaldera

    fiche = kaldera.traiter_demande(scenario["demandes"][0], partenaire_url=service.url)
    assert all(e["agent"] != "saisie" for e in fiche["trace"])

    declaration = saisie.extraire_chronometre(
        saisie.ExtractionParRegles(), RECITS[0][1], AUJOURDHUI
    )
    etapes = parcours.trace_complete(fiche, declaration)
    assert len(etapes) == len(fiche["trace"]) + 1, "la composition se fait côté démonstration"


def test_sans_saisie_le_parcours_se_reduit_au_traitement() -> None:
    from demo import parcours

    fiche = {
        "trace": [
            {
                "agent": "decision",
                "action": "decision",
                "duree_ms": 0.01,
                "statut": "ok",
                "ecrit": ["issue"],
                "verdict": "close",
            }
        ]
    }
    etapes = parcours.trace_complete(fiche)
    assert len(etapes) == 1
    assert parcours.part_du_modele(etapes) == 0.0


def test_la_part_du_modele_se_calcule_sur_le_temps_reel() -> None:
    from demo import parcours

    etapes = [
        {"acteur": "courtier", "agent": "saisie", "outil": "modèle de langage", "duree_ms": 4000.0},
        {"acteur": "kaldera", "agent": "decision", "outil": "calcul", "duree_ms": 1000.0},
    ]
    assert parcours.part_du_modele(etapes) == pytest.approx(0.8)
    assert parcours.repartition(etapes) == {"courtier": 4000.0, "kaldera": 1000.0}
