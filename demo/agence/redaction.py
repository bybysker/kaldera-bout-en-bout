"""Les écrits que produit l'agence : un courrier pour l'assuré, une fiche pour le gestionnaire.

La plateforme rend une **fiche de décision** : une issue, un motif, une file. C'est ce dont un
système d'information a besoin. Ce n'est pas ce qu'on envoie à quelqu'un dont la salle de bain a
été inondée, ni ce qui permet à un gestionnaire de reprendre un dossier qu'il n'a jamais vu.

Ce module traduit l'une en l'autre. Il ne décide de rien : il met en mots ce que la plateforme a
décidé.

---

**Par gabarit, et pas autrement** (décision `D9`). Deux assurés dans la même situation doivent
recevoir le même courrier ; le même dossier relu six mois plus tard doit donner le même texte.
Un modèle de langage produirait des formulations plus naturelles et des résultats non
reproductibles — pour un courrier qui engage un assureur, c'est le mauvais échange.

**Ces documents portent des données personnelles**, et c'est normal : ils sont destinés à
l'assuré ou au gestionnaire qui le suit. Ils ne doivent jamais être journalisés.
"""

from __future__ import annotations

from datetime import date
from typing import Any

#: Ce qu'un assuré doit comprendre, par motif produit par la plateforme.
#: La clé est le début du motif ; les gabarits de `regles/issues.py` sont déterministes.
EXPLICATIONS: tuple[tuple[str, str], ...] = (
    (
        "Demande non éligible",
        "Après examen de votre contrat, cette demande ne peut pas être prise en charge.",
    ),
    (
        "Pièces manquantes",
        "Il nous manque une ou plusieurs pièces pour instruire votre demande.",
    ),
    (
        "Dommage inférieur",
        "Le montant des dommages retenus ne dépasse pas la franchise prévue à votre contrat. "
        "Aucun remboursement ne peut donc être versé.",
    ),
    (
        "Contrôle renforcé",
        "Votre demande fait l'objet d'un examen complémentaire par l'un de nos gestionnaires.",
    ),
    (
        "Suspicion de fraude",
        "Votre demande fait l'objet d'un examen approfondi avant toute décision.",
    ),
    (
        "Contrôle anti-fraude manuel",
        "Votre demande fait l'objet d'un examen complémentaire avant toute décision.",
    ),
    (
        "Seuil de délégation",
        "En raison de son montant, votre demande est soumise à la validation d'un gestionnaire.",
    ),
    (
        "Remboursement accordé",
        "Votre demande est acceptée.",
    ),
    (
        "Pièces illisibles",
        "Les pièces reçues ne nous permettent pas d'instruire votre demande.",
    ),
    (
        "Traitement interrompu",
        "Votre demande nécessite une reprise par l'un de nos gestionnaires.",
    ),
)

#: Ce que le gestionnaire doit faire, selon la file.
CONSIGNES: dict[str, str] = {
    "gestionnaire": "Reprendre l'instruction et statuer.",
    "cellule_fraude": "Contrôle approfondi avant toute décision. Ne pas contacter l'assuré.",
}

DELAI_RECLAMATION_JOURS = 60


def explication(motif: str) -> str:
    """La phrase destinée à l'assuré, déduite du motif technique."""
    for debut, texte in EXPLICATIONS:
        if motif.startswith(debut):
            return texte
    return "Votre demande est en cours d'examen."


def courrier_assure(
    fiche: dict[str, Any], demande: dict[str, Any], aujourdhui: date | None = None
) -> str:
    """Le courrier adressé à l'assuré.

    Il dit ce qui a été décidé et ce qu'il peut faire ensuite. Il ne dit **pas** par quel chemin
    la décision a été prise : ni les agents, ni les bornes, ni l'avis du partenaire. Un assuré
    n'a pas à connaître le fonctionnement interne de l'assureur pour comprendre sa situation.
    """
    aujourdhui = aujourdhui or date.today()
    assure = demande["assure"]
    sinistre = demande["sinistre"]
    lignes = [
        f"{assure['prenom']} {assure['nom']}",
        assure["adresse"],
        f"{assure['code_postal']}",
        "",
        f"Le {aujourdhui.strftime('%d/%m/%Y')}",
        "",
        f"Objet : votre déclaration de sinistre {fiche['reference']}",
        "",
        f"Madame, Monsieur {assure['nom']},",
        "",
        f"Vous avez déclaré le {_date_lisible(sinistre['date_survenance'])} un sinistre de type "
        f"« {sinistre['type'].replace('_', ' ')} », pour un montant de "
        f"{sinistre['montant_declare']:.2f} €.",
        "",
        explication(fiche["motif"]),
        "",
    ]

    montant = fiche.get("montant_rembourse")
    if fiche.get("decision") == "acceptee" and montant:
        lignes += [
            f"Un virement de {montant:.2f} € sera effectué sur votre compte sous dix jours ouvrés.",
            "",
            "Ce montant tient compte de la franchise et du plafond prévus à votre contrat.",
            "",
        ]
    elif fiche.get("decision") == "refusee":
        lignes += [
            "Aucun versement ne sera effectué au titre de cette déclaration.",
            "",
            f"Si vous estimez que cette décision ne tient pas compte d'un élément, vous "
            f"disposez de {DELAI_RECLAMATION_JOURS} jours pour nous écrire en précisant la "
            "référence ci-dessus.",
            "",
        ]
    else:
        lignes += [
            "Un gestionnaire reprend votre dossier. Vous recevrez une réponse dans les "
            "meilleurs délais, sans démarche de votre part.",
            "",
        ]
        if "Pièces manquantes" in fiche["motif"]:
            lignes[-1] = (
                "Vous pouvez déposer les pièces attendues depuis votre espace en ligne. "
                "Votre dossier reprendra dès réception."
            )
            lignes += [""]

    lignes += [
        "Nous restons à votre disposition.",
        "",
        "Le service indemnisation",
        "Kaldera Assurances",
    ]
    return "\n".join(lignes)


def fiche_gestionnaire(
    fiche: dict[str, Any], demande: dict[str, Any], aujourdhui: date | None = None
) -> str:
    """La fiche remise au gestionnaire qui reprend le dossier.

    Elle répond à trois questions, dans cet ordre : **de quoi s'agit-il**, **pourquoi
    m'arrive-t-il**, **que dois-je faire**. Tout le reste est du contexte, et vient après.
    """
    aujourdhui = aujourdhui or date.today()
    assure, contrat, sinistre = demande["assure"], demande["contrat"], demande["sinistre"]
    anciennete = _jours(contrat["date_souscription"], sinistre["date_survenance"])
    avis = fiche.get("avis_fraude")

    lignes = [
        f"DOSSIER {fiche['reference']} — à reprendre",
        f"Reçu le {aujourdhui.strftime('%d/%m/%Y')} · file : {fiche.get('file') or '—'}",
        "",
        "POURQUOI CE DOSSIER VOUS ARRIVE",
        f"  {fiche['motif']}",
        "",
        "À FAIRE",
        f"  {CONSIGNES.get(fiche.get('file') or '', 'Statuer sur ce dossier.')}",
        "",
        "L'ASSURÉ",
        f"  {assure['prenom']} {assure['nom']} — client {assure['id_client']}",
        f"  {assure['adresse']}, {assure['code_postal']}",
        f"  {assure['email']} · {assure['telephone']}",
        "",
        "LE CONTRAT",
        f"  {contrat['numero']} — formule {contrat['formule']}, statut {contrat['statut']}",
        f"  Souscrit le {_date_lisible(contrat['date_souscription'])}"
        f" ({anciennete} jours avant le sinistre)",
        f"  Cotisations à jour : {'oui' if contrat['cotisations_a_jour'] else 'NON'}",
        "",
        "LE SINISTRE",
        f"  {sinistre['type'].replace('_', ' ')} survenu le "
        f"{_date_lisible(sinistre['date_survenance'])},"
        f" déclaré le {_date_lisible(sinistre['date_declaration'])}",
        f"  Montant déclaré : {sinistre['montant_declare']:.2f} €",
        f"  Sinistres sur 12 mois : {demande.get('historique', {}).get('sinistres_12_mois', 0)}",
    ]

    description = sinistre.get("description")
    if description:
        lignes += [f"  Récit de l'assuré : « {description} »"]

    pieces = demande.get("pieces") or []
    lignes += ["", "LES PIÈCES"]
    if pieces:
        for piece in pieces:
            montant = f" — {piece['montant']:.2f} €" if piece.get("montant") else ""
            etat = "lisible" if piece.get("lisible") else "ILLISIBLE"
            lignes += [f"  {piece['type']} · {etat}{montant}"]
    else:
        lignes += ["  aucune"]

    if avis:
        lignes += [
            "",
            "AVIS ANTI-FRAUDE DU PARTENAIRE",
            f"  niveau {avis.get('niveau')} · score {avis.get('score')}",
            "  Cet avis est consultatif : il ne vous lie pas.",
        ]
    elif fiche.get("mode_degrade"):
        lignes += [
            "",
            "AVIS ANTI-FRAUDE",
            "  NON OBTENU — le service du partenaire n'a pas répondu, ou sa réponse a été",
            "  écartée. Ce dossier n'a donc bénéficié d'aucun contrôle automatique.",
        ]

    if fiche.get("arret"):
        lignes += [
            "",
            "TRAITEMENT INTERROMPU",
            f"  Borne atteinte : {fiche['arret']['borne']}",
            "  Le dossier n'a pas suivi son parcours complet. À instruire manuellement.",
        ]

    return "\n".join(lignes)


def _date_lisible(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def _jours(debut: str, fin: str) -> int:
    return (date.fromisoformat(fin) - date.fromisoformat(debut)).days
