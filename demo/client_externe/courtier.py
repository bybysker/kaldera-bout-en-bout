"""Le dossier tel qu'un courtier le détient, et sa traduction vers le format Kaldera.

Un courtier en assurance n'a pas le format de Kaldera. Il a le sien : son identifiant de dossier,
son conseiller, son barème de commission, ses notes internes, et l'historique commercial du
client. Déposer une demande, pour lui, c'est **traduire** — et donc choisir ce qu'il transmet.

C'est le premier des trois niveaux de minimisation que ce système met en scène :

```
    le courtier détient  ──►  Kaldera reçoit  ──►  le partenaire reçoit
      ~20 champs                9 champs            7 champs
      dont commission,          dont nom, IBAN,     aucune donnée
      notes internes,           description libre   personnelle
      conseiller
```

Rien ici n'appartient au paquet ``kaldera`` : ce client est un système tiers, et il n'a accès
qu'à la porte publique — `traiter_demande`, `traiter_lot`, `bornes`.
"""

from __future__ import annotations

from datetime import date
from typing import Any

#: Ce que le courtier détient et que Kaldera n'a **pas** à recevoir.
CHAMPS_INTERNES = (
    "conseiller",
    "agence",
    "taux_commission",
    "notes_internes",
    "segment_commercial",
    "valeur_client_annuelle",
    "dernier_contact",
)

#: Les champs que la plateforme Kaldera attend (specs_metier.md §3).
CHAMPS_KALDERA = (
    "reference",
    "assure",
    "contrat",
    "sinistre",
    "pieces",
    "historique",
    "espace_assure",
)


class TraductionImpossible(ValueError):
    """Le dossier du courtier ne porte pas de quoi construire une demande."""


def traduire(dossier: dict[str, Any]) -> dict[str, Any]:
    """Traduit un dossier courtier en demande Kaldera, **en partant de rien**.

    Même principe que la charge envoyée au partenaire : on écrit les champs un par un plutôt que
    de filtrer. Un champ ajouté demain au format du courtier ne partira pas tout seul.
    """
    manquants = [cle for cle in ("client", "police", "evenement") if cle not in dossier]
    if manquants:
        raise TraductionImpossible(f"dossier incomplet : {', '.join(manquants)}")

    client, police, evenement = dossier["client"], dossier["police"], dossier["evenement"]
    return {
        "reference": reference_kaldera(dossier["id_dossier"]),
        "assure": {
            "id_client": client["identifiant"],
            "nom": client["nom"],
            "prenom": client["prenom"],
            "email": client["courriel"],
            "telephone": client["telephone"],
            "iban": client["iban"],
            "adresse": client["adresse"],
            "code_postal": client["code_postal"],
        },
        "contrat": {
            "numero": police["numero"],
            "formule": police["formule"],
            "date_souscription": police["effet"],
            "statut": "actif" if police["en_vigueur"] else "resilie",
            "cotisations_a_jour": bool(police["primes_reglees"]),
        },
        "sinistre": {
            "type": evenement["nature"],
            "date_survenance": evenement["survenu_le"],
            "date_declaration": evenement.get("declare_le") or date.today().isoformat(),
            "montant_declare": float(evenement["estimation_client"]),
            "description": evenement.get("recit", ""),
        },
        "pieces": [
            {
                "type": piece["categorie"],
                "lisible": bool(piece.get("exploitable", True)),
                "montant": piece.get("valeur"),
            }
            for piece in dossier.get("justificatifs", [])
        ],
        "historique": {"sinistres_12_mois": int(client.get("sinistres_recents", 0))},
        "espace_assure": {
            "depots": [
                {
                    "type": piece["categorie"],
                    "lisible": bool(piece.get("exploitable", True)),
                    "montant": piece.get("valeur"),
                }
                for piece in dossier.get("justificatifs_en_attente", [])
            ]
        },
    }


def reference_kaldera(identifiant_courtier: str) -> str:
    """Le courtier numérote à sa façon ; Kaldera attend `KAL-AA-NNNN`.

    Le format est imposé par le contrat partenaire, qui le valide par expression régulière.
    """
    chiffres = "".join(c for c in identifiant_courtier if c.isdigit())
    if len(chiffres) < 6:
        raise TraductionImpossible(
            f"« {identifiant_courtier} » ne porte pas assez de chiffres pour une référence Kaldera"
        )
    return f"KAL-{chiffres[:2]}-{chiffres[2:6]}"


def retenu_par_le_courtier(dossier: dict[str, Any]) -> dict[str, Any]:
    """Ce que le courtier garde pour lui. Sert à le montrer, pas à le transmettre."""
    return {cle: dossier[cle] for cle in CHAMPS_INTERNES if cle in dossier}
