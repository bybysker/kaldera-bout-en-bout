"""Ce qu'un gestionnaire fait d'un dossier escaladé.

**Ceci est hors du système automatisé.** Le brief s'arrête à l'escalade : la plateforme confie
le dossier à une file humaine, et son travail est terminé. Ce qui se passe ensuite est le métier
du gestionnaire, pas celui de l'équipe d'agents.

Le modéliser quand même a une raison : une escalade n'est pas une fin. Tant qu'on ne voit pas ce
qu'elle produit — une décision écrite, un complément demandé, un dossier transmis ailleurs — on
ne sait pas si l'escalade a servi à quelque chose. C'est ce que montre l'espace gestionnaire.

Rien ici n'écrit dans la plateforme : les décisions prises vivent le temps de la démonstration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

#: Ce qu'un gestionnaire peut décider, et ce que cela produit pour l'assuré.
SUITES: dict[str, dict[str, Any]] = {
    "accepter": {
        "libelle": "Accepter et indemniser",
        "demande_un_montant": True,
        "motif": "Remboursement accordé après examen : {montant:.2f} €",
        "issue": "decision",
        "decision": "acceptee",
    },
    "refuser": {
        "libelle": "Refuser",
        "demande_un_montant": False,
        "motif": "Demande refusée après examen : {precision}",
        "issue": "decision",
        "decision": "refusee",
    },
    "complement": {
        "libelle": "Demander un complément à l'assuré",
        "demande_un_montant": False,
        "motif": "Pièces manquantes : {precision}",
        "issue": "escalade",
        "decision": None,
    },
    "cellule_fraude": {
        "libelle": "Transmettre à la cellule anti-fraude",
        "demande_un_montant": False,
        "motif": "Suspicion de fraude : {precision}",
        "issue": "escalade",
        "decision": None,
    },
}


class SuiteInconnue(ValueError):
    """La suite demandée ne fait pas partie de ce qu'un gestionnaire peut décider."""


class MontantManquant(ValueError):
    """Accepter un dossier sans dire combien n'a pas de sens."""


@dataclass
class DecisionManuelle:
    """Une décision prise par un humain sur un dossier escaladé."""

    reference: str
    suite: str
    gestionnaire: str
    montant: float | None = None
    precision: str = ""
    prise_le: date = field(default_factory=date.today)

    def en_fiche(self, fiche_initiale: dict[str, Any]) -> dict[str, Any]:
        """La fiche telle qu'elle devient après la décision du gestionnaire.

        Elle garde la forme de celle que la plateforme produit — c'est ce qui permet de
        réutiliser la rédaction des courriers sans la dupliquer.
        """
        reglage = SUITES[self.suite]
        motif = reglage["motif"].format(
            montant=self.montant or 0.0,
            precision=self.precision or "voir le dossier",
        )
        return {
            **fiche_initiale,
            "issue": reglage["issue"],
            "decision": reglage["decision"],
            "montant_rembourse": self.montant
            if self.suite == "accepter"
            else (0.0 if self.suite == "refuser" else None),
            "motif": motif,
            "file": "cellule_fraude"
            if self.suite == "cellule_fraude"
            else ("gestionnaire" if self.suite == "complement" else None),
            "decide_par": self.gestionnaire,
            "decide_le": self.prise_le.isoformat(),
        }


def decider(
    reference: str,
    suite: str,
    gestionnaire: str,
    montant: float | None = None,
    precision: str = "",
    aujourdhui: date | None = None,
) -> DecisionManuelle:
    """Enregistre une décision manuelle, après l'avoir vérifiée."""
    if suite not in SUITES:
        raise SuiteInconnue(f"suite inconnue : « {suite} »")
    if SUITES[suite]["demande_un_montant"] and not montant:
        raise MontantManquant("accepter un dossier sans montant n'a pas de sens")
    if not gestionnaire.strip():
        raise ValueError("une décision manuelle est signée : le gestionnaire doit être nommé")

    return DecisionManuelle(
        reference=reference,
        suite=suite,
        gestionnaire=gestionnaire.strip(),
        montant=round(float(montant), 2) if montant else None,
        precision=precision.strip(),
        prise_le=aujourdhui or date.today(),
    )


def file_d_attente(fiches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Les dossiers qui attendent un humain, les plus sensibles d'abord.

    La cellule anti-fraude passe avant le gestionnaire : un dossier qu'on soupçonne attend moins
    bien qu'un dossier qu'on vérifie. Et un dossier sans avis anti-fraude passe avant un dossier
    qui en a un, parce que personne ne l'a encore regardé.
    """

    def rang(fiche: dict[str, Any]) -> tuple[int, int, str]:
        return (
            0 if fiche.get("file") == "cellule_fraude" else 1,
            0 if fiche.get("mode_degrade") else 1,
            fiche.get("reference", ""),
        )

    return sorted(
        (f for f in fiches if f.get("issue") == "escalade"),
        key=rang,
    )
