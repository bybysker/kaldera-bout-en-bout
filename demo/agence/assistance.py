"""Deux aides au gestionnaire, qui ne décident rien.

Troisième cercle de la doctrine d'intégration : **hors du système, au service d'un humain qui
décide**. Aucune contrainte de service ne s'y applique — ni les 10 secondes, ni le
déterminisme des tests d'acceptance — puisque rien du service rendu n'en dépend.

| Aide | Ce qu'elle fait | Ce qu'elle ne fait pas |
| --- | --- | --- |
| **Synthèse** | Trois lignes là où la fiche en fait quarante | Rien retirer du dossier : elle s'ajoute |
| **Suggestion** | Propose une suite et la justifie | Décider : le gestionnaire tranche et signe |

La règle qui les autorise toutes deux : *un modèle peut informer un humain, jamais décider à sa
place dans le temps contraint*. Ici l'humain lit, puis choisit — et il peut choisir l'inverse.

**La suggestion n'est jamais pré-sélectionnée dans l'interface.** Un bouton déjà coché est une
décision prise par la machine, même si un humain la valide ensuite d'un clic.
"""

from __future__ import annotations

import json
from typing import Any

from kaldera import llm

#: Les suites qu'un gestionnaire peut décider — reprises de `gestionnaire.SUITES`.
SUITES_POSSIBLES = ("accepter", "refuser", "complement", "cellule_fraude")

JETONS_MAX = 4000

#: Généreux : ces aides sont hors du budget des dix secondes.
DELAI_S = 60.0

CONSIGNE_SYNTHESE = """Tu résumes un dossier d'assurance habitation pour le gestionnaire qui va
le reprendre. Il ne l'a jamais vu.

Trois phrases au plus, dans cet ordre :
1. de quoi il s'agit (sinistre, montant, contrat),
2. pourquoi il arrive sur son bureau,
3. le point qui mérite son attention en premier.

Ton factuel. Pas de salutation, pas de conclusion, pas de recommandation — un autre s'en charge.
Tu ne te prononces jamais sur une suspicion de fraude."""

CONSIGNE_SUGGESTION = """Tu conseilles un gestionnaire d'assurance habitation sur un dossier
escaladé. Il décidera lui-même : tu l'éclaires.

Réponds UNIQUEMENT par un objet JSON, sans texte autour :

  "suite"      : "accepter", "refuser", "complement" ou "cellule_fraude"
  "confiance"  : "forte", "moyenne" ou "faible"
  "parce_que"  : une phrase, 30 mots au plus
  "contre"     : une phrase disant ce qui pourrait justifier l'inverse — jamais vide

Règles :
- "contre" est obligatoire. Un conseil qui ne dit pas ce qui lui résiste n'est pas un conseil.
- Tu ne te prononces jamais sur une suspicion de fraude : ce n'est pas ton rôle.
- "faible" est une réponse honnête quand le dossier ne permet pas de trancher."""


def _modele(fabrique: Any = None) -> Any:
    """Le client de modèle, construit par la fabrique unique du paquet `kaldera`.

    L'espace gestionnaire est une interface de Kaldera, pas un tiers : il emprunte la même
    fabrique que la revue plutôt que d'en réapprendre les subtilités.
    """
    if fabrique is not None:
        return fabrique()
    return llm.fabriquer(jetons_max=JETONS_MAX, delai_s=DELAI_S)


def _dossier(fiche: dict[str, Any], demande: dict[str, Any]) -> dict[str, Any]:
    """Ce que les aides voient. Même minimisation que la revue : aucune identité.

    Un gestionnaire a besoin du nom de l'assuré ; le modèle qui l'aide, non.
    """
    from kaldera.revue import charge

    return charge.construire(demande, fiche)


def synthese(
    fiche: dict[str, Any], demande: dict[str, Any], fabrique: Any = None
) -> dict[str, Any]:
    """Trois lignes pour un gestionnaire qui découvre le dossier."""
    modele = _modele(fabrique)
    if modele is None:
        return {"texte": "", "disponible": False, "cause": "aucun modèle configuré"}
    try:
        brut = modele.invoke(
            [
                ("system", CONSIGNE_SYNTHESE),
                ("human", json.dumps(_dossier(fiche, demande), ensure_ascii=False, indent=2)),
            ]
        )
        texte = (getattr(brut, "content", "") or "").strip()
    except Exception as exc:  # noqa: BLE001
        return {
            "texte": "",
            "disponible": False,
            "cause": f"modèle en échec ({type(exc).__name__})",
        }

    if not texte:
        return {"texte": "", "disponible": False, "cause": "réponse vide"}
    return {"texte": texte, "disponible": True, "cause": ""}


def suggestion(
    fiche: dict[str, Any], demande: dict[str, Any], fabrique: Any = None
) -> dict[str, Any]:
    """Une suite proposée, sa raison, et **ce qui pourrait la contredire**.

    Le champ « contre » n'est pas une précaution de style : un conseil qui ne dit pas ce qui lui
    résiste se fait suivre sans être pesé, et c'est exactement ce qu'on veut éviter quand la
    décision engage un assuré.
    """
    modele = _modele(fabrique)
    if modele is None:
        return _sans_suggestion("aucun modèle configuré")
    try:
        brut = modele.invoke(
            [
                ("system", CONSIGNE_SUGGESTION),
                ("human", json.dumps(_dossier(fiche, demande), ensure_ascii=False, indent=2)),
            ]
        )
        donnees = _lire_json(getattr(brut, "content", "") or "")
    except Exception as exc:  # noqa: BLE001
        return _sans_suggestion(f"modèle en échec ({type(exc).__name__})")

    suite = donnees.get("suite")
    if suite not in SUITES_POSSIBLES:
        return _sans_suggestion("suite hors nomenclature")

    contre = str(donnees.get("contre") or "").strip()
    if not contre:
        return _sans_suggestion("aucun contre-argument : conseil écarté")

    confiance = donnees.get("confiance")
    return {
        "suite": suite,
        "confiance": confiance if confiance in ("forte", "moyenne", "faible") else "faible",
        "parce_que": str(donnees.get("parce_que") or "").strip(),
        "contre": contre,
        "disponible": True,
        "cause": "",
    }


def _sans_suggestion(cause: str) -> dict[str, Any]:
    return {
        "suite": None,
        "confiance": "faible",
        "parce_que": "",
        "contre": "",
        "disponible": False,
        "cause": cause,
    }


def _lire_json(texte: str) -> dict[str, Any]:
    texte = texte.strip()
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut == -1 or fin == -1:
        raise ValueError("aucun objet JSON dans la réponse")
    return json.loads(texte[debut : fin + 1])
