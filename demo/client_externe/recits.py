"""Des déclarations telles qu'un assuré les formule au téléphone.

Chaque récit est choisi pour ce qu'il met à l'épreuve, et non pour illustrer une réussite. Les
plus utiles en soutenance sont ceux que l'extraction par règles **ne sait pas** traiter : ils
montrent ce qu'un modèle apporte, et où il n'apporte rien.

**Données entièrement fictives.** Aucun nom, aucune adresse, aucun montant ne correspond à une
personne ou à un dossier réels.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Recit:
    titre: str
    texte: str
    #: Ce que ce récit met à l'épreuve, dit en une ligne.
    eprouve: str


RECITS: tuple[Recit, ...] = (
    Recit(
        titre="Fuite — le cas simple",
        texte=(
            "Bonjour, j'ai eu une fuite sous l'évier samedi dernier, le parquet du couloir a "
            "gondolé. J'ai la facture du plombier, 1 400 euros, et j'ai pris des photos."
        ),
        eprouve="Le cas de référence : tout est dit, les deux extracteurs y arrivent.",
    ),
    Recit(
        titre="Incendie — date écrite en clair",
        texte=(
            "Un incendie s'est déclaré dans le garage le 28/09/2026. Les dégâts sont estimés à "
            "7 800 € par l'expert, j'ai la facture."
        ),
        eprouve="Une date au format français, et un montant au-dessus du seuil anti-fraude.",
    ),
    Recit(
        titre="Vol — deux natures évoquées",
        texte=(
            "On m'a cambriolé hier, effraction par la fenêtre de la cuisine. Ordinateur portable "
            "emporté, 950 euros. Je suis allé au commissariat déposer plainte."
        ),
        eprouve=(
            "Les règles ne tranchent pas — « cambriolé » et « fenêtre » évoquent deux natures — "
            "et préfèrent ne rien conclure. Le modèle répond « vol », et il a raison."
        ),
    ),
    Recit(
        titre="Dégât des eaux — tournure indirecte",
        texte=(
            "Le plafond de ma salle de bain s'est mis à couler après que le voisin du dessus a "
            "laissé sa baignoire déborder, c'était mardi. L'artisan a chiffré la remise en état "
            "à 1 200 euros."
        ),
        eprouve="Aucun mot-clé évident : ni « fuite », ni « dégât des eaux ». Les règles passent à côté.",
    ),
    Recit(
        titre="Bris de glace — nié puis affirmé",
        texte=(
            "Ce n'est pas un vol, rien n'a été emporté : la vitre du salon s'est brisée toute "
            "seule hier matin. Le vitrier demande 480 euros, voici son devis."
        ),
        eprouve="Une négation que les mots-clés ne voient pas : « vol » est présent dans le texte.",
    ),
    Recit(
        titre="Montant écrit en lettres",
        texte=(
            "Départ de feu dans la cuisine le 2 octobre 2026, les réparations sont estimées à "
            "deux mille cinq cents euros. J'ai la facture et des photos."
        ),
        eprouve="Un montant qu'aucune expression régulière ne lit, et une date en toutes lettres.",
    ),
    Recit(
        titre="Tout dans le désordre",
        texte=(
            "Facture de 3 200 euros pour le remplacement du parquet, suite à la fuite de la "
            "machine à laver survenue le 05/10/2026."
        ),
        eprouve="La conséquence avant la cause : l'ordre des informations ne suit pas le formulaire.",
    ),
    Recit(
        titre="Vol avec un délai dépassé",
        texte=(
            "Je me suis fait cambrioler le 15 septembre 2026, j'ai tardé à vous prévenir. "
            "Télévision et bijoux, 2 300 euros au total. J'ai le dépôt de plainte."
        ),
        eprouve=(
            "Un vol déclaré bien au-delà des cinq jours : l'extraction réussit, et c'est "
            "l'éligibilité qui refusera ensuite. La saisie ne juge pas."
        ),
    ),
    Recit(
        titre="L'assuré en dit trop",
        texte=(
            "Bonjour, c'est Camille Vasseur, 8 rue de la Guillotière à Lyon, mon IBAN est le "
            "FR76 3000 4000 0312 3456 7890 143. Dégât des eaux hier dans la cuisine, "
            "900 euros de réparations, j'ai la facture et des photos."
        ),
        eprouve=(
            "Nom, adresse et IBAN dans le récit. L'extraction ne les retient pas — et même "
            "s'ils entraient dans la demande, ils ne franchiraient pas la passerelle."
        ),
    ),
    Recit(
        titre="Rien de précis",
        texte=(
            "Il y a eu un problème chez moi la semaine dernière, je ne sais pas encore combien "
            "ça va coûter ni ce qu'en dira l'artisan."
        ),
        eprouve=(
            "Trois champs indéterminés. Une information absente coûte moins cher qu'une "
            "information fausse : rien ne doit être deviné."
        ),
    ),
    Recit(
        titre="Deux sinistres dans un même appel",
        texte=(
            "J'ai deux choses à déclarer : une fuite dans la cuisine lundi, 600 euros, et la "
            "vitre du garage cassée le même jour, 300 euros."
        ),
        eprouve=(
            "Une déclaration pour deux sinistres. Ni les règles ni le modèle ne savent la "
            "scinder — c'est à l'opérateur de le voir, et l'interface doit le lui permettre."
        ),
    ),
)


def par_titre(titre: str) -> Recit:
    (trouve,) = [r for r in RECITS if r.titre == titre]
    return trouve
