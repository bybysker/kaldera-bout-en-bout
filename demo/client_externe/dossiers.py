"""Dossiers de démonstration, au format du courtier.

**Données entièrement fictives.** Noms, adresses, IBAN et numéros sont inventés pour la
démonstration ; aucun ne correspond à une personne ou à un compte réels.

Trois dossiers qui mènent chacun à une issue différente, pour que la démonstration montre
quelque chose plutôt que de répéter le même parcours.
"""

from __future__ import annotations

from typing import Any

DOSSIERS: list[dict[str, Any]] = [
    {
        "id_dossier": "CAB-26-7001",
        "intitule": "Dégât des eaux, dossier complet",
        "attendu": "acceptée, sans contrôle anti-fraude",
        # --- ce que le courtier garde pour lui
        "conseiller": "M. Berthier",
        "agence": "Lyon Part-Dieu",
        "taux_commission": 0.12,
        "notes_internes": "Client fidèle, aucun litige. Relance commerciale prévue en mars.",
        "segment_commercial": "premium",
        "valeur_client_annuelle": 1840.0,
        "dernier_contact": "2026-07-02",
        # --- ce qu'il transmet
        "client": {
            "identifiant": "CLI-70011",
            "nom": "Vasseur",
            "prenom": "Camille",
            "courriel": "camille.vasseur@exemple.fr",
            "telephone": "0611223344",
            "iban": "FR7630004000031234567890143",
            "adresse": "8 rue de la Guillotière",
            "code_postal": "69007",
            "sinistres_recents": 0,
        },
        "police": {
            "numero": "POL-70011-C",
            "formule": "confort",
            "effet": "2023-04-01",
            "en_vigueur": True,
            "primes_reglees": True,
        },
        "evenement": {
            "nature": "degat_des_eaux",
            "survenu_le": "2026-09-12",
            "declare_le": "2026-09-14",
            "estimation_client": 1400.0,
            "recit": "Fuite au niveau du ballon d'eau chaude, parquet du couloir gondolé.",
        },
        "justificatifs": [
            {"categorie": "facture", "exploitable": True, "valeur": 1400.0},
            {"categorie": "photo", "exploitable": True},
        ],
    },
    {
        "id_dossier": "CAB-26-7002",
        "intitule": "Incendie sur contrat récent, montant élevé",
        "attendu": "contrôle anti-fraude déclenché",
        "conseiller": "Mme Olivero",
        "agence": "Marseille Prado",
        "taux_commission": 0.15,
        "notes_internes": "Souscription récente via comparateur. Vigilance habituelle.",
        "segment_commercial": "standard",
        "valeur_client_annuelle": 620.0,
        "dernier_contact": "2026-08-30",
        "client": {
            "identifiant": "CLI-70022",
            "nom": "Nadeau",
            "prenom": "Dominique",
            "courriel": "d.nadeau@exemple.fr",
            "telephone": "0755667788",
            "iban": "FR7612548029981234567890161",
            "adresse": "140 avenue du Prado",
            "code_postal": "13008",
            "sinistres_recents": 1,
        },
        "police": {
            "numero": "POL-70022-P",
            "formule": "premium",
            "effet": "2026-07-20",
            "en_vigueur": True,
            "primes_reglees": True,
        },
        "evenement": {
            "nature": "incendie",
            "survenu_le": "2026-09-28",
            "declare_le": "2026-09-30",
            "estimation_client": 7800.0,
            "recit": "Départ de feu dans le garage, matériel de bricolage détruit.",
        },
        "justificatifs": [
            {"categorie": "facture", "exploitable": True, "valeur": 7800.0},
            {"categorie": "photo", "exploitable": True},
        ],
    },
    {
        "id_dossier": "CAB-26-7003",
        "intitule": "Vol, dépôt de plainte manquant",
        "attendu": "escalade gestionnaire, sans arrêt",
        "conseiller": "M. Berthier",
        "agence": "Lyon Part-Dieu",
        "taux_commission": 0.12,
        "notes_internes": "Client a indiqué devoir repasser au commissariat.",
        "segment_commercial": "standard",
        "valeur_client_annuelle": 410.0,
        "dernier_contact": "2026-10-01",
        "client": {
            "identifiant": "CLI-70033",
            "nom": "Lambrecht",
            "prenom": "Sacha",
            "courriel": "sacha.lambrecht@exemple.fr",
            "telephone": "0622334455",
            "iban": "FR7610096000301234567890125",
            "adresse": "3 place Bellecour",
            "code_postal": "69002",
            "sinistres_recents": 0,
        },
        "police": {
            "numero": "POL-70033-C",
            "formule": "confort",
            "effet": "2022-11-05",
            "en_vigueur": True,
            "primes_reglees": True,
        },
        "evenement": {
            "nature": "vol",
            "survenu_le": "2026-10-03",
            "declare_le": "2026-10-05",
            "estimation_client": 950.0,
            "recit": "Effraction par la fenêtre de la cuisine, ordinateur portable emporté.",
        },
        "justificatifs": [
            {"categorie": "facture", "exploitable": True, "valeur": 950.0},
        ],
    },
]


def par_identifiant(identifiant: str) -> dict[str, Any]:
    (trouve,) = [d for d in DOSSIERS if d["id_dossier"] == identifiant]
    return trouve
