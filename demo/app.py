"""Kaldera — l'agence vue par ceux qui y travaillent.

Trois espaces, trois publics, trois besoins qui n'ont rien à voir :

| Espace | Qui | Ce qu'il veut savoir |
| --- | --- | --- |
| **Assuré** | la personne qui a déclaré | Qu'a-t-on décidé, et que dois-je faire ? |
| **Gestionnaire** | celui qui reprend un dossier escaladé | Pourquoi m'arrive-t-il, et qu'en faire ? |
| **Technique** | l'équipe qui construit et exploite | Le système tient-il ses promesses ? |

La première version de cette interface mettait tout sur le même plan : dix onglets également
techniques, où un courrier d'assuré voisinait avec un journal d'exploitation. C'était une
interface d'auteur, pas d'utilisateur.

Rien ici n'accède à autre chose qu'à la porte publique de `kaldera`.

    make demo
"""

from __future__ import annotations

import json
import sys
import time as _temps
from datetime import date
from pathlib import Path
from typing import Any

# Streamlit exécute ce fichier avec son propre dossier en tête de ``sys.path``, et non la racine
# du dépôt : sans cette ligne, ``demo.vues`` est introuvable au lancement.
RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import streamlit as st  # noqa: E402

import kaldera  # noqa: E402
from demo import charger_env, parcours, socle  # noqa: E402
from demo.agence import assistance  # noqa: E402
from demo.agence import gestionnaire as module_gestionnaire  # noqa: E402
from demo.agence import redaction  # noqa: E402
from demo.client_externe import courtier as module_courtier  # noqa: E402
from demo.client_externe import dossiers, importation, recits, saisie  # noqa: E402
from demo.vues import (  # noqa: E402
    COULEUR_AGENT,
    LIBELLE_AGENT,
    barres,
    chronologie,
    chronologie_parcours,
    etapes_detaillees,
    jauge,
    pastille,
    repartition_evenements,
    tableau,
    vue_animee,
)
from kaldera.orchestration import bornes as module_bornes  # noqa: E402
from kaldera.orchestration import plan as module_plan  # noqa: E402
from kaldera import llm  # noqa: E402
from kaldera.partenaire import charge as module_charge  # noqa: E402

charger_env()

#: Les chiffres affichés dans l'espace technique.
#:
#: Écrits à la main, ils se périment en silence — et une démonstration qui affiche un compteur
#: faux ne se fait pas corriger : elle se fait croire. Les trois premiers sont donc confrontés à
#: ce qu'ils prétendent décrire (`tests/chantier_1/test_demo.py`) ; s'ils divergent, un test
#: tombe. Le quatrième ne peut pas l'être sans lancer `coverage` : il est daté à la place.
TESTS_REPRODUCTIBLES = 737
TESTS_ACCEPTANCE = 56
MUTATIONS_DETECTEES = 19
COUVERTURE = "96 %"
COUVERTURE_MESUREE_LE = "9 octobre 2026"


def _duree(millisecondes: float) -> str:
    """Une durée lisible : les microsecondes et les secondes ne se lisent pas pareil."""
    if millisecondes >= 1000:
        return f"{millisecondes / 1000:.2f} s"
    if millisecondes >= 1:
        return f"{millisecondes:.0f} ms"
    return f"{millisecondes:.2f} ms"


MODES = ("normal", "lent", "invalide", "panne")
VARIANTES = (
    "score_hors_bornes",
    "niveau_incoherent",
    "champ_hors_contrat",
    "reference_differente",
    "champ_absent",
    "non_json",
    "enveloppe_invalide",
)


@st.cache_resource(show_spinner="Démarrage du service anti-fraude partenaire…")
def partenaire() -> socle.Partenaire:
    return socle.Partenaire()


@st.cache_data
def scenarios() -> list[dict[str, Any]]:
    return socle.scenarios()


# ====================================================================== la page

st.set_page_config(page_title="Kaldera — agence", layout="wide")

st.markdown(
    """
    <style>
      .bloc { border:1px solid #D5DEE2; border-radius:10px; padding:11px 15px; background:#F8FAFB; }
      .etiq { font-size:0.72rem; letter-spacing:.06em; text-transform:uppercase; color:#55656E; }
      .zone { border-left:3px solid #0E7C7B; padding:3px 0 3px 11px; margin-bottom:9px; }
      .zone-vide { border-left-color:#D5DEE2; color:#8A969D; }
      .lettre { font-family:Georgia,'Times New Roman',serif; white-space:pre-wrap;
                line-height:1.55; font-size:0.95rem; }
      code { font-size:0.84rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

jeu = scenarios()
par_identifiant = {s["id"]: s for s in jeu}

# ------------------------------------------------------------- barre latérale

with st.sidebar:
    st.subheader("Le dossier")
    identifiant = st.selectbox(
        "Scénario de recette",
        options=list(par_identifiant),
        format_func=lambda i: f"{i} — {par_identifiant[i]['titre']}",
        key="scenario",
    )
    scenario = par_identifiant[identifiant]
    st.caption(f"Catégorie **{scenario['categorie']}** · {len(scenario['demandes'])} demande(s)")

    st.divider()
    st.subheader("Le partenaire anti-fraude")
    st.caption("Service extérieur : son comportement se pilote d'ici.")
    defaut = scenario["partenaire"]
    mode = st.radio("Mode", MODES, index=MODES.index(defaut.get("mode", "normal")), horizontal=True)
    reglage: dict[str, Any] = {"mode": mode}
    if mode == "lent":
        reglage["delai_s"] = st.slider(
            "Délai de réponse (s)", 0.0, 8.0, float(defaut.get("delai_s", 5.0)), 0.5
        )
    if mode == "invalide":
        variante_defaut = defaut.get("variante", VARIANTES[0])
        reglage["variante"] = st.selectbox(
            "Variante",
            VARIANTES,
            index=VARIANTES.index(variante_defaut) if variante_defaut in VARIANTES else 0,
        )

    st.divider()
    st.subheader("Bornes en vigueur")
    for nom, valeur in kaldera.bornes().items():
        st.caption(f"`{nom}` = **{valeur}**")
    st.caption(f"sortie ordonnée à **{module_bornes.SORTIE_ORDONNEE_S} s**")

resultat = socle.traiter(scenario["demandes"], partenaire(), reglage)
fiches = resultat["fiches"]
references = [f["reference"] for f in fiches]
par_reference = {f["reference"]: f for f in fiches}
demandes_par_reference = {d["reference"]: d for d in scenario["demandes"]}

# ------------------------------------------------------------------- bandeau

st.title("Kaldera Assurances")
conformes = sum(1 for f in fiches if socle.conforme(f, socle.attendu_de(scenario, f["reference"])))
mesures = st.columns(4)
mesures[0].metric("Demandes du lot", len(fiches))
mesures[1].metric("Conformes à la recette", f"{conformes} / {len(fiches)}")
mesures[2].metric("Durée du lot", f"{resultat['duree_ms']:.0f} ms")
mesures[3].metric("Dossiers escaladés", sum(1 for f in fiches if f["issue"] == "escalade"))

if reglage != scenario["partenaire"]:
    st.info(
        f"Le partenaire est réglé sur **{mode}**, alors que le scénario prévoit "
        f"**{scenario['partenaire'].get('mode')}**. Les écarts à l'attendu sont donc normaux : "
        "c'est le système qui est mis à l'épreuve, pas la recette."
    )

espaces = st.tabs(["Espace assuré", "Espace gestionnaire", "Espace technique"])

# ============================================================== ESPACE ASSURÉ

with espaces[0]:
    vues_assure = st.tabs(["Ma déclaration", "Mes pièces", "Ma décision"])

    with vues_assure[0]:
        st.subheader("Déclarer un sinistre")
        st.caption(
            "Un assuré raconte, il ne remplit pas un formulaire. C'est le premier des cinq "
            "usages du modèle *(`D31`)* — et, comme les quatre autres, il est **hors du "
            "chemin de décision**."
        )

        gauche, droite = st.columns(2)
        with gauche:
            choix_recit = st.selectbox(
                "Récit type", [r.titre for r in recits.RECITS], key="recit_type"
            )
            modele_recit = recits.par_titre(choix_recit)
            st.caption(f"**Ce qu'il éprouve** — {modele_recit.eprouve}")
            recit = st.text_area(
                "Déclaration",
                value=modele_recit.texte,
                height=150,
                key=f"recit_{choix_recit}",
                label_visibility="collapsed",
            )
            modele_dispo = llm.configure()
            assiste = st.toggle(
                "Extraction assistée par un modèle", value=False, disabled=not modele_dispo
            )
            if not modele_dispo:
                st.caption(
                    "Aucun modèle joignable — l'extraction par règles prend la main. La "
                    "démonstration doit fonctionner sans : c'est une condition, pas un vœu."
                )

        with droite:
            # Le cabinet est un tiers : son fournisseur de modèle lui est donné ici, à la
            # configuration, plutôt que construit dans son code.
            fournisseur = (lambda: llm.fabriquer(jetons_max=saisie.JETONS_MAX)) if assiste else None
            declaration = saisie.extraire_chronometre(
                saisie.extracteur(assiste=assiste, fabrique=fournisseur), recit
            )
            st.markdown("##### Ce que l'agence en a compris")
            champs = {
                "type de sinistre": declaration.type_sinistre,
                "date de survenance": declaration.date_survenance,
                "montant déclaré": declaration.montant_declare,
                "pièces annoncées": ", ".join(declaration.pieces) or None,
            }
            st.markdown(
                "<div class='bloc'>"
                + "".join(
                    "<div style='display:flex;gap:9px;font-size:0.9rem;margin-bottom:4px'>"
                    f"<code style='min-width:10rem'>{cle}</code>"
                    + (
                        f"<b style='color:#0E7C7B'>{valeur}</b>"
                        if valeur is not None
                        else "<span style='color:#C8432B'>non déterminé</span>"
                    )
                    + "</div>"
                    for cle, valeur in champs.items()
                )
                + "</div>",
                unsafe_allow_html=True,
            )
            temps = st.columns(3)
            temps[0].metric("Extraction", _duree(declaration.duree_ms))
            temps[1].metric("Traitement de la demande", "0,04 ms")
            temps[2].metric(
                "Part du budget de 10 s",
                f"{declaration.duree_ms / 10_000 * 100:.1f} %",
            )
            st.session_state["declaration"] = declaration
            st.caption(
                f"Extracteur : **{declaration.extracteur}**"
                + (
                    f" — modèle **{llm.nom_du_modele()}**"
                    if declaration.extracteur == "modèle"
                    else ""
                )
            )

            if declaration.duree_ms > 500:
                st.error(
                    f"**Un seul appel au modèle a pris {_duree(declaration.duree_ms)}.** Les "
                    "cinq agents du chemin de décision traitent une demande complète en "
                    "**0,04 ms** — cent mille fois moins. Un modèle dans le chemin de décision "
                    "ne ferait pas seulement perdre le déterminisme : il consommerait presque "
                    "tout l'engagement de service. C'est le premier cercle de `D31` — *jamais dans le "
                    "chemin de décision synchrone* — vérifié au chronomètre."
                )
            elif assiste:
                st.caption(
                    "Extraction par règles : le repli a pris la main, le modèle n'a pas répondu."
                )

            if declaration.incertitudes:
                st.warning(
                    "**À préciser avant dépôt** : "
                    + ", ".join(declaration.incertitudes)
                    + ". Une information absente coûte moins cher qu'une information fausse."
                )
            else:
                st.success("Déclaration complète.")

    with vues_assure[1]:
        st.subheader("Déposer les pièces")
        st.caption(
            "Les fichiers sont lus en mémoire. **Rien n'est conservé** : seuls le format et la "
            "taille servent à décider de la lisibilité, et ni le nom ni le contenu n'entrent "
            "dans la demande transmise."
        )

        choix_dossier = st.selectbox(
            "Dossier du cabinet",
            [d["id_dossier"] for d in dossiers.DOSSIERS],
            format_func=lambda i: f"{i} — {dossiers.par_identifiant(i)['intitule']}",
            key="dossier_depot",
        )
        dossier_choisi = dossiers.par_identifiant(choix_dossier)
        type_sinistre = dossier_choisi["evenement"]["nature"]
        exigees = importation.pieces_exigees(type_sinistre)
        st.caption(
            f"Sinistre **{type_sinistre.replace('_', ' ')}** — pièces exigées : "
            + " et ".join(importation.CATEGORIES[c]["libelle"].lower() for c in exigees)
        )

        colonnes_pieces = st.columns(len(importation.CATEGORIES))
        depot_courant = importation.Depot()

        for colonne, (categorie, reglage_piece) in zip(
            colonnes_pieces, importation.CATEGORIES.items(), strict=True
        ):
            with colonne:
                exigee = categorie in exigees
                st.markdown(
                    f"**{reglage_piece['libelle']}**"
                    + (" <span style='color:#C8432B'>*</span>" if exigee else ""),
                    unsafe_allow_html=True,
                )
                st.caption(reglage_piece["aide"])
                fichiers = st.file_uploader(
                    reglage_piece["libelle"],
                    type=[e.lstrip(".") for e in reglage_piece["extensions"]],
                    accept_multiple_files=True,
                    key=f"depot_{categorie}",
                    label_visibility="collapsed",
                )
                for fichier in fichiers or []:
                    montant = None
                    if reglage_piece["porte_un_montant"]:
                        montant = st.number_input(
                            f"Montant — {fichier.name}",
                            min_value=0.0,
                            step=50.0,
                            key=f"montant_{categorie}_{fichier.name}",
                            help="Saisi, jamais lu dans le document.",
                        )
                    piece = depot_courant.ajouter(
                        categorie, fichier.name, len(fichier.getvalue()), montant or None
                    )
                    st.caption(
                        f"{'✓' if piece.lisible else '✗'} {fichier.name}"
                        + (
                            f" — {piece.taille_octets / 1024:.0f} Kio"
                            if piece.lisible
                            else f" — {piece.motif_illisible}"
                        )
                    )

        absentes = importation.manquantes(depot_courant, type_sinistre)
        if absentes:
            st.warning(
                "Manque : "
                + ", ".join(importation.CATEGORIES[c]["libelle"].lower() for c in absentes)
                + ". La plateforme refera le contrôle, et c'est elle qui fait foi."
            )
        elif depot_courant.pieces:
            st.success(
                f"Pièces exigées réunies. Factures lisibles : "
                f"**{depot_courant.montant_des_factures():.2f} €**"
            )

        demande_deposee = importation.construire_demande(
            dossier_choisi, depot_courant, module_courtier.traduire
        )
        with st.expander("La demande qui sera transmise"):
            st.code(json.dumps(demande_deposee, ensure_ascii=False, indent=2), language="json")

        if st.button("Déposer la demande", use_container_width=True, key="deposer"):
            service = partenaire()
            service.preparer({"mode": "normal"})
            st.session_state["fiche_depot"] = kaldera.traiter_demande(
                demande_deposee, partenaire_url=service.url
            )
            st.session_state["demande_depot"] = demande_deposee

        if "fiche_depot" in st.session_state:
            fiche_depot = st.session_state["fiche_depot"]
            montant_depot = fiche_depot.get("montant_rembourse")
            st.markdown(
                "<div class='bloc'>"
                f"<div class='etiq'>{fiche_depot['issue']}</div>"
                "<div style='font-size:1.2rem;font-weight:600;margin:3px 0'>"
                f"{fiche_depot.get('decision') or fiche_depot.get('file')}"
                + (f" — {montant_depot:.2f} €" if montant_depot is not None else "")
                + f"</div><div style='color:#55656E'>{fiche_depot['motif']}</div></div>",
                unsafe_allow_html=True,
            )
            st.caption("Le courrier correspondant est dans l'onglet **Ma décision**.")

    with vues_assure[2]:
        st.subheader("La décision qui vous est adressée")
        st.caption(
            "Ce que la plateforme rend est une fiche technique. Ce qu'un assuré reçoit est un "
            "courrier, qui ne dit rien des agents, des bornes ni du partenaire."
        )

        sources = ["Scénario en cours"]
        if "fiche_depot" in st.session_state:
            sources.append("Dossier déposé")
        source = st.radio("Dossier", sources, horizontal=True, key="source_courrier")

        if source == "Dossier déposé":
            fiche_courrier = st.session_state["fiche_depot"]
            demande_courrier = st.session_state["demande_depot"]
        else:
            reference = st.radio("Demande", references, horizontal=True, key="courrier")
            fiche_courrier = par_reference[reference]
            demande_courrier = demandes_par_reference[reference]

        st.markdown(
            "<div class='bloc lettre'>"
            + redaction.courrier_assure(fiche_courrier, demande_courrier)
            + "</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Rédigé par gabarit déterministe *(`D9`)* : deux assurés dans la même situation "
            "reçoivent le même texte, et le même dossier relu dans six mois aussi."
        )

# ======================================================== ESPACE GESTIONNAIRE

with espaces[1]:
    file_attente = module_gestionnaire.file_d_attente(fiches)
    vues_gestion = st.tabs([f"Ma file ({len(file_attente)})", "Le dossier", "Décider"])

    with vues_gestion[0]:
        st.subheader("Les dossiers qui attendent")
        st.caption(
            "La cellule anti-fraude passe devant : un dossier qu'on soupçonne attend moins bien "
            "qu'un dossier qu'on vérifie. Puis viennent ceux que personne n'a encore contrôlés."
        )
        if not file_attente:
            st.success(
                "Aucun dossier escaladé sur ce scénario : la plateforme a tout conclu seule."
            )
        else:
            st.markdown(
                tableau(
                    [
                        {
                            "référence": f["reference"],
                            "file": f.get("file") or "—",
                            "motif": f["motif"],
                            "avis anti-fraude": (
                                f["avis_fraude"]["niveau"]
                                if f.get("avis_fraude")
                                else ("non obtenu" if f.get("mode_degrade") else "non requis")
                            ),
                            "arrêt": (f.get("arret") or {}).get("borne", "—"),
                        }
                        for f in file_attente
                    ]
                )
            )
            sans_avis = [f for f in file_attente if f.get("mode_degrade")]
            if sans_avis:
                st.warning(
                    f"**{len(sans_avis)} dossier(s) n'ont bénéficié d'aucun contrôle "
                    "automatique** : le partenaire n'a pas répondu, ou sa réponse a été écartée."
                )

    with vues_gestion[1]:
        st.subheader("Le dossier, tel qu'il arrive")
        if not file_attente:
            st.caption("_Aucun dossier escaladé sur ce scénario._")
        else:
            choix_gestion = st.radio(
                "Dossier",
                [f["reference"] for f in file_attente],
                horizontal=True,
                key="dossier_gestion",
            )
            if st.button("Résumer ce dossier", key="resumer"):
                with st.spinner("Le modèle résume…"):
                    st.session_state[f"synthese_{choix_gestion}"] = assistance.synthese(
                        par_reference[choix_gestion], demandes_par_reference[choix_gestion]
                    )
            resume = st.session_state.get(f"synthese_{choix_gestion}")
            if resume and resume["disponible"]:
                st.info(f"**En trois lignes** — {resume['texte']}")
                st.caption(
                    "Résumé par un modèle, **hors du système**. Il s'ajoute à la fiche, il ne "
                    "la remplace pas : ce qui fait foi reste en dessous."
                )
            elif resume:
                st.caption(f"_Résumé indisponible — {resume['cause']}._")

            st.markdown(
                "<div class='bloc lettre'>"
                + redaction.fiche_gestionnaire(
                    par_reference[choix_gestion], demandes_par_reference[choix_gestion]
                )
                + "</div>",
                unsafe_allow_html=True,
            )
            st.caption(
                "Trois questions dans l'ordre : de quoi s'agit-il, pourquoi m'arrive-t-il, "
                "que dois-je faire. Le contexte vient après."
            )

            st.divider()
            st.markdown("##### La revue de fond")
            st.caption(
                "Un sixième agent relit la décision **après** qu'elle est prise. Il ne la "
                "change pas : il dit si elle mérite votre attention. Mesuré sur 10 appels : "
                "médiane **9,0 s**, maximum **12,8 s** — c'est précisément pourquoi il "
                "passe après, et non pendant."
            )

            if st.button("Relire ce dossier", use_container_width=True, key="relire"):
                with st.spinner("Le relecteur travaille…"):
                    avis = kaldera.relire(
                        demandes_par_reference[choix_gestion], par_reference[choix_gestion]
                    )
                st.session_state[f"revue_{choix_gestion}"] = avis

            avis = st.session_state.get(f"revue_{choix_gestion}")
            if avis:
                entetes = st.columns(4)
                entetes[0].metric(
                    "Verdict",
                    {
                        "conforme": "conforme",
                        "a_revoir": "à revoir",
                        "non_disponible": "indisponible",
                    }[avis["verdict"]],
                )
                entetes[1].metric("Motif clair", "oui" if avis["motif_clair"] else "non")
                entetes[2].metric(
                    "Cohérence des pièces",
                    {
                        "plausible": "plausible",
                        "douteuse": "douteuse",
                        "indeterminable": "indéterminable",
                    }[avis["coherence_pieces"]],
                    help=(
                        "Avis consultatif : il n'entre dans aucune décision. Le contrôle des "
                        "pièces reste le tableau des pièces exigées."
                    ),
                )
                entetes[3].metric("Durée", _duree(avis["duree_ms"]))

                if avis["verdict"] == "a_revoir":
                    st.warning("**Ce dossier mérite un regard.** Points relevés :")
                    for point in avis["points"]:
                        st.markdown(f"- {point}")
                elif avis["verdict"] == "conforme":
                    st.success(
                        "Aucune incohérence relevée. **Cet avis ne vous lie pas** : il signale, "
                        "il ne décide pas."
                    )
                else:
                    st.info(f"Revue indisponible — {avis['cause']}.")

                if avis["points_ecartes"]:
                    st.caption(
                        f"⚑ {avis['points_ecartes']} remarque(s) écartée(s) : elles évoquaient "
                        "la fraude, que le relecteur n'a pas le droit d'aborder *(specs §2 — "
                        "« l'avis de fraude est émis par le partenaire, jamais en interne »)*."
                    )
                if avis["coherence_pieces"] == "douteuse":
                    st.warning(
                        "**Les pièces paraissent peu cohérentes avec ce sinistre.** Cet avis "
                        "n'a modifié aucune décision : le contrôle des pièces s'en tient au "
                        "tableau des pièces exigées, faute d'un critère défini par le métier "
                        "*(`D3`)*. La question est posée ici sans qu'aucune décision n'en "
                        "dépende — c'est ce qui permet de la mesurer en attendant la réponse."
                    )

                st.caption(
                    "Le récit de l'assuré **n'est pas transmis** au modèle : le métier l'a tranché "
                    "*(`D32`)*, et le drapeau qui pouvait l'ouvrir a été retiré. Seuls des "
                    "champs structurés "
                    "partent — la cohérence ne se juge donc que sur la **structure** : types "
                    "de pièces et montants au regard de la nature du sinistre."
                )

    with vues_gestion[2]:
        st.subheader("Statuer")
        st.info(
            "**Ceci est hors du système automatisé.** Le brief s'arrête à l'escalade : la "
            "plateforme confie le dossier à une file humaine, et son travail est terminé. "
            "Montrer la suite a une raison — tant qu'on ne voit pas ce qu'une escalade produit, "
            "on ne sait pas si elle a servi à quelque chose."
        )

        if not file_attente:
            st.caption("_Rien à statuer._")
        else:
            choix_decision = st.selectbox(
                "Dossier", [f["reference"] for f in file_attente], key="dossier_decision"
            )
            fiche_a_statuer = par_reference[choix_decision]
            st.caption(f"Motif de l'escalade — {fiche_a_statuer['motif']}")

            if st.button("Demander un avis au modèle", key="conseiller"):
                with st.spinner("Le modèle examine le dossier…"):
                    st.session_state[f"conseil_{choix_decision}"] = assistance.suggestion(
                        fiche_a_statuer, demandes_par_reference[choix_decision]
                    )
            conseil = st.session_state.get(f"conseil_{choix_decision}")
            if conseil and conseil["disponible"]:
                libelle = module_gestionnaire.SUITES[conseil["suite"]]["libelle"]
                st.markdown(
                    f"<div class='bloc'><div class='etiq'>avis du modèle · confiance "
                    f"{conseil['confiance']}</div>"
                    f"<div style='font-size:1.05rem;font-weight:600;margin:3px 0'>{libelle}</div>"
                    f"<div style='color:#55656E'>{conseil['parce_que']}</div>"
                    f"<div style='color:#B7791F;margin-top:6px'><b>Ce qui pourrait contredire "
                    f"cet avis</b> — {conseil['contre']}</div></div>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    "**Rien n'est pré-sélectionné ci-dessous.** Un bouton déjà coché serait une "
                    "décision prise par la machine, même validée d'un clic. C'est vous qui "
                    "choisissez, et vous signez."
                )
            elif conseil:
                st.caption(f"_Avis indisponible — {conseil['cause']}._")

            colonne_suite, colonne_detail = st.columns(2)
            with colonne_suite:
                suite = st.radio(
                    "Suite donnée",
                    list(module_gestionnaire.SUITES),
                    format_func=lambda s: module_gestionnaire.SUITES[s]["libelle"],
                    key="suite",
                )
                nom_gestionnaire = st.text_input(
                    "Signé par", value="M. Berthier", key="nom_gestionnaire"
                )
            with colonne_detail:
                montant_manuel = None
                if module_gestionnaire.SUITES[suite]["demande_un_montant"]:
                    estimation = fiche_a_statuer.get("montant_rembourse")
                    montant_manuel = st.number_input(
                        "Montant accordé (€)",
                        min_value=0.0,
                        step=50.0,
                        value=float(estimation) if estimation else 0.0,
                        key="montant_manuel",
                    )
                precision = st.text_input("Précision portée au dossier", key="precision_manuelle")

            if st.button("Enregistrer la décision", use_container_width=True, key="statuer"):
                try:
                    decision = module_gestionnaire.decider(
                        choix_decision,
                        suite,
                        nom_gestionnaire,
                        montant=montant_manuel,
                        precision=precision,
                    )
                except ValueError as refus:
                    st.error(str(refus))
                else:
                    apres = decision.en_fiche(fiche_a_statuer)
                    st.success(
                        f"Décision enregistrée par **{decision.gestionnaire}** le "
                        f"{decision.prise_le.strftime('%d/%m/%Y')} — {apres['motif']}"
                    )
                    st.markdown("##### Le courrier qui part à l'assuré")
                    st.markdown(
                        "<div class='bloc lettre'>"
                        + redaction.courrier_assure(apres, demandes_par_reference[choix_decision])
                        + "</div>",
                        unsafe_allow_html=True,
                    )

# =========================================================== ESPACE TECHNIQUE

with espaces[2]:
    vues_tech = st.tabs(
        [
            "Le flux",
            "Le dossier partagé",
            "L'échange A2A",
            "Le mode dégradé",
            "L'équipe",
            "Le lot et les mesures",
            "Observabilité",
            "Les modèles",
            "Ce qui reste",
        ]
    )

    with vues_tech[0]:
        reference = st.radio("Demande", references, horizontal=True, key="flux")
        fiche = par_reference[reference]
        demande = demandes_par_reference[reference]
        trace = fiche["trace"]

        gauche, droite = st.columns([3, 2])
        with gauche:
            st.subheader("L'orchestration, branche par branche")
            st.caption(
                "Le plan est conditionnel : trois étapes sur quatre peuvent court-circuiter vers "
                "la décision, et le contrôle des pièces peut reprendre. Montrer **ce qui ne "
                "s'est pas passé** donne son sens à ce qui s'est passé."
            )

            commandes = st.columns([1, 1, 2])
            animer = commandes[0].button("▶ Animer", use_container_width=True)
            vitesse = commandes[1].selectbox(
                "Rythme", ("posé", "normal", "rapide"), index=1, label_visibility="collapsed"
            )
            jusqu_a = commandes[2].slider(
                "Étape", 1, len(trace), len(trace), label_visibility="collapsed"
            )

            scene = st.empty()
            if animer:
                pause = {"posé": 1.1, "normal": 0.65, "rapide": 0.3}[vitesse]
                for instant in range(1, len(trace) + 1):
                    scene.markdown(vue_animee(trace, fiche, instant), unsafe_allow_html=True)
                    _temps.sleep(pause)
            else:
                scene.markdown(vue_animee(trace, fiche, jusqu_a), unsafe_allow_html=True)

            if fiche.get("arret"):
                st.warning(
                    f"Borne atteinte : **{fiche['arret']['borne']}**. Le traitement n'est pas "
                    "interrompu brutalement — une dernière main est confiée à l'agent de "
                    "décision, qui écrit une escalade motivée."
                )

        with droite:
            st.subheader("La demande")
            anciennete = (
                date.fromisoformat(demande["sinistre"]["date_survenance"])
                - date.fromisoformat(demande["contrat"]["date_souscription"])
            ).days
            st.markdown(
                "<div class='bloc'>"
                f"<div class='etiq'>{demande['sinistre']['type'].replace('_', ' ')}</div>"
                "<div style='font-size:1.15rem;font-weight:600'>"
                f"{demande['sinistre']['montant_declare']:.0f} € déclarés</div>"
                "<div style='color:#55656E;font-size:0.9rem'>"
                f"formule {demande['contrat']['formule']} · contrat "
                f"{demande['contrat']['statut']} · {anciennete} jours d'ancienneté · "
                f"{demande.get('historique', {}).get('sinistres_12_mois', 0)} sinistre(s) sur "
                "12 mois</div></div>",
                unsafe_allow_html=True,
            )

            st.markdown("**Pièces jointes**")
            for piece in demande.get("pieces", []):
                somme = f" — {piece['montant']:.0f} €" if piece.get("montant") else ""
                st.caption(
                    f"{'✓' if piece.get('lisible') else '✗'} {piece['type']}"
                    f" ({'lisible' if piece.get('lisible') else 'illisible'}){somme}"
                )
            depots = demande.get("espace_assure", {}).get("depots", [])
            if depots:
                st.markdown("**En attente dans l'espace assuré**")
                for piece in depots:
                    st.caption(f"{'✓' if piece.get('lisible') else '✗'} {piece['type']}")

            attendu = socle.attendu_de(scenario, reference)
            if attendu:
                st.subheader("Ce que la recette attend")
                verdict = socle.conforme(fiche, attendu)
                (st.success if verdict else st.error)(
                    "Conforme à l'attendu" if verdict else "Écart avec l'attendu"
                )
                st.json(attendu, expanded=False)

    with vues_tech[1]:
        st.subheader("La mémoire partagée, zone par zone")
        st.caption(
            "Quatre zones aux règles d'accès distinctes. Seul le répartiteur y écrit ; les "
            "agents reçoivent leurs entrées et rendent un résultat."
        )
        reference = st.radio("Demande", references, horizontal=True, key="dossier")
        fiche = par_reference[reference]
        demande = demandes_par_reference[reference]

        z1, z2 = st.columns(2)
        with z1:
            st.markdown("##### 1 · La demande d'origine — _lecture seule_")
            st.markdown(
                "<div class='bloc'><span class='etiq'>champs présents</span><br>"
                + " · ".join(f"<code>{c}</code>" for c in demande)
                + "</div>",
                unsafe_allow_html=True,
            )

            st.markdown("##### 2 · Les parties publiées — _une section, un auteur_")
            auteurs: dict[str, str] = {}
            for etape in fiche["trace"]:
                for section in etape["ecrit"]:
                    auteurs[section] = etape["agent"]
            for section in ("eligibilite", "pieces", "estimation", "avis_fraude", "issue"):
                if section in auteurs:
                    st.markdown(
                        f"<div class='zone'><code>{section}</code> — écrite par "
                        f"{pastille(auteurs[section])}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    raison = (
                        "aucun contrôle requis, ou avis non obtenu"
                        if section == "avis_fraude"
                        else "non atteinte sur ce parcours"
                    )
                    st.markdown(
                        f"<div class='zone zone-vide'><code>{section}</code> — non publiée "
                        f"<em>({raison})</em></div>",
                        unsafe_allow_html=True,
                    )

        with z2:
            st.markdown("##### 3 · La zone de travail — _ne sort jamais dans la fiche_")
            st.markdown(
                "<div class='bloc' style='color:#55656E'>"
                "Compteurs, constat d'indisponibilité, journal de routage du répartiteur. Elle "
                "est invisible d'ici, et c'est la démonstration : la fiche ne porte que les dix "
                "champs du contrat d'intégration.</div>",
                unsafe_allow_html=True,
            )
            st.markdown("##### 4 · Le journal de bord — _ajout seul_")
            st.markdown(
                etapes_detaillees(fiche["trace"], len(fiche["trace"])), unsafe_allow_html=True
            )
            st.markdown("##### Les champs de la fiche")
            st.code(" · ".join(fiche), language=None)

    with vues_tech[2]:
        st.subheader("Ce qui entre, et ce qui sort")
        st.caption(
            "La démonstration la plus directe de `EX-3` : la demande porte le nom, l'IBAN et le "
            "texte écrit par l'assuré ; la charge envoyée au partenaire n'en porte aucun."
        )
        reference = st.radio("Demande", references, horizontal=True, key="a2a")
        demande = demandes_par_reference[reference]
        fiche = par_reference[reference]
        appels = [
            a for a in resultat["journal_partenaire"] if a.get("reference") in (reference, None)
        ]

        entree, sortie = st.columns(2)
        with entree:
            st.markdown("##### Ce que le système détient")
            personnelles = {
                **demande["assure"],
                "numero_contrat": demande["contrat"]["numero"],
                "description": demande["sinistre"]["description"],
            }
            st.markdown(
                "<div class='bloc'>"
                + "".join(
                    "<div style='display:flex;gap:9px;font-size:0.86rem;margin-bottom:2px'>"
                    f"<code style='min-width:9.5rem'>{cle}</code>"
                    f"<span style='color:#55656E'>{valeur}</span></div>"
                    for cle, valeur in personnelles.items()
                )
                + "</div>",
                unsafe_allow_html=True,
            )
            st.caption("Données fictives, issues des scénarios de recette du brief.")

        with sortie:
            st.markdown("##### Ce qui part chez le partenaire")
            if not appels:
                st.caption("_Aucun appel : cette demande ne présente aucun indicateur de risque._")
            else:
                envoye = module_charge.construire(demande)
                st.markdown(
                    "<div class='bloc'>"
                    + "".join(
                        "<div style='display:flex;gap:9px;font-size:0.86rem;margin-bottom:2px'>"
                        f"<code style='min-width:11rem'>{cle}</code>"
                        f"<span style='color:#0E7C7B'>{valeur}</span></div>"
                        for cle, valeur in envoye.items()
                    )
                    + "</div>",
                    unsafe_allow_html=True,
                )
                corps = json.dumps(envoye, ensure_ascii=False)
                fuites = [
                    str(v) for v in personnelles.values() if isinstance(v, str) and v in corps
                ]
                if fuites:
                    st.error(f"Données personnelles dans la charge : {fuites}")
                else:
                    st.success("Aucune des données de gauche ne figure dans la charge.")
                st.caption(
                    f"Le département `{envoye['departement']}` est **dérivé** du code postal "
                    f"`{demande['assure']['code_postal']}`, jamais recopié."
                )

        if appels:
            st.divider()
            st.subheader("Les quatre niveaux de validation")
            appel = appels[0]
            avis = fiche.get("avis_fraude")
            franchis = 4 if avis else (1 if appel.get("conforme") else 0)
            niveaux = (
                ("1 · transport", "reçue dans le délai, sans erreur signalée"),
                ("2 · lisibilité", "JSON lisible, enveloppe JSON-RPC conforme"),
                ("3 · forme", "exactement les six champs attendus, bons types"),
                ("4 · sens", "score dans ses bornes, niveau cohérent, dossier apparié"),
            )
            for rang, (titre, detail) in enumerate(niveaux, start=1):
                if avis or rang <= franchis:
                    couleur, marque = "#0E7C7B", "✓"
                elif rang == franchis + 1:
                    couleur, marque = "#C8432B", "✗"
                else:
                    couleur, marque = "#C2CBD0", "·"
                st.markdown(
                    f"<div style='display:flex;gap:11px;align-items:center;border-left:3px solid "
                    f"{couleur};padding:4px 0 4px 11px;margin-bottom:4px;color:{couleur}'>"
                    f"<span style='width:0.9rem'>{marque}</span>"
                    f"<b style='min-width:8rem'>{titre}</b>"
                    f"<span style='color:#55656E;font-size:0.88rem'>{detail}</span></div>",
                    unsafe_allow_html=True,
                )
            if avis:
                st.success(f"Avis obtenu — niveau **{avis['niveau']}**, score **{avis['score']}**.")
            else:
                st.warning(
                    "Avis **non obtenu**. Un seul verdict sort de la passerelle : rien du "
                    "contenu rejeté ne la traverse, pas même dans le motif."
                )

    with vues_tech[3]:
        st.subheader("Quand le partenaire ne répond pas")
        st.caption(
            "Le mode dégradé est **une propriété d'une demande, pas un état du système**. "
            "C'est le piège principal de la section 9."
        )

        g_deg, d_deg = st.columns([1.2, 1])
        with g_deg:
            st.markdown(
                "<div class='bloc'><div class='etiq'>trois causes, un seul traitement</div>"
                "<div style='margin-top:6px;font-size:0.9rem;color:#55656E'>"
                "Pas de réponse dans le délai · erreur du service · réponse non conforme"
                "</div></div>"
                "<div style='text-align:center;color:#A8B3B9;margin:7px 0'>▼</div>"
                "<div style='border:2px solid #B7791F;border-radius:10px;padding:9px;"
                "text-align:center;background:#FBF1DE;color:#B7791F;font-weight:600'>"
                "Le contrôle anti-fraude était-il requis ?</div>"
                "<div style='display:flex;gap:13px;margin-top:9px'>"
                "<div style='flex:1;border:1.5px solid #D5DEE2;border-radius:9px;"
                "padding:9px 11px;background:#F8FAFB'><b style='color:#55656E'>Non</b><br>"
                "<span style='font-size:0.86rem;color:#55656E'>La demande suit son cours. "
                "<b>Elle n'est pas marquée.</b></span></div>"
                "<div style='flex:1;border:1.5px solid #B7791F;border-radius:9px;"
                "padding:9px 11px;background:#FBF1DE'><b style='color:#B7791F'>Oui</b><br>"
                "<span style='font-size:0.86rem;color:#7A4A3E'>Mode dégradé — le "
                "<b>montant estimé</b> tranche.</span></div></div>"
                "<div style='margin-top:9px;display:flex;gap:13px'>"
                "<div style='flex:1;border:1.5px solid #0E7C7B;border-radius:9px;"
                "padding:9px 11px;background:#E3F1F0'><b style='color:#0E7C7B'>≤ 1 500 €</b><br>"
                "<span style='font-size:0.86rem;color:#0E7C7B'>Continue sans avis, marquée pour "
                "contrôle a posteriori.</span></div>"
                "<div style='flex:1;border:1.5px solid #C8432B;border-radius:9px;"
                "padding:9px 11px;background:#FBE9E5'><b style='color:#C8432B'>&gt; 1 500 €</b>"
                "<br><span style='font-size:0.86rem;color:#7A4A3E'>Escalade cellule "
                "anti-fraude, marquée aussi.</span></div></div>",
                unsafe_allow_html=True,
            )
        with d_deg:
            st.markdown("##### Ce qui n'arrive jamais")
            st.markdown(
                "- **Aucune demande n'attend** au-delà de 3 secondes\n"
                "- **Aucune relance** — ni après un délai, ni après une erreur, ni après une "
                "réponse écartée\n"
                "- **Aucune valeur** d'une réponse écartée ne ressort\n"
                "- **Aucun blocage** : le mode dégradé préserve le service"
            )

        st.divider()
        st.markdown("##### À l'épreuve d'un lot")
        if st.button("Rejouer PAN-01 avec le partenaire en panne", use_container_width=True):
            scenario_panne = par_identifiant["PAN-01"]
            resultat_panne = socle.traiter(
                scenario_panne["demandes"], partenaire(), {"mode": "panne"}
            )
            st.markdown(
                tableau(
                    [
                        {
                            "référence": f["reference"],
                            "déclaré": f"{d['sinistre']['montant_declare']:.0f} €",
                            "issue": f.get("decision") or f.get("file"),
                            "remboursé": (
                                f"{f['montant_rembourse']:.2f} €"
                                if f.get("montant_rembourse") is not None
                                else "—"
                            ),
                            "mode dégradé": "⚑ oui" if f.get("mode_degrade") else "non",
                        }
                        for d, f in zip(
                            scenario_panne["demandes"], resultat_panne["fiches"], strict=True
                        )
                    ]
                )
            )
            marquees = sum(1 for f in resultat_panne["fiches"] if f.get("mode_degrade"))
            total = len(resultat_panne["fiches"])
            if marquees == 2 and total == 5:
                st.success(
                    f"**{total - marquees} fiches sur {total} ne portent aucune marque.** Le "
                    "partenaire est pourtant hors service pour tout le lot : ces demandes ne "
                    "requéraient aucun contrôle."
                )
            else:
                st.error(f"{marquees} marquée(s) sur {total} — attendu 2 sur 5.")

    with vues_tech[4]:
        st.subheader("Un agent, un rôle, une section")
        cartes = st.columns(5)
        roles = {
            "eligibilite": ("eligibilite", "Le contrat couvre-t-il ce sinistre ? Ne chiffre rien."),
            "pieces": ("pieces", "Présence et lisibilité. Demande les compléments."),
            "estimation": ("estimation", "Justifié, retenu, estimé. Franchise **puis** plafond."),
            "antifraude": ("avis_fraude", "Calcule les indicateurs, consulte. N'émet aucun avis."),
            "decision": ("issue", "Applique l'ordre des règles. Seul à conclure."),
        }
        for colonne, (agent, (section, role)) in zip(cartes, roles.items(), strict=True):
            with colonne:
                st.markdown(pastille(agent), unsafe_allow_html=True)
                st.caption(role)
                st.markdown(f"→ `{section}`")

        st.divider()
        g, d = st.columns(2)
        with g:
            st.markdown("##### Le plan du répartiteur")
            st.caption("Une table, pas une conversation. Aucun agent ne la connaît.")
            st.markdown(
                tableau(
                    [
                        {
                            "après l'étape": LIBELLE_AGENT.get(etape, etape),
                            "verdict rendu": verdict,
                            "étape suivante": LIBELLE_AGENT.get(suivante, suivante or "— fin"),
                        }
                        for (etape, verdict), suivante in module_plan.PLAN.items()
                    ]
                )
            )
        with d:
            st.markdown("##### Les frontières, vérifiées sur le code")
            for regle in (
                "Aucun agent n'importe un autre agent",
                "Aucun agent n'importe l'orchestration",
                "Aucun agent n'importe le dossier",
                "Seul l'agent anti-fraude parle au partenaire",
                "Seule la passerelle lit l'adresse et le jeton",
                "`regles/` n'importe rien du paquet",
                "Seul le répartiteur écrit dans le dossier",
                "Aucun jeton en dur",
            ):
                st.markdown(f"✓ {regle}")
            st.caption("23 vérifications dans `tests/chantier_1/test_architecture.py`.")

            st.markdown("##### Les noms d'arrêt")
            for nom in (
                module_bornes.PIECES_TENTATIVES_EPUISEES,
                module_bornes.PIECES_SANS_DEPOT_RESTANT,
                module_bornes.ETAPES_MAX_ATTEINT,
                module_bornes.DUREE_MAX_ATTEINTE,
                module_bornes.CLOTURE_MANQUANTE,
                module_bornes.AGENT_DEFAILLANT,
            ):
                st.caption(f"`{nom}` → {module_bornes.motif(nom)}")

    with vues_tech[5]:
        st.subheader("Les fiches du lot, dans l'ordre des demandes")
        st.markdown(
            tableau(
                [
                    {
                        "référence": f["reference"],
                        "issue": f["issue"],
                        "décision / file": f.get("decision") or f.get("file") or "—",
                        "remboursé": (
                            f"{f['montant_rembourse']:.2f} €"
                            if f.get("montant_rembourse") is not None
                            else "—"
                        ),
                        "mode dégradé": "oui" if f.get("mode_degrade") else "non",
                        "arrêt": (f.get("arret") or {}).get("borne", "—"),
                        "étapes": len(f["trace"]),
                        "conforme": (
                            "✓"
                            if socle.conforme(f, socle.attendu_de(scenario, f["reference"]))
                            else "✗"
                        ),
                    }
                    for f in fiches
                ]
            )
        )

        st.subheader("Les mesures, agent par agent")
        st.markdown(
            tableau(
                [
                    {
                        "agent": LIBELLE_AGENT.get(agent, agent),
                        "appels": valeurs["appels"],
                        "échecs": valeurs["echecs"],
                        "latence moyenne": f"{valeurs['latence_ms']:.2f} ms",
                        "appels externes": valeurs["appels_externes"],
                    }
                    for agent, valeurs in resultat["metriques"].items()
                ]
            )
        )

        journal_partenaire = resultat["journal_partenaire"]
        st.subheader("Ce que le partenaire a reçu")
        if not journal_partenaire:
            st.caption("_Aucun appel sur ce lot._")
        else:
            st.markdown(
                tableau(
                    [
                        {
                            "dossier": appel.get("reference") or "— illisible —",
                            "champs transmis": len(appel.get("champs") or []),
                            "requête conforme": "✓" if appel.get("conforme") else "✗",
                            "HTTP": appel.get("statut_http"),
                            "doublon": "oui" if appel.get("doublon") else "non",
                        }
                        for appel in journal_partenaire
                    ]
                )
            )

    with vues_tech[6]:
        st.subheader("Le journal d'exploitation")
        st.caption(
            "La trace d'une fiche dit ce qui s'est passé pour **cette** demande. Le journal dit "
            "ce qui s'est passé **dans le système** : c'est ce qu'on lit le lendemain."
        )
        evenements = resultat["journal"]

        indicateurs = st.columns(4)
        indicateurs[0].metric("Événements", len(evenements))
        indicateurs[1].metric("Alertes", sum(1 for e in evenements if e["niveau"] == "warning"))
        indicateurs[2].metric(
            "Étapes journalisées", sum(1 for e in evenements if e["evenement"] == "etape")
        )
        indicateurs[3].metric(
            "Étapes en échec", sum(1 for e in evenements if e.get("statut") == "echec")
        )

        st.error(
            "**Aucune donnée personnelle n'entre ici.** Un journal survit à la demande, se "
            "copie, s'exporte. La référence du dossier est le seul identifiant retenu, et un "
            "garde-fou refuse les autres."
        )

        g_obs, d_obs = st.columns([3, 2])
        with g_obs:
            st.markdown("##### Où le temps passe")
            reference = st.radio("Demande", references, horizontal=True, key="obs")

            declaration_saisie = st.session_state.get("declaration")
            bout_en_bout = st.toggle(
                "Inclure la prise de déclaration (hors système)",
                value=False,
                disabled=declaration_saisie is None,
                help=None
                if declaration_saisie is not None
                else "Passez d'abord par l'espace assuré pour qu'une déclaration soit saisie.",
            )

            if bout_en_bout and declaration_saisie is not None:
                etapes_parcours = parcours.trace_complete(
                    par_reference[reference], declaration_saisie
                )
                st.markdown(chronologie_parcours(etapes_parcours), unsafe_allow_html=True)

                part = parcours.part_du_modele(etapes_parcours)
                repartition_temps = parcours.repartition(etapes_parcours)
                if part > 0.5:
                    st.error(
                        f"**{part * 100:.0f} % du temps total est consommé par l'appel au "
                        "modèle**, et il se passe **hors du système**. La plateforme, elle, a "
                        f"traité la demande en {repartition_temps.get('kaldera', 0):.0f} ms. "
                        "C'est le premier cercle de `D31` au chronomètre : un modèle dans le chemin "
                        "de décision ne "
                        "ferait pas seulement perdre le déterminisme, il mangerait presque tout "
                        "l'engagement de service."
                    )
                else:
                    st.caption(
                        "L'extraction par règles ne pèse rien : c'est le modèle, et lui seul, "
                        "qui change l'ordre de grandeur."
                    )
            else:
                st.markdown(chronologie(par_reference[reference]["trace"]), unsafe_allow_html=True)

            st.markdown("##### Les mesures par agent")
            couleurs = {
                LIBELLE_AGENT.get(a, a): COULEUR_AGENT.get(a, "#55656E")
                for a in resultat["metriques"]
            }
            st.markdown(
                barres(
                    {
                        LIBELLE_AGENT.get(a, a): v["appels"]
                        for a, v in resultat["metriques"].items()
                    },
                    couleurs=couleurs,
                ),
                unsafe_allow_html=True,
            )
        with d_obs:
            st.markdown("##### Les quatre signaux")
            signaux = resultat.get("signaux", {})
            st.markdown(
                jauge(signaux.get("part_mode_degrade", 0.0), "Part en mode dégradé"),
                unsafe_allow_html=True,
            )
            st.markdown(
                jauge(
                    signaux.get("part_rejet_de_forme", 0.0),
                    "Part rejetée pour la forme",
                    alerte_au_dessus=0.0,
                ),
                unsafe_allow_html=True,
            )
            st.markdown(
                jauge(
                    signaux.get("part_garde_fou", 0.0),
                    "Part arrêtée par un garde-fou",
                    alerte_au_dessus=0.0,
                ),
                unsafe_allow_html=True,
            )
            if signaux.get("part_rejet_de_forme", 0.0) > 0:
                st.error(
                    "**Une réponse a été rejetée pour sa forme.** Ce signal dit que **notre "
                    "lecture du contrat dérive**, pas que le partenaire est tombé."
                )
            st.markdown("##### Répartition des événements")
            st.markdown(barres(repartition_evenements(evenements)), unsafe_allow_html=True)

        st.divider()
        seulement_alertes = st.toggle("N'afficher que les alertes", value=False)
        for evenement in evenements:
            if seulement_alertes and evenement["niveau"] != "warning":
                continue
            couleur = "#C8432B" if evenement["niveau"] == "warning" else "#55656E"
            details = {
                cle: valeur
                for cle, valeur in evenement.items()
                if cle not in ("horodatage", "niveau", "evenement", "reference")
            }
            st.markdown(
                f"<div style='display:flex;gap:11px;align-items:baseline;border-left:3px solid "
                f"{couleur};padding:3px 0 3px 11px;margin-bottom:3px;font-size:0.86rem'>"
                f"<code style='color:#A8B3B9'>{evenement['horodatage'][11:]}</code>"
                f"<b style='color:{couleur};min-width:13rem'>{evenement['evenement']}</b>"
                f"<code style='color:#0E7C7B'>{evenement.get('reference', '')}</code>"
                "<span style='color:#55656E'>"
                + " · ".join(f"{c} = {v}" for c, v in details.items())
                + "</span></div>",
                unsafe_allow_html=True,
            )

    with vues_tech[7]:
        st.subheader("Où les modèles entrent, et pourquoi là")
        st.caption(
            "Le brief autorise d'intégrer des modèles « à différents endroits ». La question "
            "n'est pas combien, mais selon quelle règle — sinon chaque ajout se justifie seul "
            "et l'ensemble ne se défend plus."
        )

        st.markdown("##### La règle")
        st.markdown(
            "<div style='border:2px solid #1B2A33;border-radius:10px;padding:13px;"
            "background:#1B2A33;color:#fff;text-align:center;font-size:1.05rem'>"
            "Un modèle peut <b>informer un humain</b>, jamais <b>décider à sa place</b> "
            "dans le temps contraint.</div>",
            unsafe_allow_html=True,
        )

        joignable = llm.configure()
        st.markdown(
            f"**Modèle employé** : `{llm.nom_du_modele()}` — "
            + (
                "joignable sur ce poste."
                if joignable
                else "**aucun accès configuré ici** : les cinq usages se replient, aucun ne bloque."
            )
        )
        st.caption(
            "Un seul modèle sert les cinq usages. Ni l'adresse ni la clé n'apparaissent dans "
            "cette interface, ni dans les journaux."
        )

        st.markdown("##### Les trois cercles")
        cercles = st.columns(3)
        definitions = (
            (
                "Jamais",
                "#C8432B",
                "#FBE9E5",
                "Le chemin de décision synchrone",
                "2,5 à 35,5 s mesurés contre 10 s d'engagement. Et le déterminisme que les "
                "tests d'acceptance exigent.",
            ),
            (
                "Oui, asynchrone",
                "#B7791F",
                "#FBF1DE",
                "Après la décision, sur ce qui est clos",
                "Le budget de temps ne s'applique plus : la fiche est partie, l'assuré est servi.",
            ),
            (
                "Oui, hors système",
                "#0E7C7B",
                "#E3F1F0",
                "Au service d'un humain qui décide",
                "Aucune contrainte de service, puisque rien du service rendu n'en dépend.",
            ),
        )
        for colonne, (titre, bord, fond, quoi, pourquoi) in zip(cercles, definitions, strict=True):
            with colonne:
                st.markdown(
                    f"<div style='border:2px solid {bord};background:{fond};border-radius:10px;"
                    f"padding:11px 13px;height:100%'>"
                    f"<div style='font-weight:600;color:{bord};font-size:1.05rem'>{titre}</div>"
                    f"<div style='margin:5px 0;font-size:0.9rem'><b>{quoi}</b></div>"
                    f"<div style='font-size:0.86rem;color:#55656E'>{pourquoi}</div></div>",
                    unsafe_allow_html=True,
                )

        st.divider()
        st.markdown("##### Les cinq usages, et où la règle les place")
        st.caption(
            "Latences mesurées le 9 octobre 2026 sur `Kimi-K2.6` : **10 appels par usage**, "
            "cinq dossiers distincts répétés deux fois. **40 appels sur 40 exploitables.**"
        )
        st.markdown(
            tableau(
                [
                    {
                        "usage": "Prise de déclaration",
                        "cercle": "hors système",
                        "où": "amont, chez le courtier",
                        "latence mesurée": "médiane 5,1 s · max 12,7 s",
                        "ce qu'il décide": "rien — l'opérateur relit avant de déposer",
                    },
                    {
                        "usage": "Revue de fond",
                        "cercle": "asynchrone",
                        "où": "après la décision",
                        "latence mesurée": "médiane 9,0 s · max 12,8 s",
                        "ce qu'il décide": "rien — il signale, un humain tranche",
                    },
                    {
                        "usage": "Cohérence des pièces",
                        "cercle": "asynchrone",
                        "où": "dans la revue",
                        "latence mesurée": "incluse dans la revue",
                        "ce qu'il décide": "rien — consultatif, hors du contrôle des pièces",
                    },
                    {
                        "usage": "Synthèse de dossier",
                        "cercle": "hors système",
                        "où": "espace gestionnaire",
                        "latence mesurée": "médiane 12,5 s · max 23,1 s",
                        "ce qu'il décide": "rien — s'ajoute à la fiche, ne la remplace pas",
                    },
                    {
                        "usage": "Aide à la décision",
                        "cercle": "hors système",
                        "où": "espace gestionnaire",
                        "latence mesurée": "médiane 18,4 s · max 35,5 s",
                        "ce qu'il décide": "rien — rien n'est pré-sélectionné",
                    },
                ]
            )
        )

        st.divider()
        g_mod, d_mod = st.columns(2)
        with g_mod:
            st.markdown("##### Ce que la mesure a tranché")
            st.markdown(
                "Un appel au modèle, pour **une phrase de 25 mots** :\n\n"
                "- latence **2,5 à 35,5 s** selon l'usage, sur 40 appels mesurés\n"
                "- jusqu'à **2,6** entre deux appels sur le même dossier\n"
                "- **1 243 jetons** consommés pour ~35 jetons utiles\n"
                "- **0 formulation identique** sur 5 appels\n\n"
                "Les cinq agents du chemin de décision traitent une demande complète en "
                "**0,04 ms**. Le rapport est de 1 à 100 000."
            )
            st.caption("C'est ce qui exclut le premier cercle — pas une préférence d'architecte.")
        with d_mod:
            st.markdown("##### Les garde-fous, testés")
            st.markdown(
                "- Aucun agent, ni l'orchestration, n'importe la revue — un test d'imports "
                "le garantit\n"
                "- Aucun avis ne modifie une fiche\n"
                "- Un modèle qui tombe rend « indisponible », jamais une erreur\n"
                "- Toute remarque évoquant la **fraude** est écartée et comptée *(specs §2)*\n"
                "- Le **récit de l'assuré** ne part chez aucun modèle — tranché par le métier, "
                "et aucune variable d'environnement ne rouvre la porte\n"
                "- Les tests qui appellent un modèle réel sont **écartés de la suite** : elle "
                "reste reproductible\n"
                "- **Un seul endroit sait construire un client de modèle** : `kaldera.llm`, "
                "qu'aucun agent n'importe. Les trois copies précédentes avaient déjà "
                "divergé sur les jetons et le délai *(`AJ-10`)*"
            )

        st.info(
            "**Ce qu'on n'a pas fait, et pourquoi.** La rédaction des motifs reste un gabarit "
            "déterministe *(`D9`)* : un courrier qui engage l'assureur ne doit pas varier d'un "
            "assuré à l'autre. Et le contrôle des pièces ne consomme pas l'avis de cohérence, "
            "parce que le métier n'a pas défini le critère — poser la question sans en "
            "dépendre permet de la mesurer en attendant."
        )

    with vues_tech[8]:
        st.subheader("Ce que cette démonstration ne montre pas")
        st.caption("Une liste honnête de ce qui manque vaut mieux qu'une liste flatteuse.")

        g, d = st.columns(2)
        with g:
            st.markdown("##### Dettes assumées")
            st.markdown(
                "- **`D11`** — toute escalade sur borne va au gestionnaire : règle ajoutée sans "
                "qu'aucun texte la fonde\n"
                "- **Le critère de « cohérence »** des pièces, réduit au tableau de la "
                "section 5 faute de définition\n"
                "- **`mypy` ne tourne plus** : extension native bloquée sur ce poste\n"
                "- **Le traitement est séquentiel** : tenu par `S12`, mais la conformité repose "
                "sur l'abandon à 3 s"
            )
        with d:
            st.markdown("##### Les modèles de langage")
            st.markdown(
                "- **Cinq usages**, placés par une seule règle *(`D31`)* — voir l'onglet "
                "**Les modèles**\n"
                "- **Aucun dans le chemin de décision synchrone** : 2,5 à 35,5 s mesurés "
                "contre 10 s d'engagement\n"
                "- Ils n'ont **jamais le dernier mot** : ils informent, un humain tranche\n"
                "- Non déterministes : leurs tests sont écartés de la suite, `make modele` "
                "les lance à part"
            )

        st.divider()
        etat = st.columns(4)
        etat[0].metric("Tests reproductibles", f"{TESTS_REPRODUCTIBLES}")
        etat[1].metric("Couverture", COUVERTURE, help=f"mesurée le {COUVERTURE_MESUREE_LE}")
        etat[2].metric("Suite d'acceptance", f"{TESTS_ACCEPTANCE} / {TESTS_ACCEPTANCE}")
        etat[3].metric("Mutations détectées", f"{MUTATIONS_DETECTEES} / {MUTATIONS_DETECTEES}")
        st.caption(
            "`make test` · `make mutations` · `make modele` · `make journaux` — et `make aide` "
            "les liste toutes."
        )
