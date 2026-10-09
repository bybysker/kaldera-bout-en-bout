"""La prise de déclaration : transformer un récit en champs structurés.

C'est le seul endroit de tout le système où un modèle de langage a sa place, et la raison en
est simple : **un assuré qui appelle son courtier raconte, il ne remplit pas un formulaire.**

> *« Bonjour, j'ai eu une fuite sous l'évier samedi dernier, le parquet du couloir a gondolé.
> J'ai la facture du plombier, 1 400 euros. J'ai aussi pris des photos. »*

Transformer cela en `type`, `date_survenance`, `montant_declare` et liste de pièces est une tâche
de langage. Aucune règle chiffrée n'y est décidée : la demande produite repart ensuite par la
traduction déterministe de ``courtier.py``, puis par la porte publique de Kaldera.

---

**Pourquoi c'est compatible avec `D25`.** La décision disait : aucun modèle **dans le chemin de
décision d'une demande**. Ce module est hors du paquet `kaldera`, hors de la recette, et son
résultat est relu par un humain avant d'être déposé. Le déterminisme du système n'est pas touché.

**Deux extracteurs, et le déterministe reste le défaut.**

| | Quand | Ce qu'il vaut |
| --- | --- | --- |
| `ExtractionParRegles` | toujours | Mots-clés et expressions régulières. Suffit sur des récits simples, échoue sur les tournures indirectes |
| `ExtractionAssistee` | si un modèle est configuré | Meilleur sur le langage réel, mais non déterministe — d'où la relecture avant dépôt |

Les deux sont mesurés par le même jeu de récits : voir `tests/chantier_2/test_saisie.py`. Un
extracteur qu'on ne sait pas noter n'est pas un extracteur, c'est un pari.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Protocol

TYPES_SINISTRE = ("degat_des_eaux", "incendie", "bris_de_glace", "vol")
TYPES_PIECE = ("facture", "photo", "depot_plainte")

#: Mots qui désignent chaque nature de sinistre dans un récit ordinaire.
INDICES_SINISTRE: dict[str, tuple[str, ...]] = {
    "degat_des_eaux": ("fuite", "eau", "inondation", "infiltration", "dégât des eaux", "plomb"),
    "incendie": ("incendie", "feu", "brûlé", "brule", "flamme", "fumée", "fumee"),
    "bris_de_glace": ("vitre", "fenêtre", "fenetre", "baie", "verre", "glace", "carreau"),
    "vol": ("vol", "cambriolage", "effraction", "dérobé", "derobe", "volé", "vole"),
}

INDICES_PIECE: dict[str, tuple[str, ...]] = {
    "facture": ("facture", "devis", "reçu", "recu", "note"),
    "photo": ("photo", "cliché", "cliche", "image"),
    "depot_plainte": ("plainte", "commissariat", "gendarmerie", "main courante"),
}

JOURS_NOMMES = (
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
)

JOURS = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
}


@dataclass
class Declaration:
    """Ce qu'on a compris d'un récit — et ce qu'on n'a pas compris."""

    type_sinistre: str | None = None
    date_survenance: str | None = None
    montant_declare: float | None = None
    pieces: list[str] = field(default_factory=list)
    recit: str = ""
    extracteur: str = ""
    incertitudes: list[str] = field(default_factory=list)
    #: Temps réellement passé à extraire. Le seul endroit du système où il se compte en
    #: secondes et non en microsecondes — voir la note en tête de module.
    duree_ms: float = 0.0

    @property
    def complete(self) -> bool:
        return not self.incertitudes

    def en_dict(self) -> dict[str, Any]:
        return {
            "type_sinistre": self.type_sinistre,
            "date_survenance": self.date_survenance,
            "montant_declare": self.montant_declare,
            "pieces": list(self.pieces),
            "extracteur": self.extracteur,
            "incertitudes": list(self.incertitudes),
            "duree_ms": round(self.duree_ms, 2),
        }


class Extracteur(Protocol):
    nom: str

    def extraire(self, recit: str, aujourdhui: date) -> Declaration: ...


# ------------------------------------------------------------- par règles


class ExtractionParRegles:
    """Mots-clés et expressions régulières. Toujours disponible, toujours le même résultat."""

    nom = "règles"

    def extraire(self, recit: str, aujourdhui: date | None = None) -> Declaration:
        aujourdhui = aujourdhui or date.today()
        minuscules = recit.lower()
        declaration = Declaration(recit=recit, extracteur=self.nom)

        declaration.type_sinistre = self._type_sinistre(minuscules)
        declaration.date_survenance = self._date(minuscules, aujourdhui)
        declaration.montant_declare = self._montant(minuscules)
        declaration.pieces = self._pieces(minuscules)

        for champ, valeur in (
            ("type_sinistre", declaration.type_sinistre),
            ("date_survenance", declaration.date_survenance),
            ("montant_declare", declaration.montant_declare),
        ):
            if valeur is None:
                declaration.incertitudes.append(champ)
        return declaration

    @staticmethod
    def _type_sinistre(recit: str) -> str | None:
        trouves = [
            nature
            for nature, indices in INDICES_SINISTRE.items()
            if any(indice in recit for indice in indices)
        ]
        # Un récit qui évoque deux natures est ambigu : mieux vaut ne rien conclure.
        return trouves[0] if len(trouves) == 1 else None

    @staticmethod
    def _montant(recit: str) -> float | None:
        motif = r"(\d[\d\s  ]{0,9}(?:[.,]\d{1,2})?)\s*(?:€|euros?|eur\b)"
        trouves = re.findall(motif, recit)
        if not trouves:
            return None
        nettoye = trouves[0].replace(" ", "").replace(" ", "").replace(" ", "")
        try:
            return float(nettoye.replace(",", "."))
        except ValueError:
            return None

    @staticmethod
    def _date(recit: str, aujourdhui: date) -> str | None:
        explicite = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", recit)
        if explicite:
            return explicite.group(0)

        francaise = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", recit)
        if francaise:
            jour, mois, annee = (int(g) for g in francaise.groups())
            try:
                return date(annee, mois, jour).isoformat()
            except ValueError:
                return None

        if "hier" in recit:
            return (aujourdhui - timedelta(days=1)).isoformat()
        if "avant-hier" in recit:
            return (aujourdhui - timedelta(days=2)).isoformat()
        if "aujourd'hui" in recit or "ce matin" in recit:
            return aujourdhui.isoformat()

        for nom, indice in JOURS.items():
            if nom in recit:
                recul = (aujourdhui.weekday() - indice) % 7 or 7
                return (aujourdhui - timedelta(days=recul)).isoformat()
        return None

    @staticmethod
    def _pieces(recit: str) -> list[str]:
        return [
            categorie
            for categorie, indices in INDICES_PIECE.items()
            if any(indice in recit for indice in indices)
        ]


# ------------------------------------------------------------- assistée


CONSIGNE = """Tu extrais des informations d'une déclaration de sinistre habitation.
Réponds UNIQUEMENT par un objet JSON, sans texte autour, avec exactement ces clés :

  "type_sinistre"    : une valeur parmi degat_des_eaux, incendie, bris_de_glace, vol — ou null
  "date_survenance"  : la date du sinistre au format AAAA-MM-JJ — ou null
  "montant_declare"  : le montant en euros, nombre sans séparateur — ou null
  "pieces"           : une liste parmi facture, photo, depot_plainte

Règles :
- Aujourd'hui, nous sommes le {aujourdhui} ({jour_semaine}).
- **Résous les dates relatives** : « hier », « samedi dernier », « mercredi » désignent des jours
  passés ; rends la date correspondante au format AAAA-MM-JJ.
- Pour le type de sinistre, retiens **la cause principale** du dommage. Une fenêtre brisée lors
  d'un cambriolage reste un vol ; une vitre qui se brise seule est un bris de glace.
- Mets null seulement pour ce qui n'est **pas déductible** du récit. N'invente aucune valeur :
  une information absente coûte moins cher qu'une information fausse."""


#: Un modèle de raisonnement consomme des jetons avant de répondre : trop peu, et la réponse
#: revient vide sans qu'aucune erreur ne soit levée. Constaté avec Kimi — 72 jetons pour « OK ».
JETONS_MAX = 3000


class ExtractionAssistee:
    """Un modèle de langage, **si** l'appelant en fournit un.

    Il ne décide rien : il lit un récit et remplit des champs, que l'opérateur relit ensuite.
    En cas d'échec — modèle absent, réponse illisible — le repli déterministe prend la main,
    pour que la démonstration fonctionne sans accès au modèle.

    **Le cabinet ne construit pas son modèle : on le lui donne.** Ce n'est pas un détail de
    style. Ce paquet simule un tiers, et un tiers n'emprunte pas l'infrastructure de Kaldera :
    il a son propre fournisseur, qu'il configure lui-même. C'est aussi ce qui permet au test
    de frontière de rester entier — aucun module de ce paquet n'importe quoi que ce soit du
    système en dehors de sa porte publique.
    """

    nom = "modèle"

    def __init__(self, fabrique: Any = None, repli: Extracteur | None = None) -> None:
        self._fabrique = fabrique
        self.repli = repli or ExtractionParRegles()

    def extraire(self, recit: str, aujourdhui: date | None = None) -> Declaration:
        aujourdhui = aujourdhui or date.today()
        modele = self._modele()
        if modele is None:
            declaration = self.repli.extraire(recit, aujourdhui)
            declaration.incertitudes.append("modèle indisponible : extraction par règles")
            return declaration

        try:
            brut = modele.invoke(
                [
                    (
                        "system",
                        CONSIGNE.format(
                            aujourdhui=aujourdhui.isoformat(),
                            jour_semaine=JOURS_NOMMES[aujourdhui.weekday()],
                        ),
                    ),
                    ("human", recit),
                ]
            )
            donnees = _lire_json(getattr(brut, "content", str(brut)))
        except Exception as exc:  # noqa: BLE001 — un modèle qui tombe ne doit rien bloquer
            declaration = self.repli.extraire(recit, aujourdhui)
            declaration.incertitudes.append(f"modèle en échec ({type(exc).__name__})")
            return declaration

        return _declaration_depuis(donnees, recit, self.nom)

    def _modele(self) -> Any:
        """Le fournisseur donné à la construction, ou rien."""
        return self._fabrique() if self._fabrique is not None else None


def _lire_json(texte: str) -> dict[str, Any]:
    """Un modèle entoure souvent son JSON de texte ou de balises ; on va le chercher."""
    texte = texte.strip()
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut == -1 or fin == -1:
        raise ValueError("aucun objet JSON dans la réponse")
    return json.loads(texte[debut : fin + 1])


def _declaration_depuis(donnees: dict[str, Any], recit: str, extracteur: str) -> Declaration:
    """Relit ce que le modèle a rendu. Ce qui n'est pas conforme devient une incertitude."""
    declaration = Declaration(recit=recit, extracteur=extracteur)

    nature = donnees.get("type_sinistre")
    if nature in TYPES_SINISTRE:
        declaration.type_sinistre = nature
    else:
        declaration.incertitudes.append("type_sinistre")

    survenance = donnees.get("date_survenance")
    if isinstance(survenance, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", survenance):
        declaration.date_survenance = survenance
    else:
        declaration.incertitudes.append("date_survenance")

    montant = donnees.get("montant_declare")
    if isinstance(montant, (int, float)) and not isinstance(montant, bool) and montant > 0:
        declaration.montant_declare = float(montant)
    else:
        declaration.incertitudes.append("montant_declare")

    pieces = donnees.get("pieces")
    if isinstance(pieces, list):
        declaration.pieces = [p for p in pieces if p in TYPES_PIECE]
    return declaration


# ------------------------------------------------------------- choix de l'extracteur


def extraire_chronometre(
    extracteur: Extracteur, recit: str, aujourdhui: date | None = None
) -> Declaration:
    """Extrait, et mesure le temps que cela prend.

    **Pourquoi cette mesure compte.** Les cinq agents du chemin de décision traitent une demande
    complète en **0,04 ms**. Un appel au modèle met entre **3,5 et 9,3 secondes**, mesuré sur ce
    poste — jusqu'à 92 % de l'engagement de service, pour un seul appel, avec un facteur 2,6
    entre deux exécutions.

    C'est la justification empirique de `D31` : un modèle dans le chemin de décision ne ferait
    pas seulement perdre le déterminisme, il consommerait presque tout le budget de temps.
    """
    debut = time.perf_counter()
    declaration = extracteur.extraire(recit, aujourdhui)
    declaration.duree_ms = (time.perf_counter() - debut) * 1000
    return declaration


def extracteur(assiste: bool = False, fabrique: Any = None) -> Extracteur:
    """L'extracteur à utiliser. Déterministe par défaut : le modèle se demande.

    `fabrique` est le fournisseur de modèle du cabinet. Sans lui, l'extraction assistée se
    replie sur les règles et l'annonce dans ses incertitudes.
    """
    return ExtractionAssistee(fabrique) if assiste else ExtractionParRegles()
