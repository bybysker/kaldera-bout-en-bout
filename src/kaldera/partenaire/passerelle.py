"""Le seul point du système qui parle au partenaire anti-fraude (décision D17).

Un filtre dispersé est un filtre invérifiable : l'adresse, le jeton et la construction de la
charge sont ici, et nulle part ailleurs. Un test d'architecture le vérifie sur les imports.

---

**Les douze hypothèses de conception, confrontées au contrat v2.0** (décision D13). Elles ont été
posées avant d'avoir le contrat ; onze sur douze sont confirmées. Les garder réunies ici permet
de les relire le jour où le contrat change.

| H | Hypothèse posée en conception | Verdict |
| --- | --- | --- |
| H1 | Échange synchrone, une requête une réponse | confirmée |
| H2 | JSON-RPC 2.0, méthode `message/send` | confirmée |
| H3 | Jeton porteur dans l'en-tête `Authorization` | confirmée |
| H4 | La référence du dossier sert de clé d'appariement | confirmée |
| H5 | L'avis porte un niveau de risque parmi trois | confirmée |
| H6 | Un score numérique accompagne le niveau | confirmée, bornes [0 ; 1] |
| H7 | Validation stricte : aucun champ en trop toléré | confirmée |
| H8 | Le partenaire répond en quelques secondes | confirmée : 2 s d'engagement |
| H9 | Un délai d'abandon de l'ordre de 3 à 5 s | confirmée : **3 s**, fixé par le contrat |
| H10 | Aucune relance après échec | confirmée, et **étendue** aux trois cas |
| H11 | Le partenaire se découvre par une carte d'agent | confirmée : `/.well-known/agent.json` |
| H12 | Aucune date transmise, seulement des durées | **infirmée** : le contrat exige `date_survenance` |

H12 est la seule contredite. L'arbitrage avait été annoncé : avec une date et une durée, on
retrouve la souscription par soustraction. Le contrat accepte sciemment cette déductibilité.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import httpx

from .. import observabilite
from . import charge as module_charge
from . import erreurs, validation
from .registre import Registre

URL_PAR_DEFAUT = "http://localhost:8100"

#: Délai d'abandon, fixé par le contrat §5. Le partenaire s'engage à 2 s ; nous abandonnons à 3.
DELAI_ABANDON_S = 3.0


def url_partenaire(url: str | None = None) -> str:
    """L'adresse du partenaire — lue ici, et nulle part ailleurs."""
    return (url or os.environ.get("PARTENAIRE_URL") or URL_PAR_DEFAUT).rstrip("/")


def _jeton() -> str:
    """Le jeton d'accès, lu dans l'environnement. Jamais en dur, jamais journalisé."""
    return os.environ.get("PARTENAIRE_JETON", "")


class Passerelle:
    """Construit, envoie, valide — et rend un verdict unique.

    Une passerelle par demande : le registre d'appels ne traverse pas les demandes (décision D8).
    """

    def __init__(self, url: str | None = None) -> None:
        self.url = url_partenaire(url)
        self.registre = Registre()

    def consulter(self, demande: dict[str, Any]) -> dict[str, Any]:
        """Demande l'avis du partenaire pour une demande.

        Rend toujours la même forme : ``{"avis": …, "cause": …, "evaluation_id": …}``. Soit un
        avis est obtenu, soit il ne l'est pas et la cause est nommée — jamais les deux, et jamais
        rien du contenu rejeté.
        """
        reference = str(demande["reference"])
        if self.registre.deja_appele(reference):
            # Le contrat refuse le doublon et le signale comme manquement : ne pas même l'émettre.
            return _verdict(cause=erreurs.APPEL_DEJA_FAIT)

        donnees = module_charge.construire(demande)
        identifiant = str(uuid.uuid4())
        enveloppe = {
            "jsonrpc": "2.0",
            "id": identifiant,
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "messageId": str(uuid.uuid4()),
                    "parts": [{"kind": "data", "data": donnees}],
                }
            },
        }

        self.registre.marquer(reference)
        corps, cause = self._envoyer(enveloppe)
        if cause is not None:
            observabilite.alerter(
                "partenaire.indisponible",
                reference=reference,
                cause=cause,
                niveau_validation=erreurs.niveau(cause),
            )
            return _verdict(cause=cause)

        evaluation, cause = validation.valider(corps, identifiant, reference)
        if cause is not None or evaluation is None:
            cause = cause or erreurs.ENVELOPPE_NON_CONFORME
            observabilite.alerter(
                "partenaire.reponse_ecartee",
                reference=reference,
                cause=cause,
                niveau_validation=erreurs.niveau(cause),
            )
            return _verdict(cause=cause)

        return _verdict(
            avis={"niveau": evaluation["niveau"], "score": evaluation["score"]},
            evaluation_id=evaluation["evaluation_id"],
        )

    # ------------------------------------------------------- niveau 1 : transport

    def _envoyer(self, enveloppe: dict[str, Any]) -> tuple[Any, str | None]:
        """Envoi et contrôle du transport. Aucune relance, dans aucun cas (décision D19)."""
        entetes = {"Authorization": f"Bearer {_jeton()}"}
        try:
            reponse = httpx.post(
                f"{self.url}/a2a",
                json=enveloppe,
                headers=entetes,
                timeout=DELAI_ABANDON_S,
            )
        except httpx.TimeoutException:
            return None, erreurs.DELAI_DEPASSE
        except httpx.HTTPError:
            return None, erreurs.ERREUR_RESEAU

        if reponse.status_code == 401:
            return None, erreurs.AUTHENTIFICATION_REFUSEE
        if reponse.status_code == 503:
            return None, erreurs.SERVICE_INDISPONIBLE
        if reponse.status_code >= 400:
            # Une erreur JSON-RPC peut arriver avec un code HTTP d'erreur : la lire quand même.
            try:
                return reponse.json(), None
            except ValueError:
                return None, erreurs.SERVICE_INDISPONIBLE

        try:
            return reponse.json(), None
        except ValueError:
            return None, erreurs.CORPS_ILLISIBLE


def _verdict(
    *,
    avis: dict[str, Any] | None = None,
    cause: str | None = None,
    evaluation_id: str | None = None,
) -> dict[str, Any]:
    return {"avis": avis, "cause": cause, "evaluation_id": evaluation_id}
