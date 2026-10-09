"""Construction de la charge envoyée au partenaire (décision D14).

**En partant de rien, jamais en filtrant la demande.** La différence n'est pas théorique : un
filtre laisse passer tout champ ajouté plus tard à la demande, sans que personne ne l'ait décidé.
Ici, un champ qui n'est pas écrit explicitement ci-dessous ne part pas.

Les sept champs et leurs contraintes viennent du contrat partenaire version 2.0, §2.
"""

from __future__ import annotations

from typing import Any

from ..regles.calendrier import jours_entre

#: Les seuls champs que le contrat autorise. Toute autre clé est un manquement.
CHAMPS_AUTORISES = frozenset(
    {
        "reference_dossier",
        "type_sinistre",
        "montant_declare",
        "date_survenance",
        "anciennete_contrat_jours",
        "sinistres_12_mois",
        "departement",
    }
)


def construire(demande: dict[str, Any]) -> dict[str, Any]:
    """Les sept champs du contrat, écrits un par un.

    La conception avait d'abord exclu toute date (décision D15), après avoir vérifié qu'avec une
    date et une durée on retrouve la souscription par soustraction. **Le contrat exige la date de
    survenance** : il accepte donc sciemment cette déductibilité. L'arbitrage se tranche contre
    nous, et c'est écrit.
    """
    contrat, sinistre = demande["contrat"], demande["sinistre"]
    return {
        "reference_dossier": demande["reference"],
        "type_sinistre": sinistre["type"],
        "montant_declare": float(sinistre["montant_declare"]),
        "date_survenance": sinistre["date_survenance"],
        "anciennete_contrat_jours": jours_entre(
            contrat["date_souscription"], sinistre["date_survenance"]
        ),
        "sinistres_12_mois": int(demande.get("historique", {}).get("sinistres_12_mois", 0)),
        "departement": departement(demande["assure"]["code_postal"]),
    }


def departement(code_postal: str) -> str:
    """Département déduit du code postal, **sans jamais recopier le code postal entier**.

    Le code postal complet fait partie des coordonnées que le contrat interdit de transmettre
    « sous quelque forme que ce soit ».
    """
    code = str(code_postal).strip()
    if code.startswith(("97", "98")):
        return code[:3]  # outre-mer
    if code.startswith("20"):
        # Corse : le contrat attend 2A ou 2B. La limite usuelle entre Corse-du-Sud et
        # Haute-Corse passe à 20200.
        return "2A" if code < "20200" else "2B"
    return code[:2]
