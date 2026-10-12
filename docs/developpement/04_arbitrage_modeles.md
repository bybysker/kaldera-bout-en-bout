# Arbitrage · faut-il un modèle de langage dans le système ?

Brief Kaldera · Phase DÉVELOPPEMENT · 7 octobre 2026

Deux modèles de décision typée ont été examinés pour un usage dans Kaldera : **Jev** (TypeSafe) et
**LAYA** (Convai Innovations). Ce document consigne ce qui a été vérifié, où ils pourraient
s'insérer, et la décision prise.

---

> **Document dépassé sur un point, le 9 octobre.** Le formateur a ouvert le brief : un modèle
> peut être intégré au système. `D25` reste vrai **sur le chemin de décision synchrone** — la
> mesure l'a même confirmé — mais il excluait le système entier, ce qui allait trop loin. La
> doctrine qui le remplace est dans [`10_doctrine_des_modeles.md`](10_doctrine_des_modeles.md),
> décision `D31`.

## La décision

> **D25 · Aucun modèle n'intervient dans le chemin de décision d'une demande.**
> Le système reste entièrement déterministe. L'arbitrage est consigné ici plutôt que dans le code.

> **D26 · Un usage hors production reste ouvert**, dans le plan d'épreuve uniquement, et seulement
> une fois le chantier 2 vert.

---

## 1 · Ce que sont ces deux outils

Même concept : des modèles qui répondent à des **questions typées** sur un état et rendent une
valeur structurée. Trois primitives communes — `Choice` (choisir dans une liste), `Score` (noter
sur une grille), `Noul` (cette affirmation est-elle vraie, de 0 à 1). **Ni l'un ni l'autre ne génère
de texte.**

|           | Jev · TypeSafe                     | LAYA · Convai Innovations                           |
| --------- | ---------------------------------- | --------------------------------------------------- |
| Modèle    | propriétaire, via API              | poids ouverts, **Apache 2.0**                       |
| Taille    | non publiée                        | 421 M (anglais) · 322 M (multilingue, 100+ langues) |
| Base      | non publiée                        | ModernBERT-large / mmBERT-base                      |
| Exécution | cloud (API TypeSafe ou OpenRouter) | **locale**                                          |
| Latence   | 70–500 ms *annoncés par l'éditeur* | ~33 ms annoncés · 13,4 ms P50 mesurés sur M3 Max    |
| Coût      | 0,042 $ / M tokens en entrée       | nul                                                 |
| Données   | **partent chez un tiers**          | **ne sortent pas**                                  |

**Niveau de vérification.** Pour LAYA, les éléments viennent de la carte de modèle et du dépôt du
portage MLX. Pour Jev, la documentation officielle décrit les primitives, mais **le prix et la
latence viennent de sources secondaires** et la latence est donnée par l'éditeur sans reproduction
indépendante. À remesurer si l'outil était retenu.

**Un obstacle matériel.** `laya-mlx` exige macOS 14 et une puce Apple Silicon ; le poste de
développement est sous Windows 11. Les chiffres de latence ci-dessus proviennent donc d'une
machine que nous n'avons pas. Les poids restent utilisables par l'écosystème habituel, mais leur
comportement sur la configuration réelle n'a **pas** été mesuré.

---

## 2 · Les trois endroits où ils n'ont pas leur place

Ces trois lignes viennent du métier, pas de la technique. **Aucun changement d'outil ne les
déplace.**

| Endroit                  | Pourquoi non                                                                                                                                                                                                                   |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **L'avis de fraude**     | Interdit par les spécifications, §2 : « l'avis de fraude est émis par le partenaire, jamais en interne ». C'est l'usage le plus tentant — un `Score` sur une grille de risque — et ce serait la faute la plus grave du dossier |
| **Le motif de la fiche** | C'est le seul endroit du système où un jugement serait utile, mais il demande de **rédiger un texte** pour un assuré. Ni Jev ni LAYA ne produisent de texte : l'outil ne correspond pas au besoin                              |
| **Les règles chiffrées** | Éligibilité, montants, indicateurs, seuils : ce sont des comparaisons. Un modèle probabiliste y coûterait le déterminisme, et rendrait les tests d'acceptance instables                                                        |

---

## 3 · Le seul endroit possible, et sa condition bloquante

**La « cohérence » des pièces avec la déclaration** — la troisième frontière ambiguë du chantier 1,
tranchée par `D3`.
La spécification emploie le mot sans jamais le définir ; nous avons réduit le contrôle au tableau
des pièces exigées, en signalant que le mot restait plus large.

Un `Noul` irait exactement là : *« cette facture est-elle cohérente avec la description du
sinistre ? »*.

**Trois conditions, et la première est bloquante :**

1. **Le métier doit d'abord donner un critère.** Mettre un modèle pour combler un trou de
   spécification ne résout rien : cela rend le trou opaque. On remplacerait une règle absente par
   un jugement qu'on ne saurait pas expliquer à un assuré.
2. **Le résultat reste consultatif** : il alimente le contrôle des pièces, ne décide jamais seul, et
   aucun test d'acceptance n'en dépend.
3. **Le seuil doit être calibré, pas estimé.** Un `Noul` rend une probabilité ; en tirer une
   décision demande un seuil. Or la carte de LAYA signale une **surconfiance initiale nécessitant
   un recalibrage**. Poser ce seuil à l'estime serait exactement le « réglage au doigt mouillé »
   que les critères de performance interdisent.

À quoi s'ajoutent deux limites annoncées par la carte de modèle, et qu'il faut connaître : les
questions de **score ordinal sont sa primitive la plus faible**, et les points de contrôle de base
sont « proches du hasard » sur son propre test de décisions typées — le choix de la version exacte
n'est donc pas un détail.

---

## 4 · Pourquoi nous n'y allons pas

**Les critères de performance n'en demandent aucun.** Tests d'acceptance qui passent · six
exigences démontrées · A2A conforme au contrat · mode dégradé qui préserve le service · bornes
justifiées par l'épreuve. Pas une ligne sur un modèle.

**Le risque est à sens unique.** Un modèle mal placé peut faire échouer des scénarios — non
-déterminisme, latence, seuil mal calibré. Il ne peut rien faire gagner sur la grille.

**La démonstration d'IA est déjà dans le sujet.** Le brief ne demande pas d'utiliser un modèle de
langage : il demande une équipe d'agents qui collabore avec **un agent externe appartenant à une
autre société**, selon un contrat A2A, avec un filtre de données et une validation des réponses.
C'est l'objet du chantier 2. Le partenaire anti-fraude *est* l'agent d'IA du système — nous n'avons
pas à en être le fournisseur.

**Et la conception l'avait déjà établi.** Le chantier 1 a montré, mesures à l'appui, que la
lisibilité d'une pièce est fournie comme un booléen, que la description libre n'est utilisée par
aucune règle, et que toutes les règles sont des comparaisons chiffrées. La décision `D9` en
découlait déjà : gabarit par défaut, rédaction assistée en option à mesurer.

---

## 5 · Si l'un des deux devait être retenu

**LAYA, sans hésitation.** Licence ouverte, exécution locale, aucune donnée qui sort, aucun coût par
appel. Il supprime la seule objection technique opposée à Jev : avec Jev, la description libre du
sinistre partirait chez un tiers — exactement le problème qu'`EX-3` pose pour le partenaire.

**Usage retenu si le temps le permet, et seulement après un chantier 2 vert** : un `Score` dans le
plan d'épreuve, sur une grille « ce motif est-il compréhensible par un assuré ? », appliqué aux
motifs produits par le gabarit. C'est un outil de contrôle, pas un composant : le
non-déterminisme n'y casse rien.

**Si malgré tout un usage en production était voulu** : la cohérence des pièces, derrière un drapeau
**désactivé par défaut**, avec un test prouvant que les 28 scénarios rendent le même résultat avec
et sans. La démonstration porterait alors autant sur la prudence que sur la technique.

---

## 6 · Ce qui ferait changer cette décision

- Le formateur indique explicitement attendre un modèle **dans** le système. L'objectif change
  alors, et doit être assumé comme tel : « branché pour la démonstration, à l'endroit le moins
  risqué », et non « le métier le réclamait ».
- Le métier fournit un **critère de cohérence** opérationnel. La condition bloquante tombe, et
  l'usage redevient défendable — avec un seuil calibré et consigné.

---

## 7 · Ce que cela entraîne

- [ ] **Poser au formateur la question du critère de « cohérence »** des pièces. La spécification
      emploie le mot sans le définir : c'est une lacune réelle, et la réponse tranche l'arbitrage
      ci-dessus.
- [ ] Ne rien brancher tant que le chantier 2 n'est pas vert.
- [ ] Si le temps le permet ensuite : le `Score` de contrôle des motifs, **hors du paquet
      `kaldera`**, dans l'outillage de test.
- [ ] Mesurer LAYA sur la configuration réelle avant tout engagement — les chiffres publiés
      viennent d'une machine différente.

---

*Sources consultées le 7 octobre 2026 :
[docs.typesafe.ai/introduction](https://docs.typesafe.ai/introduction) ·
[huggingface.co/convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya) ·
[github.com/mizorewww/laya-mlx](https://github.com/mizorewww/laya-mlx). Le prix et la latence de Jev
proviennent de sources secondaires et n'ont pas été vérifiés dans la documentation officielle.*
