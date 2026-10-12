"""Épreuve des tests eux-mêmes : un test qui ne sait pas échouer ne prouve rien.

Chaque mutation réintroduit **un** défaut réel dans le code, lance **un** test précis, et vérifie
qu'il tombe. Le fichier d'origine est restauré quoi qu'il arrive. Ce n'est pas un test : c'est un
outil à lancer à la main, parce qu'il modifie les sources.

    uv run python -m tests.chantier_1.epreuve_mutations
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SOURCE = RACINE / "src" / "kaldera"
DEMO = RACINE / "demo"
CHANTIER_2 = "tests/chantier_2"

ACCEPTANCE = "tests/acceptance"
CHANTIER_1 = "tests/chantier_1"


@dataclass(frozen=True)
class Mutation:
    """Un défaut réintroduit, et le test qui doit s'en apercevoir."""

    nom: str
    fichier: Path
    avant: str
    apres: str
    test: str
    attendu: str


MUTATIONS: list[Mutation] = [
    Mutation(
        nom="le plafond s'applique avant la franchise",
        fichier=SOURCE / "regles" / "montants.py",
        avant="    return round(min(apres_franchise, formules.plafond(formule)), 2)",
        apres="    return round(max(0.0, min(retenu, formules.plafond(formule))"
        " - formules.franchise(formule)), 2)",
        test=f"{ACCEPTANCE}/test_equipe_orchestration.py::"
        "test_scenario_nominal_produit_la_decision_attendue[NOM-05]",
        attendu="NOM-05 attend 3 000 € ; l'ordre inversé donnerait 2 700 €",
    ),
    Mutation(
        nom="le plafond redevient un critère d'éligibilité",
        fichier=SOURCE / "regles" / "eligibilite.py",
        avant='        motifs.append("sinistre non couvert par la formule")',
        apres='        motifs.append("sinistre non couvert par la formule")'
        '\n    if sinistre["montant_declare"] > formules.plafond(contrat["formule"]):'
        '\n        motifs.append("montant supérieur au plafond")',
        test=f"{ACCEPTANCE}/test_equipe_orchestration.py::"
        "test_scenario_nominal_produit_la_decision_attendue[NOM-05]",
        attendu="NOM-05 serait refusée au lieu d'être acceptée",
    ),
    Mutation(
        nom="la trace nomme le répartiteur au lieu de l'agent",
        fichier=SOURCE / "orchestration" / "repartiteur.py",
        avant="            agent.NOM,",
        apres='            "repartiteur",',
        test=f"{ACCEPTANCE}/test_equipe_orchestration.py::"
        "test_scenario_nominal_produit_la_decision_attendue[NOM-01]",
        attendu="le greffier deviendrait l'auteur des cinq sections",
    ),
    Mutation(
        nom="le mode dégradé marque toutes les demandes",
        fichier=SOURCE / "agents" / "decision.py",
        avant='    elif e["controle_requis"] and e["partenaire_indisponible"]:',
        apres="    elif True:",
        test=f"{ACCEPTANCE}/test_collaboration_a2a.py::"
        "test_partenaire_en_panne_le_mode_degrade_s_applique_sans_bloquer_le_reste[PAN-01]",
        attendu="trois des cinq fiches de PAN-01 ne doivent pas être marquées",
    ),
    Mutation(
        nom="le seuil du mode dégradé passe à 15 000 €",
        fichier=SOURCE / "regles" / "issues.py",
        avant="SEUIL_MODE_DEGRADE = 1_500.0",
        apres="SEUIL_MODE_DEGRADE = 15_000.0",
        test=f"{ACCEPTANCE}/test_collaboration_a2a.py::"
        "test_partenaire_en_panne_le_mode_degrade_s_applique_sans_bloquer_le_reste[PAN-01]",
        attendu="KAL-26-0404 doit partir en cellule_fraude",
    ),
    Mutation(
        nom="l'arrêt n'est plus signalé dans la fiche",
        fichier=SOURCE / "orchestration" / "repartiteur.py",
        avant="        if borne:",
        apres="        if borne and False:",
        test=f"{ACCEPTANCE}/test_equipe_orchestration.py::"
        "test_scenario_piege_a_boucle_s_arrete_dans_les_bornes",
        attendu="BCL-01 exige un arrêt nommé",
    ),
    Mutation(
        nom="la borne d'étapes est desserrée à 1 000",
        fichier=SOURCE / "orchestration" / "bornes.py",
        avant='    "etapes_max": 10,',
        apres='    "etapes_max": 1000,',
        test=f"{CHANTIER_1}/test_bornes.py::"
        "test_les_bornes_publiees_sont_celles_qui_ont_ete_decidees",
        attendu="desserrer une borne pour faire passer un test doit rester visible",
    ),
    Mutation(
        nom="les mesures comptent un appel de trop",
        fichier=SOURCE / "mesures.py",
        avant='        entree["appels"] += 1',
        apres='        entree["appels"] += 2',
        test=f"{CHANTIER_1}/test_invariants.py::"
        "test_i7_chaque_agent_a_ses_mesures_et_ses_appels_comptent_ses_etapes[NOM-01]",
        attendu="le nombre d'appels doit égaler le nombre d'étapes",
    ),
    Mutation(
        nom="un agent importe un autre agent",
        fichier=SOURCE / "agents" / "estimation.py",
        avant="from ..regles import montants as regles_montants",
        apres="from ..regles import montants as regles_montants"
        "\nfrom . import pieces  # noqa: F401",
        test=f"{CHANTIER_1}/test_architecture.py::"
        "test_aucun_agent_n_importe_un_autre_agent[estimation]",
        attendu="D5 — un agent ne renvoie pas le travail à un autre",
    ),
    Mutation(
        nom="un agent écrit directement dans le dossier",
        fichier=SOURCE / "agents" / "eligibilite.py",
        avant="    motifs = regles_eligibilite.motifs_non_eligibilite(",
        apres="    if False:  # branche morte : la lecture des imports doit la voir quand même"
        '\n        entrees.publier("eligibilite", None, NOM)'
        "\n    motifs = regles_eligibilite.motifs_non_eligibilite(",
        test=f"{CHANTIER_1}/test_architecture.py::test_seul_le_repartiteur_ecrit_dans_le_dossier",
        attendu="D7 — seul le répartiteur dépose dans le dossier",
    ),
    Mutation(
        nom="l'agent anti-fraude publie un avis qu'il a inventé",
        fichier=SOURCE / "agents" / "antifraude.py",
        avant='    verdict = entrees["passerelle"].consulter(entrees["demande"])',
        apres='    verdict = {"avis": {"niveau": "faible", "score": 0.1},'
        ' "cause": None, "evaluation_id": "EVA-invente"}',
        test=f"{ACCEPTANCE}/test_collaboration_a2a.py::"
        "test_echange_antifraude_respecte_le_contrat_et_ne_transmet_que_les_donnees_autorisees"
        "[AF-04]",
        attendu="l'avis de fraude est émis par le partenaire, jamais en interne",
    ),
    Mutation(
        nom="la page n'ajoute plus la racine au chemin d'import",
        fichier=DEMO / "app.py",
        avant="if str(RACINE) not in sys.path:",
        apres="if False:",
        test=f"{CHANTIER_1}/test_demo.py::"
        "test_la_page_se_charge_dans_les_conditions_reelles_de_streamlit",
        attendu="`streamlit run` ne met pas la racine du dépôt dans sys.path",
    ),
    Mutation(
        nom="l'arbre de décision allume une branche trop tôt",
        fichier=DEMO / "vues.py",
        avant="    retenue = regle_appliquee(fiche) if visible else None",
        apres="    retenue = regle_appliquee(fiche)",
        test=f"{CHANTIER_1}/test_demo.py::"
        "test_l_arbre_n_allume_la_branche_qu_une_fois_le_parcours_acheve",
        attendu="tant que le parcours se déroule, l'issue n'est pas connue",
    ),
    Mutation(
        nom="la charge est un filtre de la demande",
        fichier=SOURCE / "partenaire" / "charge.py",
        avant='        "departement": departement(demande["assure"]["code_postal"]),',
        apres='        "departement": departement(demande["assure"]["code_postal"]),'
        '\n        "code_postal": demande["assure"]["code_postal"],',
        test=f"{CHANTIER_2}/test_charge_envoyee.py::"
        "test_s10_la_charge_porte_exactement_les_sept_champs_du_contrat",
        attendu="le contrat n_accepte aucun champ en dehors des sept",
    ),
    Mutation(
        nom="la validation accepte un champ en trop",
        fichier=SOURCE / "partenaire" / "validation.py",
        avant="    if presents - CHAMPS_REPONSE:",
        apres="    if False:",
        test="tests/acceptance/test_collaboration_a2a.py::"
        "test_reponse_invalide_du_partenaire_est_rejetee_et_non_propagee[INV-03]",
        attendu="une reponse non conforme n_engage pas le partenaire",
    ),
    Mutation(
        nom="le delai d_abandon passe de 3 s a 30 s",
        fichier=SOURCE / "partenaire" / "passerelle.py",
        avant="DELAI_ABANDON_S = 3.0",
        apres="DELAI_ABANDON_S = 30.0",
        test=f"{CHANTIER_2}/test_robustesse.py::"
        "test_s12_bis_aucune_demande_n_attend_au_dela_du_delai_d_abandon",
        attendu="le contrat fixe l_abandon a 3 s au plus tard",
    ),
    Mutation(
        nom="le registre n_empeche plus le second appel",
        fichier=SOURCE / "partenaire" / "passerelle.py",
        avant="        if self.registre.deja_appele(reference):",
        apres="        if False:",
        test=f"{CHANTIER_2}/test_registre.py::test_un_second_appel_sur_le_meme_dossier_est_refuse",
        attendu="un doublon est un manquement contractuel",
    ),
    Mutation(
        nom="une defaillance d_agent remonte a l_appelant",
        fichier=SOURCE / "orchestration" / "repartiteur.py",
        avant="                borne = bornes.AGENT_DEFAILLANT\n                break",
        apres="                raise",
        test=f"{CHANTIER_2}/test_robustesse.py::"
        "test_s16_un_agent_defaillant_ne_prive_pas_la_demande_de_son_issue",
        attendu="EX-1 : une demande ne reste jamais sans issue",
    ),
    Mutation(
        nom="le niveau n_est plus confronte au score",
        fichier=SOURCE / "partenaire" / "validation.py",
        avant='    if evaluation["niveau"] != niveau_attendu(score):',
        apres="    if False:",
        test="tests/acceptance/test_collaboration_a2a.py::"
        "test_reponse_invalide_du_partenaire_est_rejetee_et_non_propagee[INV-02]",
        attendu="le contrat lie le niveau au score",
    ),
]


def lancer(test: str) -> bool:
    """Vrai si le test passe."""
    acheve = subprocess.run(
        [sys.executable, "-m", "pytest", test, "-q", "--no-header", "-x"],
        cwd=RACINE,
        capture_output=True,
        text=True,
    )
    return acheve.returncode == 0


def main() -> int:
    largeur = max(len(m.nom) for m in MUTATIONS) + 2
    print(f"{'mutation':<{largeur}} {'test':<8} verdict")
    print("-" * (largeur + 24))
    anomalies = 0

    for mutation in MUTATIONS:
        origine = mutation.fichier.read_text(encoding="utf-8")
        if mutation.avant not in origine:
            print(f"{mutation.nom:<{largeur}} {'-':<8} ANCRE INTROUVABLE")
            anomalies += 1
            continue

        try:
            mutation.fichier.write_text(
                origine.replace(mutation.avant, mutation.apres, 1), encoding="utf-8"
            )
            passe = lancer(mutation.test)
        finally:
            mutation.fichier.write_text(origine, encoding="utf-8")

        if passe:
            anomalies += 1
        print(
            f"{mutation.nom:<{largeur}} {'passe' if passe else 'tombe':<8} "
            f"{'NON DETECTE' if passe else 'detecte'}"
        )

    print("-" * (largeur + 24))
    print(f"{len(MUTATIONS)} mutations, {anomalies} non detectee(s)")
    return 1 if anomalies else 0


if __name__ == "__main__":
    raise SystemExit(main())
