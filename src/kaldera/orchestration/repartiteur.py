"""Le répartiteur : déléguer → réceptionner → avancer (décisions D5, D7, D12).

Il ne juge rien. Il confie une étape à l'agent dont c'est le métier, réceptionne ce que celui-ci
lui rend, le dépose dans le dossier **au nom de son auteur**, puis lit le plan pour savoir où aller.
Il est greffier, pas auteur : son nom n'apparaît pas dans le journal de bord, et aucune section
métier ne lui est imputée.

Quand une borne est atteinte, il n'interrompt pas brutalement : il confie une dernière main à
l'agent de décision, qui écrit une escalade motivée, puis signale l'arrêt dans la fiche.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from .. import agents, mesures, observabilite
from ..dossier import Dossier
from ..partenaire import Passerelle
from . import bornes, plan

#: L'agent chargé de chaque étape du plan.
AGENTS: dict[str, Any] = {
    plan.ELIGIBILITE: agents.eligibilite,
    plan.PIECES: agents.pieces,
    plan.ESTIMATION: agents.estimation,
    plan.ANTIFRAUDE: agents.antifraude,
    plan.DECISION: agents.decision,
}


class ReceptionRefusee(RuntimeError):
    """Un agent a rendu autre chose que la section dont il est l'auteur."""


class AgentDefaillant(RuntimeError):
    """Le code d'un agent a leve une exception.

    C'est un defaut a corriger, pas un cas metier. Mais la demande d'un assure ne disparait pas
    pour autant : elle ressort par la porte avec une escalade motivee, pour qu'un humain la
    reprenne. C'est l'exigence EX-1 — « une demande ne reste jamais sans issue ».
    """


class Repartiteur:
    """Déroule le plan pour une demande, et une seule."""

    def __init__(self, partenaire_url: str | None = None) -> None:
        self.partenaire_url = partenaire_url

    # ------------------------------------------------------------------ public

    def traiter(self, demande: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """Rend la fiche de décision, les compteurs et l'observation de cette demande."""
        with observabilite.demande_en_cours(str(demande["reference"])) as faits:
            return self._derouler(demande, faits)

    def _derouler(
        self, demande: dict[str, Any], faits: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        dossier = Dossier(demande)
        compteurs = mesures.Compteurs()
        # Une passerelle par demande : son registre d'appels ne traverse pas les demandes (D8).
        passerelle = Passerelle(self.partenaire_url)
        debut = perf_counter()
        borne: str | None = None

        etape: str | None = plan.PREMIERE_ETAPE
        while etape is not None:
            garde_fou = self._borne_avant(etape, dossier, debut)
            if garde_fou:
                borne = garde_fou
                break

            try:
                verdict = self._confier(etape, dossier, compteurs, borne, passerelle)
            except (AgentDefaillant, ReceptionRefusee):
                borne = bornes.AGENT_DEFAILLANT
                break
            borne = plan.borne_atteinte(etape, verdict) or borne
            suivante = plan.etape_suivante(etape, verdict)
            self._tracer_routage(dossier, etape, verdict, suivante)
            etape = suivante

        if not dossier.publiee("issue"):
            try:
                self._confier(plan.DECISION, dossier, compteurs, borne, passerelle)
            except (AgentDefaillant, ReceptionRefusee):
                borne = bornes.AGENT_DEFAILLANT

        if not dossier.publiee("issue"):  # ne doit jamais arriver : c'est un défaut
            borne = bornes.CLOTURE_MANQUANTE
            dossier.publier(
                "issue",
                {
                    **_escalade_de_secours(),
                    "mode_degrade": False,
                },
                agents.decision.NOM,
            )
            dossier.journaliser(agents.decision.NOM, "secours", ["issue"], 0.0, statut="echec")

        if borne:
            dossier.signaler_arret(borne)
            observabilite.alerter("borne.atteinte", reference=dossier.reference, borne=borne)

        fiche = self._fiche(dossier)
        faits.update(
            issue=fiche["issue"],
            decision=fiche.get("decision"),
            file=fiche.get("file"),
            mode_degrade=fiche.get("mode_degrade"),
            etapes=len(fiche["trace"]),
        )
        observation = mesures.observer(fiche, dossier.note("cause_indisponibilite"))
        return fiche, {"compteurs": compteurs.brut(), "observation": observation}

    # ---------------------------------------------------------------- déléguer

    def _confier(
        self,
        etape: str,
        dossier: Dossier,
        compteurs: mesures.Compteurs,
        borne_courante: str | None,
        passerelle: Passerelle | None = None,
    ) -> str:
        """Confie une étape, réceptionne, dépose, journalise. Rend le verdict de l'agent."""
        agent = AGENTS[etape]
        entrees = self._entrees(etape, dossier, borne_courante, passerelle)

        debut = perf_counter()
        try:
            resultat = agent.traiter(entrees)
        except Exception:  # noqa: BLE001 — un defaut de code ne fait pas disparaitre une demande
            duree_ms = (perf_counter() - debut) * 1000
            dossier.journaliser(agent.NOM, etape, [], duree_ms, statut="echec")
            compteurs.enregistrer(agent.NOM, duree_ms, echec=True)
            observabilite.alerter(
                "agent.defaillant", reference=dossier.reference, agent=agent.NOM, action=etape
            )
            raise AgentDefaillant(etape) from None
        duree_ms = (perf_counter() - debut) * 1000

        section = self._receptionner(agent, resultat)
        if section is not None:
            dossier.publier(section, resultat["contenu"], agent.NOM)
        for cle, valeur in resultat.get("travail", {}).items():
            dossier.noter(cle, valeur)

        echec = bool(resultat.get("echec", False))
        externes = int(resultat.get("appels_externes", 0))
        verdict = str(resultat["verdict"])
        dossier.journaliser(
            agent.NOM,
            etape,
            [section] if section else [],
            duree_ms,
            statut="echec" if echec else "ok",
            appels_externes=externes,
            verdict=verdict,
        )
        compteurs.enregistrer(
            agent.NOM,
            duree_ms,
            echec=echec,
            appels_externes=externes,
        )
        observabilite.noter(
            "etape",
            reference=dossier.reference,
            agent=agent.NOM,
            action=etape,
            ecrit=[section] if section else [],
            duree_ms=round(duree_ms, 2),
            statut="echec" if echec else "ok",
            appels_externes=externes,
            verdict=verdict,
        )
        return verdict

    @staticmethod
    def _tracer_routage(dossier: Dossier, etape: str, verdict: str, suivante: str | None) -> None:
        """Le journal de routage du répartiteur, **séparé** du journal de bord (décision D12).

        Le journal de bord dit qui a fait quoi : il ne doit contenir que des agents auteurs.
        Les décisions d'aiguillage sont d'une autre nature — elles servent à comprendre un
        parcours, pas à imputer un acte. Elles vivent donc dans la zone de travail, qui ne
        ressort pas dans la fiche.
        """
        routage = list(dossier.note("routage", []))
        routage.append({"apres": etape, "verdict": verdict, "vers": suivante})
        dossier.noter("routage", routage)

    def _entrees(
        self,
        etape: str,
        dossier: Dossier,
        borne_courante: str | None,
        passerelle: Passerelle | None = None,
    ) -> dict[str, Any]:
        """Extrait du dossier ce dont l'agent a besoin. Aucun agent ne reçoit le dossier."""
        demande = dossier.demande
        if etape == plan.ELIGIBILITE:
            return agents.eligibilite.entrees(demande)
        if etape == plan.PIECES:
            return agents.pieces.entrees(demande, dossier.travail)
        if etape == plan.ESTIMATION:
            return agents.estimation.entrees(demande, dossier.partie("pieces", {}))
        if etape == plan.ANTIFRAUDE:
            assert passerelle is not None
            return agents.antifraude.entrees(
                demande,
                dossier.partie("estimation", {}),
                int(dossier.note("anciennete_contrat_jours", 0)),
                passerelle,
            )
        return agents.decision.entrees(
            dossier.parties,
            dossier.travail,
            bornes.motif(borne_courante) if borne_courante else None,
        )

    # -------------------------------------------------------------- réceptionner

    @staticmethod
    def _receptionner(agent: Any, resultat: dict[str, Any]) -> str | None:
        """Vérifie que l'agent rend sa section, ou aucune. Rien d'autre n'est accepté."""
        section = resultat.get("section")
        if section is None:
            return None
        if section != agent.SECTION:
            raise ReceptionRefusee(
                f"l'agent « {agent.NOM} » a rendu « {section} », attendu « {agent.SECTION} »"
            )
        return str(section)

    # ------------------------------------------------------------------ bornes

    def _borne_avant(self, etape: str, dossier: Dossier, debut: float) -> str | None:
        """Garde-fous vérifiés avant de confier une étape. Une étape reste pour la sortie."""
        if dossier.etapes >= bornes.BORNES["etapes_max"] - 1:
            return bornes.ETAPES_MAX_ATTEINT
        if perf_counter() - debut >= bornes.SORTIE_ORDONNEE_S:
            return bornes.DUREE_MAX_ATTEINTE
        if etape == plan.PIECES:
            faites = sum(1 for e in dossier.journal if e["action"] == plan.PIECES)
            if faites >= bornes.BORNES["pieces_tentatives_max"]:
                return bornes.PIECES_TENTATIVES_EPUISEES
        return None

    # ------------------------------------------------------------------- fiche

    @staticmethod
    def _fiche(dossier: Dossier) -> dict[str, Any]:
        issue = dict(dossier.partie("issue") or {})
        mode_degrade = bool(issue.pop("mode_degrade", False))
        return {
            "reference": dossier.reference,
            **issue,
            "avis_fraude": dossier.partie("avis_fraude"),
            "mode_degrade": mode_degrade,
            "trace": dossier.journal,
            "arret": dossier.arret,
        }


def _escalade_de_secours() -> dict[str, Any]:
    from ..regles import issues

    return issues.escalade_sur_borne(bornes.motif(bornes.CLOTURE_MANQUANTE))
