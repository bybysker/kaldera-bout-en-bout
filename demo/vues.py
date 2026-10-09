"""Rendu des vues de la démonstration — des fonctions pures, sans Streamlit.

Les séparer de l'application permet de les éprouver par des tests : un schéma qui ment sur le
parcours d'une demande serait pire que pas de schéma du tout.
"""

from __future__ import annotations

from datetime import date
from typing import Any

COULEUR_AGENT = {
    "eligibilite": "#0E7C7B",
    "pieces": "#2F6F9F",
    "estimation": "#6B5B95",
    "antifraude": "#B7791F",
    "decision": "#1B2A33",
}

LIBELLE_AGENT = {
    "eligibilite": "Éligibilité",
    "pieces": "Pièces",
    "estimation": "Estimation",
    "antifraude": "Anti-fraude",
    "decision": "Décision",
}


def attendu_de(scenario: dict[str, Any], reference: str) -> dict[str, Any]:
    for attendu in scenario["attendu"]:
        if attendu["reference"] == reference:
            return attendu
    return {}


def conforme(fiche: dict[str, Any], attendu: dict[str, Any]) -> bool:
    for champ in ("issue", "decision", "file"):
        if champ in attendu and fiche.get(champ) != attendu[champ]:
            return False
    if "mode_degrade" in attendu and bool(fiche.get("mode_degrade")) != attendu["mode_degrade"]:
        return False
    if "montant_rembourse" in attendu:
        obtenu, prevu = fiche.get("montant_rembourse"), attendu["montant_rembourse"]
        if prevu is None:
            if obtenu is not None:
                return False
        elif obtenu is None or abs(obtenu - prevu) >= 0.01:
            return False
    if attendu.get("arret") and not (fiche.get("arret") or {}).get("borne"):
        return False
    return True


def pastille(agent: str) -> str:
    couleur = COULEUR_AGENT.get(agent, "#55656E")
    libelle = LIBELLE_AGENT.get(agent, agent)
    return (
        f"<span style='background:{couleur};color:#fff;padding:2px 9px;border-radius:11px;"
        f"font-size:0.82rem;white-space:nowrap'>{libelle}</span>"
    )


def anciennete(demande: dict[str, Any]) -> int:
    return (
        date.fromisoformat(demande["sinistre"]["date_survenance"])
        - date.fromisoformat(demande["contrat"]["date_souscription"])
    ).days


# ========================================================= le schéma animé du flux

#: Les agents que le schéma sait représenter. Un agent absent d'ici disparaîtrait
#: silencieusement de la démonstration : un test le vérifie.
ETAPES_SCHEMA = ("eligibilite", "pieces", "estimation", "antifraude", "decision")


def bandeau_repartiteur(courante: str | None, rang: int, total: int) -> str:
    """Le répartiteur, au-dessus de l'équipe : il délègue, il n'écrit pas.

    Il n'a pas sa place parmi les agents — aucune section ne lui est imputable. Mais l'effacer
    du schéma donnerait à croire que les agents s'enchaînent d'eux-mêmes, alors que c'est lui
    qui tient le plan.
    """
    action = (
        f"confie l'étape « {LIBELLE_AGENT.get(courante, courante)} »"
        if courante
        else "ouvre le dossier"
    )
    return (
        "<div style='border:1.6px solid #1B2A33;border-radius:9px;background:#1B2A33;"
        "color:#fff;padding:7px 13px;margin-bottom:9px;display:flex;align-items:center;gap:11px'>"
        "<span style='font-weight:600'>Répartiteur</span>"
        f"<span style='opacity:.8;font-size:0.88rem'>{action}</span>"
        f"<span style='margin-left:auto;opacity:.65;font-size:0.8rem'>étape {rang} / {total}</span>"
        "</div>"
        "<div style='text-align:center;color:#A8B3B9;font-size:1.1rem;margin:-4px 0 3px'>▼</div>"
    )


def encart_partenaire(trace: list[dict[str, Any]], jusqu_a: int) -> str:
    """Le détour vers le partenaire, matérialisé — avec le temps d'attente réellement mesuré."""
    consultations = [etape for etape in trace[:jusqu_a] if etape["action"] == "antifraude"]
    if not consultations:
        return ""
    etape = consultations[-1]
    obtenu = bool(etape["ecrit"])
    attente = etape["duree_ms"]
    if not etape.get("appels_externes"):
        return (
            "<div style='margin-top:9px;text-align:right;color:#A8B3B9;font-size:0.82rem'>"
            "aucun indicateur de risque — le partenaire n'a pas été consulté</div>"
        )
    couleur = "#0E7C7B" if obtenu else "#C8432B"
    verdict = "avis obtenu" if obtenu else "avis non obtenu — mode dégradé"
    return (
        "<div style='margin-top:9px;display:flex;justify-content:flex-end;align-items:center;"
        "gap:9px'>"
        "<span style='color:#A8B3B9;font-size:0.82rem'>détour hors du système</span>"
        f"<span style='color:{couleur}'>⇄</span>"
        f"<span style='border:1.5px dashed {couleur};color:{couleur};border-radius:9px;"
        f"padding:5px 12px;font-size:0.85rem'>Partenaire anti-fraude — {verdict} "
        f"<span style='opacity:.75'>· {attente:.0f} ms d'attente</span></span></div>"
    )


#: La règle de la section 10 qu'un motif trahit. Les motifs sont des gabarits déterministes.
REGLES_SECTION_10 = (
    ("1", "Demande non éligible", "refusée", "Demande non éligible"),
    ("2", "Pièces manquantes", "escalade gestionnaire", "Pièces manquantes"),
    ("3", "Montant estimé nul", "refusée", "Dommage inférieur"),
    ("4", "Contrôle anti-fraude", "selon l'avis, ou mode dégradé", "Contrôle renforcé"),
    ("5", "Seuil de délégation dépassé", "escalade gestionnaire", "Seuil de délégation"),
    ("6", "Sinon", "acceptée", "Remboursement accordé"),
)

_MOTIFS_REGLE_4 = ("Contrôle renforcé", "Suspicion de fraude", "Contrôle anti-fraude manuel")


def regle_appliquee(fiche: dict[str, Any]) -> str | None:
    """Quelle règle de la section 10 a fixé l'issue — déduite du motif, qui est un gabarit."""
    if fiche.get("arret"):
        return "borne"
    motif = fiche.get("motif") or ""
    if motif.startswith("Demande non éligible"):
        return "1"
    if motif.startswith("Pièces manquantes"):
        return "2"
    if motif.startswith("Dommage inférieur"):
        return "3"
    if any(motif.startswith(debut) for debut in _MOTIFS_REGLE_4):
        return "4"
    if motif.startswith("Seuil de délégation"):
        return "5"
    if motif.startswith("Remboursement accordé"):
        return "6"
    return None


def arbre_decision(fiche: dict[str, Any], visible: bool) -> str:
    """Les six règles en cascade ; celle qui a tranché s'allume, les suivantes s'éteignent."""
    retenue = regle_appliquee(fiche) if visible else None
    atteinte = False
    lignes = []

    for numero, intitule, consequence, _ in REGLES_SECTION_10:
        if retenue == numero:
            fond, bord, texte, poids = "#E3F1F0", "#0E7C7B", "#0E7C7B", "600"
            atteinte = True
        elif retenue is None or atteinte:
            fond, bord, texte, poids = "#FFFFFF", "#E6ECEF", "#C2CBD0", "400"
        else:
            fond, bord, texte, poids = "#F8FAFB", "#D5DEE2", "#8A969D", "400"
        marque = "◆" if retenue == numero else "◇"
        lignes.append(
            f"<div style='display:flex;gap:9px;align-items:center;border:1px solid {bord};"
            f"background:{fond};color:{texte};border-radius:8px;padding:6px 11px;margin-bottom:5px;"
            f"font-weight:{poids};transition:all .25s'>"
            f"<span style='width:0.9rem'>{marque}</span>"
            f"<span style='width:1.2rem;opacity:.7'>{numero}</span>"
            f"<span style='flex:1'>{intitule}</span>"
            f"<span style='font-size:0.84rem;opacity:.8'>{consequence}</span></div>"
        )

    if retenue == "borne":
        lignes.insert(
            0,
            "<div style='display:flex;gap:9px;align-items:center;border:1px solid #B7791F;"
            "background:#FBF1DE;color:#B7791F;border-radius:8px;padding:6px 11px;margin-bottom:5px;"
            "font-weight:600'><span style='width:0.9rem'>⛔</span>"
            f"<span style='flex:1'>Sortie ordonnée — borne « {fiche['arret']['borne']} »</span>"
            "<span style='font-size:0.84rem'>escalade gestionnaire</span></div>",
        )

    entete = (
        "<div style='font-size:0.72rem;letter-spacing:.06em;text-transform:uppercase;"
        "color:#55656E;margin-bottom:7px'>l'ordre des règles · section 10 — "
        "la première qui s'applique fixe l'issue</div>"
    )
    return f"<div>{entete}{''.join(lignes)}</div>"


def etapes_detaillees(trace: list[dict[str, Any]], jusqu_a: int) -> str:
    """La liste des étapes réalisées, telle que le journal de bord les porte."""
    lignes = []
    for rang, etape in enumerate(trace[:jusqu_a], start=1):
        ecrit = (
            " · ".join(f"<code>{s}</code>" for s in etape["ecrit"])
            if etape["ecrit"]
            else "<span style='color:#A8B3B9'>n'a rien publié</span>"
        )
        marque = " ⚠" if etape.get("statut") == "echec" else ""
        lignes.append(
            f"<div style='display:flex;gap:11px;align-items:center;margin-bottom:6px'>"
            f"<span style='color:#A8B3B9;width:1.4rem'>{rang}</span>"
            f"{pastille(etape['agent'])}"
            f"<span style='color:#55656E'>{etape['action']}{marque}</span>"
            f"<span style='margin-left:auto'>{ecrit}"
            f" <span style='color:#A8B3B9'>· {etape['duree_ms']:.1f} ms</span></span></div>"
        )
    return "".join(lignes)


def vue_animee(trace: list[dict[str, Any]], fiche: dict[str, Any], jusqu_a: int) -> str:
    """Le bloc complet rejoué à un instant donné : schéma, étapes, arbre de décision."""
    close = jusqu_a >= len(trace)
    return (
        arbre_orchestration(trace, jusqu_a)
        + "<div style='height:13px'></div>"
        + etapes_detaillees(trace, jusqu_a)
        + "<div style='height:9px'></div>"
        + arbre_decision(fiche, visible=close)
    )


def tableau(lignes: list[dict[str, Any]]) -> str:
    """Un tableau Markdown, rendu nativement par Streamlit.

    `st.dataframe` et `st.table` passent par pandas, dont les extensions natives sont bloquées
    par la stratégie de contrôle d'application du poste. Un tableau Markdown n'a aucune
    dépendance et se projette aussi bien.
    """
    if not lignes:
        return "_Aucune donnée._"
    colonnes = list(lignes[0])
    entete = "| " + " | ".join(colonnes) + " |"
    separateur = "| " + " | ".join("---" for _ in colonnes) + " |"
    corps = [
        "| " + " | ".join(str(ligne.get(colonne, "")) for colonne in colonnes) + " |"
        for ligne in lignes
    ]
    return "\n".join([entete, separateur, *corps])


# ========================================================= observabilité visuelle


def chronologie(trace: list[dict[str, Any]], largeur_min: float = 1.5) -> str:
    """Les étapes d'une demande en barres proportionnelles à leur durée.

    Sans ce dessin, une demande qui passe 320 ms à attendre un partenaire et 0,04 ms à décider
    ressemble à une demande où tout prend le même temps. C'est précisément ce qu'il faut voir.
    """
    if not trace:
        return "<p style='color:#8A969D'>Aucune étape.</p>"

    total = sum(e["duree_ms"] for e in trace) or 1.0
    lignes = []
    for rang, etape in enumerate(trace, start=1):
        part = etape["duree_ms"] / total * 100
        couleur = COULEUR_AGENT.get(etape["agent"], "#55656E")
        echec = etape.get("statut") == "echec"
        lignes.append(
            "<div style='display:flex;gap:9px;align-items:center;margin-bottom:4px'>"
            f"<span style='color:#A8B3B9;width:1.2rem;font-size:0.8rem'>{rang}</span>"
            f"<span style='width:6.5rem;font-size:0.84rem;color:{couleur}'>"
            f"{LIBELLE_AGENT.get(etape['agent'], etape['agent'])}</span>"
            "<span style='flex:1;background:#F0F4F5;border-radius:4px;height:17px;position:relative'>"
            f"<span style='display:block;width:{max(part, largeur_min):.2f}%;height:100%;"
            f"background:{'repeating-linear-gradient(45deg,' + couleur + ',' + couleur + ' 4px,#fff 4px,#fff 7px)' if echec else couleur};"
            "border-radius:4px'></span></span>"
            f"<span style='width:5.5rem;text-align:right;font-size:0.8rem;color:#55656E'>"
            f"{etape['duree_ms']:.2f} ms</span>"
            f"<span style='width:3rem;text-align:right;font-size:0.78rem;color:#A8B3B9'>"
            f"{part:.0f} %</span></div>"
        )
    reseau = sum(e["duree_ms"] for e in trace if e.get("appels_externes"))
    calcul = total - reseau
    lignes.append(
        f"<div style='margin-top:7px;text-align:right;font-size:0.82rem;color:#55656E'>"
        f"total <b>{total:.2f} ms</b> · les hachures signalent une étape en échec</div>"
    )
    lignes.append(
        "<div style='margin-top:9px;border-left:3px solid #D5DEE2;padding:5px 0 5px 11px;"
        "font-size:0.82rem;color:#55656E'>"
        f"<b>{calcul:.2f} ms de calcul</b> pour {len(trace)} étapes"
        + (
            f", et <b>{reseau:.0f} ms d'attente réseau</b> chez le partenaire."
            if reseau
            else ", et aucune attente réseau sur ce parcours."
        )
        + " Ces durées sont celles d'agents <b>déterministes</b> : des comparaisons chiffrées, "
        "sans appel à un modèle. Un appel à un modèle de langage se compte en <b>secondes</b> — "
        "voir l'espace assuré.</div>"
    )
    return "".join(lignes)


def barres(
    valeurs: dict[str, float], unite: str = "", couleurs: dict[str, str] | None = None
) -> str:
    """Un histogramme horizontal, sans dépendance — pandas est bloqué sur ce poste."""
    if not valeurs:
        return "<p style='color:#8A969D'>Aucune mesure.</p>"
    maximum = max(valeurs.values()) or 1.0
    couleurs = couleurs or {}
    lignes = []
    for libelle, valeur in valeurs.items():
        couleur = couleurs.get(libelle, "#0E7C7B")
        lignes.append(
            "<div style='display:flex;gap:9px;align-items:center;margin-bottom:4px'>"
            f"<span style='width:7rem;font-size:0.84rem;color:#55656E'>{libelle}</span>"
            "<span style='flex:1;background:#F0F4F5;border-radius:4px;height:15px'>"
            f"<span style='display:block;width:{valeur / maximum * 100:.1f}%;height:100%;"
            f"background:{couleur};border-radius:4px'></span></span>"
            f"<span style='width:5.5rem;text-align:right;font-size:0.82rem'>"
            f"{valeur:g}{unite}</span></div>"
        )
    return "".join(lignes)


def jauge(part: float, libelle: str, alerte_au_dessus: float = 0.0) -> str:
    """Une part de 0 à 1. Au-delà du seuil d'alerte, elle change de couleur."""
    pourcent = max(0.0, min(1.0, part)) * 100
    en_alerte = part > alerte_au_dessus
    couleur = "#C8432B" if en_alerte else "#0E7C7B"
    return (
        "<div style='margin-bottom:11px'>"
        "<div style='display:flex;justify-content:space-between;font-size:0.84rem;"
        f"color:#55656E;margin-bottom:3px'><span>{libelle}</span>"
        f"<b style='color:{couleur}'>{pourcent:.0f} %</b></div>"
        "<div style='background:#F0F4F5;border-radius:4px;height:9px'>"
        f"<div style='width:{pourcent:.1f}%;height:100%;background:{couleur};"
        "border-radius:4px'></div></div></div>"
    )


def repartition_evenements(evenements: list[dict[str, Any]]) -> dict[str, float]:
    """Combien de fois chaque type d'événement est apparu."""
    compte: dict[str, float] = {}
    for evenement in evenements:
        nom = evenement.get("evenement", "?")
        compte[nom] = compte.get(nom, 0) + 1
    return dict(sorted(compte.items(), key=lambda paire: -paire[1]))


# =================================================== l'arbre du plan conditionnel

#: Les étapes, dans l'ordre où le plan les propose, et les verdicts qui en partent.
#: Transcrit de `kaldera.orchestration.plan` — la source reste le code, ceci n'est que la
#: disposition à l'écran.
BRANCHES: tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...] = (
    (
        "eligibilite",
        (
            ("non_recevable", "decision", "non recevable"),
            ("recevable", "pieces", "recevable"),
        ),
    ),
    (
        "pieces",
        (
            ("sans_depot", "decision", "aucun dépôt — règle métier"),
            ("epuise", "decision", "dépôts épuisés — borne"),
            ("reprise", "pieces", "reprise, compteur +1"),
            ("completes", "estimation", "complètes et lisibles"),
        ),
    ),
    (
        "estimation",
        (
            ("montant_nul", "decision", "montant nul"),
            ("montant_positif", "antifraude", "montant > 0"),
        ),
    ),
    ("antifraude", (("termine", "decision", "dans tous les cas"),)),
)


def arbre_orchestration(trace: list[dict[str, Any]], jusqu_a: int) -> str:
    """Le plan conditionnel, avec la branche réellement empruntée allumée.

    La ligne droite des cinq agents mentait : elle laissait croire que le parcours est toujours
    le même, alors que trois étapes sur quatre peuvent court-circuiter vers la décision, et que
    le contrôle des pièces peut reprendre. Montrer **ce qui ne s'est pas passé** est ce qui
    donne son sens à ce qui s'est passé.
    """
    vues = trace[:jusqu_a]
    courante = vues[-1]["action"] if vues else None
    empruntees = {(e["action"], e.get("verdict", "")) for e in vues}
    atteintes = {e["action"] for e in vues}
    passages = {etape: sum(1 for e in vues if e["action"] == etape) for etape, _ in BRANCHES}

    rangs = []
    for etape, sorties in BRANCHES:
        rangs.append(_rang(etape, sorties, courante, atteintes, empruntees, passages[etape]))
    rangs.append(_decision(courante, atteintes))

    return (
        "<div style='border:1px solid #D5DEE2;border-radius:12px;padding:15px;background:#fff'>"
        + bandeau_repartiteur(courante, len(vues), len(trace))
        + "".join(rangs)
        + _legende()
        + "</div>"
    )


def _rang(
    etape: str,
    sorties: tuple[tuple[str, str, str], ...],
    courante: str | None,
    atteintes: set[str],
    empruntees: set[tuple[str, str]],
    passages: int,
) -> str:
    """Une étape et les verdicts qui en partent."""
    active = etape == courante
    faite = etape in atteintes and not active
    couleur = COULEUR_AGENT[etape]

    if active:
        boite = f"background:{couleur};color:#fff;border-color:{couleur};box-shadow:0 0 0 4px {couleur}33"
    elif faite:
        boite = f"background:{couleur}1A;color:{couleur};border-color:{couleur}"
    else:
        boite = "background:#fff;color:#C2CBD0;border-color:#E6ECEF"

    repetition = (
        f"<span style='font-size:0.72rem;opacity:.85;margin-left:5px'>×{passages}</span>"
        if passages > 1
        else ""
    )

    fleches = []
    for verdict, cible, libelle in sorties:
        prise = (etape, verdict) in empruntees
        if prise:
            style = f"color:{couleur};border-color:{couleur};background:{couleur}14;font-weight:600"
            marque = "━▶"
        else:
            style = "color:#C2CBD0;border-color:#EEF2F4;background:#fff"
            marque = "─▶"
        vers = LIBELLE_AGENT.get(cible, cible)
        boucle = " ↺" if cible == etape else ""
        fleches.append(
            f"<div style='border:1px solid;border-radius:7px;padding:3px 9px;{style};"
            f"font-size:0.78rem;white-space:nowrap'>{marque} {libelle}{boucle} "
            f"<span style='opacity:.7'>· {vers}</span></div>"
        )

    return (
        "<div style='display:flex;gap:13px;align-items:center;margin-bottom:7px'>"
        f"<div style='flex:0 0 8.5rem;border:2px solid;border-radius:10px;padding:8px 11px;"
        f"text-align:center;font-weight:600;font-size:0.9rem;{boite}'>"
        f"{LIBELLE_AGENT[etape]}{repetition}</div>"
        "<div style='flex:1;display:flex;gap:6px;flex-wrap:wrap'>" + "".join(fleches) + "</div>"
        "</div>"
    )


def _decision(courante: str | None, atteintes: set[str]) -> str:
    """La décision : toutes les branches y mènent, c'est ce qui fait tenir `EX-1`."""
    active = courante == "decision"
    close = "decision" in atteintes
    if active or close:
        style = "background:#1B2A33;color:#fff;border-color:#1B2A33"
    else:
        style = "background:#fff;color:#C2CBD0;border-color:#E6ECEF"
    return (
        "<div style='text-align:center;color:#A8B3B9;font-size:0.9rem;margin:2px 0 4px'>"
        "▼ toutes les branches mènent ici ▼</div>"
        f"<div style='border:2px solid;border-radius:10px;padding:9px;text-align:center;"
        f"font-weight:600;{style}'>Décision"
        "<span style='font-weight:400;opacity:.75;font-size:0.82rem'> — écrit l'issue, "
        "le motif, la file</span></div>"
    )


def _legende() -> str:
    return (
        "<div style='margin-top:11px;display:flex;gap:17px;font-size:0.76rem;color:#8A969D'>"
        "<span><b style='color:#0E7C7B'>━▶</b> branche empruntée</span>"
        "<span>─▶ branche possible, non prise</span>"
        "<span>↺ retour sur la même étape</span></div>"
    )


def chronologie_parcours(etapes: list[dict[str, Any]]) -> str:
    """Le parcours de bout en bout, saisie comprise — avec la frontière du système visible.

    La trace de la plateforme ne porte pas la saisie, et c'est juste : elle ne l'a pas exécutée.
    Mais les mettre sur la même ligne est la seule façon de voir ce que `D31` écarte du chemin
    de décision — un appel
    à un modèle pèse plusieurs secondes là où cinq agents pèsent une fraction de milliseconde.
    """
    from demo.parcours import ACTEURS

    if not etapes:
        return "<p style='color:#8A969D'>Aucune étape.</p>"

    total = sum(e["duree_ms"] for e in etapes) or 1.0
    lignes = []
    acteur_precedent = None

    for rang, etape in enumerate(etapes, start=1):
        acteur = etape.get("acteur", "kaldera")
        reglage = ACTEURS[acteur]
        if acteur != acteur_precedent:
            bordure = "" if acteur_precedent is None else "border-top:1px dashed #D5DEE2;"
            lignes.append(
                f"<div style='{bordure}margin:9px 0 5px;padding-top:7px;font-size:0.76rem;"
                f"letter-spacing:.06em;text-transform:uppercase;color:{reglage['couleur']}'>"
                f"{reglage['libelle']}"
                + ("" if reglage["dans_le_systeme"] else " — hors du système")
                + "</div>"
            )
            acteur_precedent = acteur

        part = etape["duree_ms"] / total * 100
        couleur = (
            COULEUR_AGENT.get(etape["agent"], reglage["couleur"])
            if reglage["dans_le_systeme"]
            else reglage["couleur"]
        )
        libelle = (
            LIBELLE_AGENT.get(etape["agent"], etape["agent"])
            if reglage["dans_le_systeme"]
            else "Saisie"
        )
        duree = (
            f"{etape['duree_ms'] / 1000:.2f} s"
            if etape["duree_ms"] >= 1000
            else f"{etape['duree_ms']:.2f} ms"
        )
        outil = etape.get("outil", "")
        lignes.append(
            "<div style='display:flex;gap:9px;align-items:center;margin-bottom:4px'>"
            f"<span style='color:#A8B3B9;width:1.2rem;font-size:0.8rem'>{rang}</span>"
            f"<span style='width:6.5rem;font-size:0.84rem;color:{couleur}'>{libelle}</span>"
            f"<span style='width:9rem;font-size:0.78rem;color:#A8B3B9'>{outil}</span>"
            "<span style='flex:1;background:#F0F4F5;border-radius:4px;height:17px'>"
            f"<span style='display:block;width:{max(part, 0.6):.2f}%;height:100%;"
            f"background:{couleur};border-radius:4px'></span></span>"
            f"<span style='width:6rem;text-align:right;font-size:0.8rem;color:#55656E'>"
            f"{duree}</span>"
            f"<span style='width:3.5rem;text-align:right;font-size:0.78rem;color:#A8B3B9'>"
            f"{part:.1f} %</span></div>"
        )

    return "".join(lignes)
