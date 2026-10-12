"""Le parcours de bout en bout : ce qui précède la plateforme, et ce qu'elle fait.

La trace que rend `kaldera` ne porte que les étapes de ses agents, et c'est juste : la prise de
déclaration chez le courtier n'est pas du ressort de la plateforme, et y inscrire une étape
qu'elle n'a pas exécutée serait un mensonge dans une pièce qui sert de preuve.

Mais s'arrêter là laisse invisible ce qui compte le plus : **l'ordre de grandeur**. Les cinq
agents traitent une demande complète en une fraction de milliseconde ; l'extraction assistée par
un modèle met plusieurs secondes. Tant qu'on ne les voit pas sur la même ligne, on ne mesure pas
ce que le premier cercle de `D31` écarte du chemin de décision.

Ce module compose donc les deux, **en gardant la frontière lisible** : chaque étape dit si elle
appartient au système ou non.
"""

from __future__ import annotations

from typing import Any

#: Le libellé d'un acteur, et s'il appartient au système automatisé.
ACTEURS: dict[str, dict[str, Any]] = {
    "courtier": {
        "libelle": "Cabinet de courtage",
        "dans_le_systeme": False,
        "couleur": "#B7791F",
    },
    "kaldera": {
        "libelle": "Plateforme Kaldera",
        "dans_le_systeme": True,
        "couleur": "#0E7C7B",
    },
}


def etape_saisie(declaration: Any) -> dict[str, Any]:
    """L'étape de prise de déclaration, telle qu'elle s'est réellement passée.

    ``declaration`` est une ``saisie.Declaration`` ; le type n'est pas importé pour que ce
    module reste utilisable sans le paquet du client externe.
    """
    assiste = declaration.extracteur == "modèle"
    return {
        "acteur": "courtier",
        "agent": "saisie",
        "action": "extraire la déclaration",
        "outil": "modèle de langage" if assiste else "règles déterministes",
        "duree_ms": round(declaration.duree_ms, 2),
        "ecrit": [
            c
            for c in ("type_sinistre", "date_survenance", "montant_declare")
            if getattr(declaration, c) is not None
        ],
        "statut": "echec" if declaration.incertitudes else "ok",
        "verdict": "complète" if declaration.complete else "incomplète",
        "appels_externes": 1 if assiste else 0,
    }


def trace_complete(fiche: dict[str, Any], declaration: Any | None = None) -> list[dict[str, Any]]:
    """Le parcours entier : la saisie d'abord s'il y en a eu une, puis le traitement."""
    etapes: list[dict[str, Any]] = []
    if declaration is not None:
        etapes.append(etape_saisie(declaration))
    for etape in fiche.get("trace", []):
        etapes.append({**etape, "acteur": "kaldera", "outil": "calcul"})
    return etapes


def repartition(etapes: list[dict[str, Any]]) -> dict[str, float]:
    """Où le temps est passé, par acteur. C'est le chiffre qui fait la démonstration."""
    par_acteur: dict[str, float] = {}
    for etape in etapes:
        acteur = etape.get("acteur", "kaldera")
        par_acteur[acteur] = par_acteur.get(acteur, 0.0) + etape["duree_ms"]
    return par_acteur


def part_du_modele(etapes: list[dict[str, Any]]) -> float:
    """La part du temps total consommée par un appel à un modèle. Entre 0 et 1."""
    total = sum(e["duree_ms"] for e in etapes) or 1.0
    modele = sum(e["duree_ms"] for e in etapes if e.get("outil") == "modèle de langage")
    return modele / total
