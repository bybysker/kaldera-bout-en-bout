"""Journal d'exploitation : savoir ce que le système a fait, après coup.

La trace d'une demande et les mesures d'un lot disent **ce qui s'est passé pour cette demande**.
Elles ne disent pas ce qui s'est passé hier à 14 h, ni pourquoi le partenaire a refusé trois
requêtes d'affilée. C'est le rôle de ce journal.

---

**La règle qui prime sur toutes les autres : aucune donnée personnelle n'entre dans un journal.**

Un journal survit à la demande, se copie, s'exporte, se transmet à un service de supervision.
Y laisser un nom ou un IBAN ruine `EX-3` plus sûrement qu'une passerelle mal filtrée — la
passerelle, au moins, est testée à chaque exécution.

Ce module ne journalise donc que des **faits de traitement** : quelle étape, quel agent, combien
de temps, quelle issue. Jamais le contenu d'une demande. La référence du dossier est le seul
identifiant retenu, et c'est délibéré : sans elle, un journal est inexploitable, et elle ne
désigne personne hors du système d'information de l'assureur.

Un garde-fou le vérifie : ``verifier_absence_de_donnees_personnelles``.
"""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from time import perf_counter
from typing import Any, Iterator

JOURNAL = "kaldera"

#: Champs d'une demande qui ne doivent jamais atteindre un journal (specs §3, contrat §2).
CHAMPS_INTERDITS = (
    "nom",
    "prenom",
    "email",
    "telephone",
    "iban",
    "adresse",
    "code_postal",
    "id_client",
    "description",
    "numero",
)


class ChampInterdit(RuntimeError):
    """Une donnée personnelle a tenté d'entrer dans le journal."""


class FormatJSON(logging.Formatter):
    """Une ligne JSON par événement — lisible par un humain, exploitable par un outil."""

    def format(self, enregistrement: logging.LogRecord) -> str:
        evenement = {
            "horodatage": self.formatTime(enregistrement, "%Y-%m-%dT%H:%M:%S"),
            "niveau": enregistrement.levelname.lower(),
            "evenement": enregistrement.getMessage(),
        }
        evenement.update(getattr(enregistrement, "faits", {}))
        return json.dumps(evenement, ensure_ascii=False)


def journal() -> logging.Logger:
    return logging.getLogger(JOURNAL)


def configurer(
    niveau: int = logging.INFO, fichier: str | None = None, console: bool = False
) -> logging.Logger:
    """Installe le journal. Sans appel, la bibliothèque reste silencieuse — c'est voulu.

    Une bibliothèque qui écrit sur la sortie standard sans qu'on le lui demande est une
    bibliothèque qu'on finit par faire taire, journal compris.
    """
    enregistreur = journal()
    enregistreur.setLevel(niveau)
    enregistreur.handlers.clear()
    enregistreur.propagate = False

    if fichier:
        vers_fichier = logging.FileHandler(fichier, encoding="utf-8")
        vers_fichier.setFormatter(FormatJSON())
        enregistreur.addHandler(vers_fichier)
    if console or not fichier:
        vers_console = logging.StreamHandler()
        vers_console.setFormatter(FormatJSON())
        enregistreur.addHandler(vers_console)
    return enregistreur


def verifier_absence_de_donnees_personnelles(faits: dict[str, Any]) -> None:
    """Refuse l'événement plutôt que de le journaliser à moitié.

    Échouer bruyamment vaut mieux qu'écrire discrètement un IBAN dans un fichier qui sera
    conservé six mois.
    """
    for cle in faits:
        if cle in CHAMPS_INTERDITS:
            raise ChampInterdit(f"« {cle} » n'a rien à faire dans un journal")


def noter(evenement: str, **faits: Any) -> None:
    """Journalise un fait de traitement."""
    verifier_absence_de_donnees_personnelles(faits)
    journal().info(evenement, extra={"faits": faits})


def alerter(evenement: str, **faits: Any) -> None:
    """Journalise ce qui ne devrait pas arriver : borne atteinte, agent défaillant, rejet."""
    verifier_absence_de_donnees_personnelles(faits)
    journal().warning(evenement, extra={"faits": faits})


@contextmanager
def demande_en_cours(reference: str) -> Iterator[dict[str, Any]]:
    """Encadre le traitement d'une demande : début, fin, durée, issue.

    Le dictionnaire rendu se remplit en chemin ; son contenu est journalisé à la sortie, même
    si une exception traverse — sinon les incidents seraient les seuls à ne pas être journalisés.
    """
    faits: dict[str, Any] = {"reference": reference}
    debut = perf_counter()
    noter("demande.debut", reference=reference)
    try:
        yield faits
    except Exception as exc:  # noqa: BLE001 — journalisé puis relancé
        alerter(
            "demande.incident",
            reference=reference,
            duree_ms=round((perf_counter() - debut) * 1000, 2),
            exception=type(exc).__name__,
        )
        raise
    else:
        faits["duree_ms"] = round((perf_counter() - debut) * 1000, 2)
        noter("demande.fin", **faits)
