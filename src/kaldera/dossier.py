"""La mémoire partagée d'une demande : quatre zones aux règles d'accès distinctes.

| Zone                | Règle d'accès                                                      |
| ------------------- | ------------------------------------------------------------------ |
| demande d'origine   | lecture seule — personne ne la modifie                             |
| parties publiées    | une section, un auteur, une seule écriture                         |
| zone de travail     | libre, mais **n'apparaît jamais** dans la fiche                    |
| journal de bord     | ajout seul — aucune étape n'est effacée ni réécrite                |

Un dossier est créé par demande et n'est partagé avec aucune autre (décision D8). Seul le
répartiteur écrit dedans ; les agents reçoivent leurs entrées et rendent un résultat (décision D7).
"""

from __future__ import annotations

from typing import Any

SECTIONS_METIER = ("eligibilite", "pieces", "estimation", "avis_fraude", "issue")


class SectionDejaPubliee(RuntimeError):
    """Une partie du dossier ne s'écrit qu'une fois, par un seul auteur."""


class SectionInconnue(RuntimeError):
    """Seules les cinq sections métier peuvent être publiées."""


class Dossier:
    """L'état d'une demande en cours de traitement."""

    def __init__(self, demande: dict[str, Any]) -> None:
        self._demande = demande
        self._parties: dict[str, Any] = {}
        self._auteurs: dict[str, str] = {}
        self._travail: dict[str, Any] = {}
        self._journal: list[dict[str, Any]] = []
        self._arret: dict[str, Any] | None = None

    # ------------------------------------------------------- zone 1 : la demande

    @property
    def demande(self) -> dict[str, Any]:
        """La demande d'origine. À lire, jamais à modifier."""
        return self._demande

    @property
    def reference(self) -> str:
        return str(self._demande["reference"])

    # --------------------------------------------- zone 2 : les parties publiées

    def publier(self, section: str, contenu: Any, auteur: str) -> None:
        """Dépose une partie du dossier au nom de son auteur. Une seule fois par section."""
        if section not in SECTIONS_METIER:
            raise SectionInconnue(f"section « {section} » inconnue")
        if section in self._parties:
            raise SectionDejaPubliee(
                f"{self.reference} : « {section} » déjà publiée par « {self._auteurs[section]} »"
            )
        self._parties[section] = contenu
        self._auteurs[section] = auteur

    def partie(self, section: str, defaut: Any = None) -> Any:
        return self._parties.get(section, defaut)

    def publiee(self, section: str) -> bool:
        return section in self._parties

    def auteur(self, section: str) -> str | None:
        return self._auteurs.get(section)

    @property
    def parties(self) -> dict[str, Any]:
        return dict(self._parties)

    # --------------------------------------------- zone 3 : la zone de travail

    def noter(self, cle: str, valeur: Any) -> None:
        """Écrit dans la zone de travail. Rien de ce qui s'y trouve ne sort dans la fiche."""
        self._travail[cle] = valeur

    def note(self, cle: str, defaut: Any = None) -> Any:
        return self._travail.get(cle, defaut)

    @property
    def travail(self) -> dict[str, Any]:
        return dict(self._travail)

    # ----------------------------------------------- zone 4 : le journal de bord

    def journaliser(
        self,
        agent: str,
        action: str,
        ecrit: list[str],
        duree_ms: float,
        statut: str = "ok",
        appels_externes: int = 0,
        verdict: str = "",
    ) -> None:
        """Ajoute une étape. Le journal ne se réécrit pas.

        ``appels_externes`` dit si l'étape est sortie du système ; ``verdict`` dit ce que l'agent
        a rendu, et donc **quelle branche du plan a été empruntée**. Le contrat d'intégration
        laisse les champs supplémentaires libres.

        Sans eux, on ne saurait ni distinguer un agent qui n'a pas consulté d'un agent dont la
        consultation a échoué très vite, ni reconstituer le chemin suivi dans le plan autrement
        qu'en le devinant.
        """
        self._journal.append(
            {
                "agent": agent,
                "action": action,
                "ecrit": list(ecrit),
                "duree_ms": round(duree_ms, 2),
                "statut": statut,
                "appels_externes": int(appels_externes),
                "verdict": verdict,
            }
        )

    @property
    def journal(self) -> list[dict[str, Any]]:
        return [dict(etape) for etape in self._journal]

    @property
    def etapes(self) -> int:
        return len(self._journal)

    # ------------------------------------------------------------------- arrêt

    def signaler_arret(self, borne: str, detail: str | None = None) -> None:
        """Nomme la borne qui a interrompu le traitement. Le premier arrêt l'emporte."""
        if self._arret is None:
            self._arret = {"borne": borne}
            if detail:
                self._arret["detail"] = detail

    @property
    def arret(self) -> dict[str, Any] | None:
        return dict(self._arret) if self._arret else None
