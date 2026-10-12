
# Où les modèles entrent dans le système, et selon quelle règle

Brief Kaldera · Phase DÉVELOPPEMENT · 9 octobre 2026

Le formateur a ouvert le brief : un modèle de langage peut être intégré « à différents endroits »
du système agentique. Ce document répond à la question telle qu'elle se pose — **à quel degré, à
quel endroit, et sous quelles contraintes** — en s'appuyant sur des mesures plutôt que sur des
préférences.

Il remplace la décision `D25`, qui excluait tout modèle du système.

---

## En bref

- **Une règle unique** place les cinq usages : *un modèle peut informer un humain, jamais décider
  à sa place dans le temps contraint.*
- **Trois cercles** : jamais dans le chemin de décision synchrone · oui en asynchrone · oui hors
  système.
- **Ce qui exclut le premier cercle n'est pas une opinion** : 2,5 à 35,5 secondes mesurées
  contre un engagement de 10 secondes, et jusqu'à 2,6 entre deux appels sur le même dossier.
- **Sept garde-fous**, tous testés, dont l'interdiction d'importer la revue — ou la fabrique
  de modèle — depuis un agent.

---

## 1 · La mesure, d'abord

Tout ce qui suit découle de mesures prises sur ce poste, avec Kimi-K2.6 via Azure.

Protocole : **dix appels par usage** — cinq dossiers distincts, répétés deux fois. Quarante
appels, quarante exploitables.

| Usage                            | n   | min    | médiane | p90     | max     |
| -------------------------------- | --- | ------ | ------- | ------- | ------- |
| Prise de déclaration             | 10  | 2,51 s | 5,09 s  | 9,36 s  | 12,71 s |
| Revue de fond, cohérence incluse | 10  | 5,56 s | 8,97 s  | 11,64 s | 12,76 s |
| Synthèse de dossier              | 10  | 7,68 s | 12,49 s | 22,25 s | 23,14 s |
| Aide à la décision               | 10  | 8,07 s | 18,35 s | 29,60 s | 35,49 s |

| Mesure                                       | Valeur            |
| -------------------------------------------- | ----------------- |
| Les cinq agents, une demande complète        | **0,04 ms**       |
| Écart entre deux appels sur le même dossier  | **jusqu'à 2,6**   |
| Jetons de sortie pour ~400 caractères utiles | **2 200 à 4 400** |
| Formulations identiques sur 5 appels         | **0**             |

**L'engagement de service est de 10 secondes par demande** (specs §12). **Dix-neuf appels
sur quarante le dépassent à eux seuls** — un sur dix pour la prise de déclaration, neuf sur dix
pour l'aide à la décision. Le pire en consomme trois fois et demie le budget.

Le rapport entre le chemin de décision et un appel de modèle est de **1 à 100 000**. Ce n'est pas
une marge à optimiser, c'est un changement de nature.

---

## 2 · La règle

> **Un modèle peut informer un humain, jamais décider à sa place dans le temps contraint.**

Elle tient en une phrase parce qu'elle doit pouvoir être opposée à chaque ajout futur. Un usage
qui ne s'y range pas ne se justifie pas « pour cette fois ».

### Les trois cercles

| Cercle                | Ce qu'il recouvre                           | Pourquoi                                                                                            |
| --------------------- | ------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Jamais**            | Le chemin de décision synchrone             | La latence mangerait l'engagement, et le non-déterminisme rendrait les tests d'acceptance instables |
| **Oui, asynchrone**   | Après la décision, sur ce qui est déjà clos | Le budget de temps ne s'applique plus : la fiche est partie, l'assuré est servi                     |
| **Oui, hors système** | Au service d'un humain qui décide           | Aucune contrainte de service, puisque rien du service rendu n'en dépend                             |

---

## 3 · Les cinq usages

| Usage                    | Cercle       | Où                      | Latence        | Ce qu'il décide                                 |
| ------------------------ | ------------ | ----------------------- | -------------- | ----------------------------------------------- |
| **Prise de déclaration** | hors système | amont, chez le courtier | médiane 5,1 s  | rien — l'opérateur relit avant de déposer       |
| **Revue de fond**        | asynchrone   | après la décision       | médiane 9,0 s  | rien — il signale, un humain tranche            |
| **Cohérence des pièces** | asynchrone   | dans la revue           | incluse        | rien — consultatif, hors du contrôle des pièces |
| **Synthèse de dossier**  | hors système | espace gestionnaire     | médiane 12,5 s | rien — s'ajoute à la fiche                      |
| **Aide à la décision**   | hors système | espace gestionnaire     | médiane 18,4 s | rien — rien n'est pré-sélectionné               |

### Ce que chacun apporte

**La prise de déclaration.** Un assuré qui appelle raconte ; il ne remplit pas un formulaire.
Mesuré sur onze récits : les règles obtiennent 14 champs justes sur 15, le modèle 15 sur 15.
L'unique écart est celui où les règles refusent de trancher — *« on m'a cambriolé, effraction par
la fenêtre »* — et où le modèle répond **vol**, à raison.

**La revue de fond.** Un sixième agent relit une décision close. Sur quatre dossiers volontairement
cassés, **quatre détections sur quatre**, avec des remarques précises : *« décision acceptée
incompatible avec le motif d'inéligibilité »*, *« le libellé est incompréhensible pour un assuré
non spécialiste »*.

**La cohérence des pièces.** C'est la troisième frontière ambiguë du chantier 1, restée ouverte
parce que la spécification emploie le mot sans le définir. La question est désormais **posée**,
mais son avis **n'entre dans aucune décision**. C'est ce qui permet de l'explorer sans attendre le
métier : tant qu'aucune décision n'en dépend, aucun assuré ne subit un jugement que personne ne
saurait lui expliquer. Le jour où le critère existera, la question sera déjà mesurée.

**La synthèse.** Trois lignes là où la fiche gestionnaire en fait quarante. Elle s'ajoute, elle ne
remplace pas : ce qui fait foi reste dessous.

**L'aide à la décision.** Une suite proposée, sa raison, et **ce qui pourrait la contredire**. Ce
dernier champ est obligatoire : un conseil qui ne dit pas ce qui lui résiste se fait suivre sans
être pesé. Une suggestion sans contre-argument est écartée.

---

## 4 · Les sept garde-fous

Tous testés. Ce sont eux qui rendent la doctrine opposable plutôt que déclarative.

|       | Garde-fou                                                       | Comment il tient                                                                                                                  |
| ----- | --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **1** | Aucun agent ni l'orchestration n'importe la revue               | Un test lit les imports de tout le paquet. Sans lui, « hors du chemin » ne serait qu'une intention                                |
| **2** | Aucun avis ne modifie une fiche                                 | La fiche est comparée avant et après                                                                                              |
| **3** | Un modèle qui tombe rend « indisponible »                       | Jamais une erreur, jamais un blocage                                                                                              |
| **4** | Toute remarque évoquant la fraude est écartée                   | *« L'avis de fraude est émis par le partenaire, jamais en interne »* — specs §2. Les remarques écartées sont comptées             |
| **5** | Le récit de l'assuré ne part chez aucun modèle                  | Tranché par le métier le 12 octobre 2026. Le drapeau qui pouvait l'ouvrir est retiré, et un test garde qu'il ne revienne pas      |
| **6** | Les tests qui appellent un modèle réel sont écartés de la suite | Elle reste reproductible : `make modele` les lance à part                                                                         |
| **7** | Un seul endroit sait construire un client de modèle             | `kaldera.llm`, qu'aucun agent n'importe. Les trois copies précédentes avaient déjà divergé sur les jetons et le délai *(`AJ-10`)* |

### Sur le cinquième

Un modèle hébergé est un tiers. Le contrat anti-fraude interdit déjà la description libre
« sous quelque forme que ce soit » ; savoir si un modèle relève de la même règle **n'est pas une
question technique**, elle engage la conformité.

Tant qu'elle n'est pas tranchée, c'est la règle la plus stricte qui s'applique. Une donnée
personnelle qui part parce que personne n'a dit non est une donnée qui part **sans décision**.

Conséquence assumée : sans le récit, la cohérence des pièces ne se juge que sur la **structure** —
types de pièces et montants au regard de la nature du sinistre. C'est moins, et c'est dit.

---

## 5 · Ce qu'on n'a pas fait, et pourquoi

| Usage écarté                         | Raison                                                                                                                                           |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Rédiger les motifs**               | `D9` tient : deux assurés dans la même situation doivent recevoir le même texte. Mesuré, le modèle produit **cinq formulations sur cinq appels** |
| **Décider de l'avis de fraude**      | Interdit par les spécifications §2. Indépassable                                                                                                 |
| **Contrôler les pièces**             | Le métier n'a pas défini le critère. Un modèle qui comble un trou de spécification ne le résout pas : il le rend opaque                          |
| **Juger la lisibilité d'un fichier** | Demanderait un modèle multimodal, donc d'envoyer des photos d'intérieur à un tiers. `EX-3` s'y oppose                                            |
| **Router les étapes**                | Le plan est une table. Un modèle y introduirait du non-déterminisme sur le chemin lui-même                                                       |

---

## 6 · Les décisions

> **`D31` · Un modèle peut informer un humain, jamais décider à sa place dans le temps
> contraint.** Trois cercles en découlent : jamais dans le chemin de décision synchrone, oui en
> asynchrone après la décision, oui hors du système au service d'un humain.
>
> *Remplace `D25`, qui excluait tout modèle. La mesure a montré que l'exclusion portait sur le
> chemin synchrone, pas sur le système entier.*

> **`D32` · Le récit de l'assuré ne part chez aucun modèle hébergé.** Tranché par le métier le
> 12 octobre 2026. Le drapeau qui pouvait l'ouvrir est retiré, et un test garde qu'il ne
> revienne pas.
>
> *Jusqu'à cette date, l'architecture tenait les deux réponses, fermée par défaut. C'est ce qui
> a permis d'attendre la décision sans la préempter.*

> **`D33` · Une suggestion sans contre-argument est écartée.** Un conseil qui ne dit pas ce qui
> lui résiste se fait suivre sans être pesé, et la décision engage un assuré.

> **`D34` · Aucune suite n'est pré-sélectionnée dans l'interface après un avis du modèle.** Un
> bouton déjà coché est une décision prise par la machine, même validée d'un clic.

---

## 7 · Ce qui rouvrirait le dossier

- **Un modèle nettement plus rapide.** Si un appel descendait sous 500 ms de façon stable, le
  premier cercle mériterait d'être reconsidéré — pour la latence seulement : le déterminisme
  resterait un obstacle.
- **Un critère de cohérence défini par le métier.** L'avis consultatif deviendrait alors
  exploitable, avec un seuil calibré et consigné.
- **Des pièces qui portent de quoi juger leur cohérence.** Une pièce ne porte aujourd'hui que
  son type, sa lisibilité et son montant. Un intitulé, une date ou une nature de prestation
  rendraient la question mesurable au lieu de rester une appréciation.

**Refermé le 12 octobre 2026** : le métier a répondu sur le récit — il ne part pas *(`D32`)*.

Un test garde la première : si un appel réel descendait sous 500 ms, il échouerait — et le message
dirait qu'il faut rouvrir cette décision.

---

*Les mesures sont reproductibles par `make modele`. Les usages se voient dans la démonstration,
onglet **Espace technique → Les modèles**.*
