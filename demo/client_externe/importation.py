"""Construire une demande à partir de pièces réellement déposées.

Jusqu'ici la démonstration rejouait des scénarios écrits d'avance. Déposer de vrais fichiers
change ce qu'elle prouve : on ne vérifie plus que le système traite bien un cas préparé, mais
qu'il traite un dossier qu'on vient de lui donner.

---

**Trois règles, et elles sont strictes.**

1. **Rien n'est écrit sur disque.** Les fichiers sont lus en mémoire, leur taille et leur nom
   sont retenus, leur contenu ne l'est pas. Un dossier d'assurance contient des pièces
   d'identité, des factures, des photos d'intérieur : les conserver demanderait une base
   légale que cette démonstration n'a pas.

2. **Le contenu ne quitte jamais ce module.** La demande produite ne porte que ce que la
   section 3 des spécifications prévoit : un type, un booléen de lisibilité, un montant.

3. **Aucune extraction documentaire.** Lire un montant dans un PDF est un autre métier, avec
   ses propres taux d'erreur. Le montant d'une facture est **saisi** à côté du fichier. Une
   valeur demandée vaut mieux qu'une valeur devinée.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: Catégories de pièces qu'un dossier peut porter, et ce que la plateforme en attend.
#: `depot_plainte` n'est exigé que pour un vol ; `facture` et `photo` pour le reste.
CATEGORIES: dict[str, dict[str, Any]] = {
    "facture": {
        "libelle": "Facture",
        "extensions": (".pdf", ".jpg", ".jpeg", ".png"),
        "porte_un_montant": True,
        "aide": "Une par fichier. Le montant se saisit à côté : rien n'est lu dans le document.",
    },
    "photo": {
        "libelle": "Photo des dommages",
        "extensions": (".jpg", ".jpeg", ".png", ".webp"),
        "porte_un_montant": False,
        "aide": "JPEG, PNG ou WebP.",
    },
    "depot_plainte": {
        "libelle": "Dépôt de plainte",
        "extensions": (".pdf", ".jpg", ".jpeg", ".png"),
        "porte_un_montant": False,
        "aide": "Exigé pour un vol, inutile pour les autres sinistres.",
    },
}

#: En dessous, un fichier ne porte rien d'exploitable — une page blanche scannée, un envoi coupé.
TAILLE_MINIMALE_OCTETS = 512


class DepotRefuse(ValueError):
    """Le fichier déposé ne correspond pas à ce que la catégorie attend."""


@dataclass
class PieceDeposee:
    """Une pièce telle que l'opérateur vient de la déposer."""

    categorie: str
    nom_fichier: str
    taille_octets: int
    montant: float | None = None
    #: Pourquoi la pièce est jugée illisible, le cas échéant. Vide si elle l'est.
    motif_illisible: str = ""

    @property
    def lisible(self) -> bool:
        return not self.motif_illisible

    def en_piece(self) -> dict[str, Any]:
        """La forme que la section 3 des spécifications attend. Ni le nom, ni le contenu."""
        piece: dict[str, Any] = {"type": self.categorie, "lisible": self.lisible}
        if CATEGORIES[self.categorie]["porte_un_montant"]:
            piece["montant"] = self.montant
        return piece


@dataclass
class Depot:
    """L'ensemble des pièces déposées pour un dossier."""

    pieces: list[PieceDeposee] = field(default_factory=list)

    def ajouter(
        self,
        categorie: str,
        nom_fichier: str,
        taille_octets: int,
        montant: float | None = None,
    ) -> PieceDeposee:
        if categorie not in CATEGORIES:
            raise DepotRefuse(f"catégorie inconnue : « {categorie} »")

        piece = PieceDeposee(
            categorie=categorie,
            nom_fichier=nom_fichier,
            taille_octets=taille_octets,
            montant=montant,
            motif_illisible=motif_illisible(categorie, nom_fichier, taille_octets),
        )
        self.pieces.append(piece)
        return piece

    def retirer(self, nom_fichier: str) -> None:
        self.pieces = [p for p in self.pieces if p.nom_fichier != nom_fichier]

    def par_categorie(self, categorie: str) -> list[PieceDeposee]:
        return [p for p in self.pieces if p.categorie == categorie]

    def en_pieces(self) -> list[dict[str, Any]]:
        return [p.en_piece() for p in self.pieces]

    def montant_des_factures(self) -> float:
        return round(sum(p.montant or 0.0 for p in self.par_categorie("facture") if p.lisible), 2)


def motif_illisible(categorie: str, nom_fichier: str, taille_octets: int) -> str:
    """Pourquoi une pièce est jugée illisible — ou chaîne vide si elle l'est.

    La spécification fournit la lisibilité comme un booléen, sans dire ce qui la détermine.
    Avec de vrais fichiers il faut une convention : elle est ici **vérifiable et explicable**,
    ce qui vaut mieux qu'un jugement sur le contenu que personne ne saurait reproduire.
    """
    attendues = CATEGORIES[categorie]["extensions"]
    minuscule = nom_fichier.lower()
    if not any(minuscule.endswith(extension) for extension in attendues):
        return f"format inattendu — {' ou '.join(attendues)} attendu"
    if taille_octets <= 0:
        return "fichier vide"
    if taille_octets < TAILLE_MINIMALE_OCTETS:
        return f"fichier trop petit ({taille_octets} octets) pour porter quoi que ce soit"
    return ""


def pieces_exigees(type_sinistre: str) -> tuple[str, ...]:
    """Ce que la section 5 des spécifications exige, selon la nature du sinistre."""
    return ("facture", "depot_plainte") if type_sinistre == "vol" else ("facture", "photo")


def manquantes(depot: Depot, type_sinistre: str) -> list[str]:
    """Les catégories exigées dont aucune pièce lisible n'a été déposée.

    C'est un **aperçu** rendu à l'opérateur avant qu'il dépose : la plateforme refera le
    contrôle elle-même, et c'est elle qui fait foi.
    """
    absentes = []
    for categorie in pieces_exigees(type_sinistre):
        if not any(p.lisible for p in depot.par_categorie(categorie)):
            absentes.append(categorie)
    return absentes


def construire_demande(dossier: dict[str, Any], depot: Depot, traduire: Any) -> dict[str, Any]:
    """Assemble la demande : l'identité vient du dossier courtier, les pièces du dépôt.

    ``traduire`` est la fonction de traduction du courtier — passée en argument plutôt
    qu'importée, pour que ce module reste utilisable seul et testable sans elle.
    """
    demande = traduire(dossier)
    demande["pieces"] = depot.en_pieces()
    demande["espace_assure"] = {"depots": []}
    return demande
