# Revue d'architecture, revue de code, auto-évaluation

Brief Kaldera · Phase DÉVELOPPEMENT · 9 octobre 2026

Trois exercices menés sur le code réel, pas sur l'impression qu'il laisse. La revue a trouvé six
défauts ; ils sont corrigés et consignés.

---

## En bref

- **La carte des agents et le plan de routage se déroulent sur le code**, sans traduction : ils
  s'affichent en douze lignes de Python.
- **La revue de code a trouvé six défauts réels**, dont deux dans mes propres tests.
- **La couverture passe de 90 % à 96 %**, et la ligne de commande de **0 %** à couverte.
- **623 tests reproductibles**, plus 5 à la demande qui notent un modèle de langage.
- **Deux dettes anciennes sont soldées** : les garde-fous jamais atteints, et la ligne de commande
  jamais testée.

---

## 1 · Revue d'architecture

### La carte des agents, lue sur le code

```
$ uv run python -c "from kaldera.orchestration import repartiteur; ..."

etape         agent         section
eligibilite   eligibilite   eligibilite
pieces        pieces        pieces
estimation    estimation    estimation
antifraude    antifraude    avis_fraude
decision      decision      issue
```

C'est le tableau du dossier de conception, sans un mot de différence. Un agent, un rôle, une
section — et le répartiteur n'y figure pas, parce qu'il n'est l'auteur de rien.

### Le plan conditionnel, lu sur le code

```
plan conditionnel : 10 transitions
  eligibilite  + non_recevable    -> decision
  eligibilite  + recevable        -> pieces
  pieces       + completes        -> estimation
  pieces       + sans_depot       -> decision
  pieces       + reprise          -> pieces
  pieces       + epuise           -> decision
  estimation   + montant_nul      -> decision
  estimation   + montant_positif  -> antifraude
  antifraude   + termine          -> decision
  decision     + close            -> fin
```

C'est l'annexe technique du chantier 1, transcrite. **Une table, pas une conversation** : aucun
agent ne l'importe, ce qui les empêche de se renvoyer le travail.

### Les frontières

Onze règles d'architecture, vérifiées sur les imports par 23 tests. Elles ne reposent sur la
vigilance de personne : un import interdit fait tomber un test, pas une relecture.

| Famille          | Règles                                                                                                         |
| ---------------- | -------------------------------------------------------------------------------------------------------------- |
| Entre agents     | aucun agent n'importe un autre agent, ni l'orchestration, ni le dossier                                        |
| Vers l'extérieur | seul `antifraude` importe `partenaire/` ; seule `passerelle.py` lit l'adresse et le jeton ; aucun jeton en dur |
| Le cœur          | `regles/` n'importe rien du paquet                                                                             |
| L'écriture       | seul `repartiteur.py` écrit dans le dossier                                                                    |
| Les bords        | `partenaire/` ne remonte pas vers l'équipe ; la porte publique expose trois fonctions                          |

### Ce que la revue d'architecture n'a pas trouvé

Aucune frontière franchie, aucun cycle d'import, aucune dérive entre le dossier de conception et
le code. C'est le résultat attendu quand les frontières sont testées plutôt que recommandées.

---

## 2 · Revue de code

Menée à l'outil — volume, longueur des fonctions, code mort, couverture — puis à la lecture.

### Les six défauts trouvés

|       | Défaut                                                            | Nature            | Traitement                                                                |
| ----- | ----------------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------- |
| **1** | `Dossier.copie_demande` n'était appelée nulle part                | code mort         | supprimée, ainsi que son import `deepcopy`                                |
| **2** | `cli.py` à **0 %** de couverture                                  | dette             | 10 tests écrits — c'est pourtant la première chose qu'un évaluateur lance |
| **3** | `validation.py` à 79 % : les enveloppes malmenées jamais exercées | dette             | 58 tests, chaque branche de rejet pour elle-même                          |
| **4** | Quatre garde-fous jamais atteints par la recette                  | dette ancienne    | 15 tests qui les déclenchent en resserrant les bornes                     |
| **5** | Un test du modèle vert alors que le modèle ne répondait pas       | défaut de test    | `AJ-04`                                                                   |
| **6** | Un jeu de test aligné sur ce que les règles savaient faire        | défaut de méthode | `AJ-07`                                                                   |

Les défauts 5 et 6 sont les plus instructifs : ils étaient dans **mes tests**, pas dans le code
qu'ils surveillent. Un test vert sur un composant en panne interdit de chercher.

### Volume

|                                            | Lignes        |
| ------------------------------------------ | ------------- |
| `src/kaldera/`                             | 2 085         |
| `tests/chantier_1/` et `tests/chantier_2/` | 3 500 environ |
| `demo/`                                    | 2 400 environ |

Plus de tests que de code. Pour un système dont la promesse est « jamais de blocage, jamais de
donnée en trop », c'est le rapport attendu.

### Les fonctions les plus longues

| Lignes | Fonction                | Verdict                                                                                                       |
| ------ | ----------------------- | ------------------------------------------------------------------------------------------------------------- |
| 58     | `repartiteur._derouler` | **acceptable** : c'est la boucle d'orchestration, la découper éclaterait un déroulé qui se lit d'un trait     |
| 57     | `repartiteur._confier`  | **acceptable** : déléguer, réceptionner, journaliser, mesurer — les quatre temps d'une étape                  |
| 52     | `passerelle.consulter`  | **acceptable** : registre, charge, envoi, validation, verdict                                                 |
| 45     | `decision._issue`       | **voulu** : c'est l'ordre des règles de la section 10, dans l'ordre. Le découper le rendrait moins vérifiable |

Aucune ne dépasse 60 lignes, aucune n'imbrique plus de trois niveaux. Rien à redécouper.

### Couverture

**96 %**, contre 90 % avant la revue.

| Module                         | Avant | Après   |
| ------------------------------ | ----- | ------- |
| `cli.py`                       | 0 %   | couvert |
| `partenaire/validation.py`     | 79 %  | couvert |
| `orchestration/repartiteur.py` | 92 %  | couvert |
| `partenaire/passerelle.py`     | 88 %  | couvert |

Ce qui reste découvert est assumé : `llm.py`, fourni par le brief et que nous n'utilisons pas
(voir §4), et quelques branches défensives.

---

## 3 · Auto-évaluation

Face aux critères de performance du brief, avec ce qui les démontre.

| Critère                                    | État                                   | Ce qui le prouve                                                                                                                                  |
| ------------------------------------------ | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Les tests d'acceptance fournis passent** | tenu                                   | 56 / 56. Preuve datée dans `preuves/acceptance.txt`                                                                                               |
| **`EX-1` — jamais de blocage**             | tenu                                   | 28 scénarios, plus `S16` (agent défaillant) et les quatre garde-fous. Toute demande ressort avec une issue motivée, y compris quand le code tombe |
| **`EX-2` — un rôle, une frontière**        | tenu, et **rendu impossible à violer** | 23 tests d'architecture sur les imports ; 7 invariants sur 175 cas                                                                                |
| **`EX-3` — minimisation**                  | tenu, et **étendu**                    | Charge construite en partant de rien ; le client externe démontre une chaîne à trois paliers ; aucune donnée personnelle dans les journaux        |
| **`EX-4` — une réponse se vérifie**        | tenu                                   | Quatre niveaux, 58 tests de validation, rien du contenu rejeté ne ressort                                                                         |
| **`EX-5` — mode dégradé**                  | tenu                                   | `PAN-01` : trois fiches sur cinq non marquées. Le mode dégradé est une propriété d'une demande, pas un état du système                            |
| **`EX-6` — bornes et mesures**             | tenu                                   | Cinq bornes publiées et figées par un test ; mesures par agent ; quatre signaux ajoutés ; journal d'exploitation                                  |
| **A2A conforme au contrat**                | tenu                                   | Sept champs, un seul appel par dossier, abandon à 3 s, 16 / 16 tests A2A                                                                          |
| **Bornes justifiées par l'épreuve**        | tenu                                   | 19 mutations réintroduites, 19 détectées                                                                                                          |

### Ce qui va au-delà du demandé

- **Un client externe** qui challenge le brief : il démontre que la porte publique suffit à
  intégrer la plateforme, et met en scène la chaîne de minimisation.
- **Un modèle de langage**, au seul endroit où il a du sens — la prise de déclaration — mesuré
  sur un jeu de récits, et **écarté de la suite reproductible** parce qu'il n'est pas déterministe.
- **Une observabilité** avec journal structuré, garde-fou sur les données personnelles, et vue
  visuelle.
- **Une démonstration** en huit vues qui rejoue en direct.

### Ce que je referais autrement

- **Mesurer la couverture plus tôt.** Elle a trouvé en une commande ce que je cherchais en
  relisant : la ligne de commande sans test, les garde-fous jamais atteints.
- **Écrire le jeu d'attendus avant l'extracteur**, et non après. L'ordre inverse produit des
  attendus qui décrivent le code au lieu de le juger (`AJ-07`).
- **Vérifier qui produit un résultat, pas seulement le résultat.** Le repli silencieux d'un
  composant est précisément ce qu'un test doit refuser (`AJ-04`).

### Ce qui reste faible, et que je n'ai pas caché

| Point                                                   | Pourquoi ça compte                                                                                               |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **`D11`** — toute escalade sur borne va au gestionnaire | Règle que nous avons ajoutée, qu'aucun texte ne fonde. Signalée en revue                                         |
| **Le critère de « cohérence »** des pièces              | Réduit au tableau de la section 5, faute de définition. Question ouverte au métier                               |
| **`mypy` ne tourne plus**                               | Son extension native est bloquée par la stratégie du poste. Dernier passage propre, mais ce n'est plus vérifié   |
| **Le traitement est séquentiel**                        | Tenu par `S12`, mais la conformité à l'engagement de service repose sur l'abandon à 3 s, pas sur du parallélisme |
| **Le modèle n'est pas déterministe**                    | Isolé derrière un marqueur. C'est la vérification pratique de `D25`                                              |

---

## 4 · Deux décisions de ménage

**`Dossier.copie_demande` est supprimée.** Écrite « au cas où », appelée nulle part. Le code mort
donne à relire ce qui n'existe pas.

**`llm.py` est conservé, et c'est un choix.** Fourni par le brief, il n'est importé par personne :
le client externe a sa propre fabrique, puisqu'il ne doit rien importer de `kaldera`. Le supprimer
serait défendable ; le garder documente ce que le brief proposait et que `D25` a écarté. Les
quatre dépendances LangChain qu'il entraîne sont, elles, **du poids inutile** — à retirer si le
dépôt devait être allégé.

---

*Les sept ajustements sont dans [`journal_ajustements.md`](journal_ajustements.md), le chantier 1
dans [`07_chantier_1_realise.md`](07_chantier_1_realise.md), le chantier 2 dans
[`08_chantier_2_realise.md`](08_chantier_2_realise.md).*
