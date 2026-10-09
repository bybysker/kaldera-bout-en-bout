"""Le relecteur : un sixième agent qui relit une décision **après** qu'elle est prise.

---

**Pourquoi après, et pas pendant.** Mesuré sur ce poste, un appel au modèle met de 3,5 à
10,6 secondes, avec un facteur 2,6 entre deux appels sur la même question. L'engagement de
service est de **10 secondes par demande** : un appel sur cinq le dépasserait à lui seul. Les
cinq agents du chemin de décision, eux, traitent une demande complète en **0,04 ms**.

Un modèle dans le chemin de décision ne ferait donc pas seulement perdre le déterminisme — il
consommerait presque tout le budget, et rendrait la tenue de l'engagement dépendante d'un
service tiers.

Placé **après**, il ne coûte rien au service rendu : la fiche est close, l'assuré est servi, et
le relecteur travaille sur ce qui est déjà décidé.

**Ce qu'il peut faire, et ce qu'il ne peut pas.**

| Il peut | Il ne peut pas |
| --- | --- |
| Signaler une décision qui mérite un œil humain | Changer une décision |
| Dire qu'un motif sera mal compris | Rédiger le motif |
| Repérer un élément que les règles n'ont pas vu | Émettre un avis de fraude *(specs §2)* |

**Trois garanties structurelles**, et elles sont testées :

1. Aucun agent, ni l'orchestration, ni le répartiteur n'importe ce module. La décision ne peut
   pas en dépendre, même par accident.
2. Son résultat ne modifie jamais une fiche — il s'ajoute à côté.
3. Quand le modèle ne répond pas, la revue est *non disponible*. Jamais un échec.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from .. import llm
from . import charge as module_charge

#: Au-delà, on cesse d'attendre. Généreux à dessein : nous ne sommes plus dans le budget des 10 s.
DELAI_MAX_S = 30.0

#: Un modèle de raisonnement consomme des jetons avant de répondre — mesuré : ~1 240 pour une
#: phrase. Trop peu, et la réponse revient vide sans qu'aucune erreur ne soit levée.
JETONS_MAX = 4000

NIVEAUX = ("conforme", "a_revoir", "non_disponible")

#: La « cohérence » des pièces — la troisième frontière ambiguë du chantier 1.
#:
#: La spécification emploie le mot sans jamais le définir. Nous avions réduit le contrôle au
#: tableau des pièces exigées *(décision D3)*, en signalant que le mot restait plus large.
#:
#: Le modèle répond ici à la question large — **mais son avis n'entre dans aucune décision**.
#: Il éclaire un gestionnaire, il ne contrôle rien. C'est ce qui permet de poser la question
#: sans attendre que le métier ait défini le critère : tant qu'aucune décision n'en dépend,
#: aucun assuré ne subit un jugement que personne ne saurait expliquer.
#:
#: Sans le récit de l'assuré — fermé par défaut — le modèle ne juge que la cohérence
#: **structurelle** : des types de pièces et des montants au regard de la nature du sinistre.
COHERENCES = ("plausible", "douteuse", "indeterminable")

CONSIGNE = """Tu relis une décision d'assurance habitation DÉJÀ PRISE par un système automatisé.
Tu ne la changes pas : tu dis si elle mérite l'attention d'un gestionnaire.

Réponds UNIQUEMENT par un objet JSON, sans texte autour, avec exactement ces clés :

  "verdict"     : "conforme" ou "a_revoir"
  "motif_clair" : true si un assuré non spécialiste comprendrait le motif, false sinon
  "points"      : liste de 0 à 3 phrases courtes, ce qui mérite un regard — vide si rien
  "coherence_pieces" : "plausible", "douteuse" ou "indeterminable"

Règles :
- Tu ne te prononces JAMAIS sur une suspicion de fraude : ce n'est pas ton rôle.
- "a_revoir" seulement si quelque chose cloche vraiment : une incohérence entre les
  montants, un motif qui ne correspond pas à la décision, un élément du dossier qui
  contredit l'issue. Le doute ordinaire n'est pas un motif.
- Si tout est cohérent, réponds "conforme" avec une liste vide.

Sur "coherence_pieces" : les pièces fournies sont-elles plausibles pour ce type de sinistre
et ce montant ? Une facture de plomberie pour un bris de glace ne l'est pas ; un montant sans
rapport avec la nature du dommage non plus. Réponds "indeterminable" si tu n'as pas de quoi
juger — c'est une réponse valable, et préférable à une supposition.

**Cet avis est consultatif** : il n'entre dans aucune décision, il éclaire un gestionnaire."""


class Relecteur:
    """Relit une décision close. Ne décide de rien."""

    def __init__(self, fabrique: Any = None) -> None:
        self._fabrique = fabrique

    def disponible(self) -> bool:
        return self._fabrique is not None or llm.configure()

    def relire(self, demande: dict[str, Any], fiche: dict[str, Any]) -> dict[str, Any]:
        """Rend toujours la même forme, quoi qu'il arrive."""
        debut = time.perf_counter()
        modele = self._modele()
        if modele is None:
            return _avis(
                "non_disponible",
                cause="aucun modèle configuré",
                duree_ms=(time.perf_counter() - debut) * 1000,
            )

        dossier = module_charge.construire(demande, fiche)
        try:
            brut = modele.invoke(
                [
                    ("system", CONSIGNE),
                    ("human", json.dumps(dossier, ensure_ascii=False, indent=2)),
                ]
            )
            donnees = _lire_json(getattr(brut, "content", str(brut)))
        except Exception as exc:  # noqa: BLE001 — une revue qui tombe ne casse rien
            return _avis(
                "non_disponible",
                cause=f"modèle en échec ({type(exc).__name__})",
                duree_ms=(time.perf_counter() - debut) * 1000,
            )

        return _relire_reponse(donnees, (time.perf_counter() - debut) * 1000)

    def _modele(self) -> Any:
        if self._fabrique is not None:
            return self._fabrique()
        return llm.fabriquer(jetons_max=JETONS_MAX, delai_s=DELAI_MAX_S)


def _lire_json(texte: str) -> dict[str, Any]:
    texte = (texte or "").strip()
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut == -1 or fin == -1:
        raise ValueError("aucun objet JSON dans la réponse")
    return json.loads(texte[debut : fin + 1])


#: Mots qui trahiraient un avis de fraude — interdit par les spécifications §2.
MOTS_INTERDITS = re.compile(r"\bfraud|escroqu|falsif|mensong", re.IGNORECASE)


def _relire_reponse(donnees: dict[str, Any], duree_ms: float) -> dict[str, Any]:
    """Relit ce que le modèle a rendu. Ce qui n'est pas conforme n'est pas retenu.

    Même principe qu'avec le partenaire : une réponse hors contrat est écartée, pas corrigée.
    """
    verdict = donnees.get("verdict")
    if verdict not in ("conforme", "a_revoir"):
        return _avis("non_disponible", cause="verdict hors nomenclature", duree_ms=duree_ms)

    points = donnees.get("points")
    if not isinstance(points, list):
        points = []
    retenus = [
        p.strip()
        for p in points
        if isinstance(p, str) and p.strip() and not MOTS_INTERDITS.search(p)
    ][:3]

    ecartes = len([p for p in points if isinstance(p, str) and MOTS_INTERDITS.search(p)])

    coherence = donnees.get("coherence_pieces")
    if coherence not in COHERENCES:
        coherence = "indeterminable"

    return {
        "verdict": verdict,
        "motif_clair": bool(donnees.get("motif_clair", True)),
        "coherence_pieces": coherence,
        "points": retenus,
        "cause": "",
        "duree_ms": round(duree_ms, 2),
        # « l'avis de fraude est émis par le partenaire, jamais en interne » (specs §2)
        "points_ecartes": ecartes,
    }


def _avis(verdict: str, cause: str = "", duree_ms: float = 0.0) -> dict[str, Any]:
    return {
        "verdict": verdict,
        "motif_clair": True,
        "coherence_pieces": "indeterminable",
        "points": [],
        "cause": cause,
        "duree_ms": round(duree_ms, 2),
        "points_ecartes": 0,
    }


def relire(demande: dict[str, Any], fiche: dict[str, Any], fabrique: Any = None) -> dict[str, Any]:
    """Relit une décision close. **Ne jamais appeler depuis le chemin de décision.**"""
    return Relecteur(fabrique).relire(demande, fiche)
