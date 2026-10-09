"""Causes normalisées d'indisponibilité du partenaire.

Trois situations mènent au même endroit — le mode dégradé — mais il faut pouvoir les distinguer
en mesure : si la part rejetée pour la forme monte, c'est notre lecture du contrat qui dérive,
pas le partenaire qui tombe.
"""

from __future__ import annotations

# Niveau 1 — transport
DELAI_DEPASSE = "delai_depasse"
SERVICE_INDISPONIBLE = "service_indisponible"
AUTHENTIFICATION_REFUSEE = "authentification_refusee"
ERREUR_RESEAU = "erreur_reseau"

# Niveau 2 — lisibilité
CORPS_ILLISIBLE = "corps_illisible"
ENVELOPPE_NON_CONFORME = "enveloppe_non_conforme"
ERREUR_RPC = "erreur_rpc"
REQUETE_REFUSEE = "requete_refusee"  # -32602 : notre charge est non conforme
DOUBLON_REFUSE = "doublon_refuse"  # -32029 : manquement au contrat

# Niveau 3 — forme
CHAMPS_EN_TROP = "champs_en_trop"
CHAMPS_ABSENTS = "champs_absents"
TYPES_INVALIDES = "types_invalides"

# Niveau 4 — sens
SCORE_HORS_BORNES = "score_hors_bornes"
NIVEAU_INCOHERENT = "niveau_incoherent"
DOSSIER_DIFFERENT = "dossier_different"
IDENTIFIANT_DIFFERENT = "identifiant_different"

# Limites d'appel
APPEL_DEJA_FAIT = "appel_deja_fait"

#: Le niveau de validation auquel chaque cause se rattache — pour les mesures.
NIVEAU: dict[str, int] = {
    DELAI_DEPASSE: 1,
    SERVICE_INDISPONIBLE: 1,
    AUTHENTIFICATION_REFUSEE: 1,
    ERREUR_RESEAU: 1,
    CORPS_ILLISIBLE: 2,
    ENVELOPPE_NON_CONFORME: 2,
    ERREUR_RPC: 2,
    REQUETE_REFUSEE: 2,
    DOUBLON_REFUSE: 2,
    CHAMPS_EN_TROP: 3,
    CHAMPS_ABSENTS: 3,
    TYPES_INVALIDES: 3,
    SCORE_HORS_BORNES: 4,
    NIVEAU_INCOHERENT: 4,
    DOSSIER_DIFFERENT: 4,
    IDENTIFIANT_DIFFERENT: 4,
    APPEL_DEJA_FAIT: 0,
}

#: Causes qui révèlent que notre lecture du contrat est fausse, et non que le partenaire est tombé.
REJET_DE_FORME = frozenset({CHAMPS_EN_TROP, CHAMPS_ABSENTS, TYPES_INVALIDES, REQUETE_REFUSEE})

#: Codes JSON-RPC du contrat (§4), et la cause que chacun produit.
CODES_RPC: dict[int, str] = {
    -32700: CORPS_ILLISIBLE,
    -32600: ENVELOPPE_NON_CONFORME,
    -32601: ERREUR_RPC,
    -32602: REQUETE_REFUSEE,
    -32029: DOUBLON_REFUSE,
}


def cause_rpc(code: object) -> str:
    """La cause correspondant a un code d'erreur JSON-RPC du contrat."""
    if isinstance(code, int):
        return CODES_RPC.get(code, ERREUR_RPC)
    return ERREUR_RPC


def niveau(cause: str) -> int:
    return NIVEAU.get(cause, 0)
