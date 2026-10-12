# Le harnais de test, et ce qu'il exige vraiment

Brief Kaldera · Phase DÉVELOPPEMENT · 7 octobre 2026

`tests/acceptance/conftest.py` est la définition opérationnelle de « tester une équipe ». Ce document
dit ce que la suite exige réellement du code, ce qu'elle ne vérifie pas, et comment les sept
invariants de la conception s'y branchent.

---

## En bref

- **Six tests, 56 cas.** Trois sur l'orchestration, trois sur la collaboration A2A.
- **Sept contraintes d'implémentation** que ni les spécifications ni le contrat d'intégration ne
  laissent voir — elles ne sont lisibles que dans le harnais.
- **La conception se vérifie une fois de plus** : les sept champs du contrat, les trois fiches sur
  cinq de `PAN-01`, et la distinction `NOM-09` / `BCL-01` sont dans le dépôt, telles qu'écrites.
- **Trois hypothèses de la conception tombent, du bon côté** : le harnais fournit plus que ce que
  nous avions supposé.
- **Un invariant sur sept n'est vérifié par aucun test fourni**, et deux autres ne le sont que
  partiellement. C'est là que les scénarios ajoutés servent.

---

## 1 · Ce que la suite vérifie

| Test                                                     | Sur quoi           | Ce qu'il exige                                                          |
| -------------------------------------------------------- | ------------------ | ----------------------------------------------------------------------- |
| `test_scenario_nominal_produit_la_decision_attendue`     | 11 nominaux        | L'issue attendue **et** la répartition des rôles                        |
| `test_toute_demande_aboutit_a_une_decision_ou_escalade`  | les 28             | Autant de fiches que de demandes, **dans l'ordre**, chacune motivée     |
| `test_scenario_piege_a_boucle_s_arrete_dans_les_bornes`  | `BCL-01`           | `bornes()`, la borne d'étapes, la borne de durée, l'arrêt signalé       |
| `test_echange_antifraude_respecte_le_contrat...`         | 7 antifraude       | Un seul appel, les 7 champs, aucune donnée personnelle, le score repris |
| `test_reponse_invalide_du_partenaire_est_rejetee...`     | 7 invalides        | Requête conforme, avis écarté, rien du contenu rejeté dans la fiche     |
| `test_partenaire_en_panne_le_mode_degrade_s_applique...` | `PAN-01`, `PAN-02` | Le mode dégradé attendu, aucune relance, **les métriques par agent**    |

---

## 2 · Sept contraintes que seul le harnais révèle

Ce sont des conditions de réussite qu'on ne devinerait pas en lisant les spécifications. Chacune
peut coûter une journée si on la découvre en fin de parcours.

### 2.1 · La trace porte l'agent **auteur**, jamais le greffier

`verifier_roles` impose deux choses à la fois : une section a **un seul** auteur, et un agent n'écrit
**qu'une seule** section métier.

La conception avait distingué l'**auteur** (l'agent métier qui produit le contenu) du **greffier**
(le répartiteur, seul à écrire dans le dossier — `D7`). Le harnais tranche la façon de l'écrire :
le champ `agent` de chaque étape doit porter **le nom de l'agent métier**. Si le répartiteur
s'inscrivait comme auteur des cinq sections, les six tests de rôle échoueraient d'un coup.

Le répartiteur peut figurer dans la trace, mais avec `ecrit: []`.

### 2.2 · `eligibilite` et `issue` sont toujours attendues

Même pour une demande refusée d'emblée. Une sortie anticipée doit donc **passer par l'agent de
décision**, pas court-circuiter vers la fiche. C'est exactement la « sortie ordonnée » de la
conception, mais le harnais en fait une condition de réussite, pas une élégance.

Pour une décision `acceptee`, `pieces` et `estimation` sont requises en plus.

### 2.3 · Les métriques couvrent **tout agent vu dans une trace**

```python
agents = {etape.get("agent") for f in fiches.values() for etape in f.get("trace", [])}
```

Si le répartiteur apparaît dans la trace, il lui faut ses quatre mesures comme aux autres. Le test
exige en plus qu'au moins un `appels_externes ≥ 1` et un `echecs ≥ 1` soient visibles pendant une
panne : **l'indisponibilité du partenaire doit se lire dans les mesures**, pas seulement dans les
fiches.

### 2.4 · Notre requête doit être conforme, même quand la réponse ne l'est pas

Sur les sept scénarios `invalide`, le test commence par :

```python
assert appels and appels[0]["conforme"]
```

Autrement dit : avant de juger notre traitement d'une réponse invalide, la suite vérifie que **notre
envoi** était irréprochable. Une charge mal construite ferait échouer ces tests pour une raison qui
n'a rien à voir avec leur objet.

### 2.5 · Aucune valeur personnelle, même en sous-chaîne

`valeurs_personnelles` dresse la liste à ne jamais retrouver dans le corps envoyé : les huit champs
de l'assuré, **plus** le numéro de contrat et **la description libre du sinistre**. La recherche se
fait par inclusion de chaîne dans le corps sérialisé.

Conséquence pratique : le `departement` doit être **dérivé** du code postal, pas le recopier. Le
partenaire l'impose d'ailleurs par sa propre validation — `^(\d{2}|2A|2B|97\d)$`, deux caractères.

### 2.6 · Le budget de temps du harnais n'est pas celui des bornes

| Niveau      | Budget du harnais | Comportement au dépassement             |
| ----------- | ----------------- | --------------------------------------- |
| Une demande | `10 + 1,5` s      | `pytest.fail` — « ne rend pas la main » |
| Un lot      | `10 × n + 1,5` s  | idem                                    |

Le traitement tourne dans un fil d'exécution avec `join(délai)`. Un blocage ne fige pas la suite :
il échoue proprement. Et `bornes()["duree_max_s"]` est contrôlée : elle doit être **strictement
positive et ≤ 10**.

### 2.7 · Le doublon est natif, pas à simuler

Le partenaire simulé mémorise les dossiers évalués et répond `-32029` au second appel, en marquant
`"doublon": true` dans son journal. **La clause « un seul appel par dossier » est donc opposable
dès le premier jour**, sans rien ajouter au harnais.

---

## 3 · Les sept invariants de la conception, confrontés

|        | Invariant                                                                | Vérifié par la suite fournie ?                                                                                                       |
| ------ | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| **I1** | Autant de fiches que de demandes, dans l'ordre, chacune motivée          | **Oui**, entièrement — l'ordre est vérifié par l'appariement référence par référence                                                 |
| **I2** | Aucune demande ne dépasse 10 secondes                                    | **Oui**, avec une marge de 1,5 s                                                                                                     |
| **I3** | Chaque section a un auteur unique ; aucun agent n'en écrit deux          | **Partiellement** — `verifier_roles` n'est appelé que sur les nominaux et les antifraude, jamais sur `invalide`, `panne` ou `boucle` |
| **I4** | La succession des agents est l'un des enchaînements que le plan autorise | **Non. Aucun test ne regarde l'ordre des agents**                                                                                    |
| **I5** | Le journal ne dépasse pas la borne d'étapes, et un arrêt est signalé     | **Partiellement** — sur `BCL-01` seulement                                                                                           |
| **I6** | Aucune valeur issue d'une réponse rejetée n'apparaît dans la fiche       | **Oui** — sur deux valeurs témoins connues                                                                                           |
| **I7** | Chaque agent a ses quatre mesures, et ses appels égalent ses étapes      | **Partiellement** — les quatre mesures sont vérifiées, **l'égalité appels/étapes ne l'est pas**                                      |

**Un invariant non couvert, trois partiels.** Ce n'est pas un reproche à la suite fournie : elle
vérifie le contrat, pas notre conception. C'est précisément ce que les scénarios ajoutés au plan
d'épreuve doivent combler — et cela confirme leur utilité, mesurée plutôt qu'affirmée.

---

## 4 · Trois hypothèses de la conception qui tombent du bon côté

**Le partenaire simulé n'est pas une boîte noire.** La conception écrivait qu'`I6` « suppose de
connaître les valeurs rejetées », inconnues à ce stade. Le harnais les nomme : `EVA-NC` et
`rembourser_integralement`. L'invariant devient directement vérifiable.

**Le journal du partenaire est consultable.** `partenaire.journal()` rend, pour chaque appel reçu :
la référence, les `champs` transmis, le `corps_brut`, le `statut_http`, `conforme`, les `erreurs`,
la `reponse` et `doublon`. Plusieurs des scénarios que la conception annonçait « sans harnais » —
notamment ceux qui observent ce qui part chez le partenaire — sont donc réalisables tels quels.

**La carte d'agent existe et est servie** à `/.well-known/agent.json`, avec la version du contrat,
le schéma d'authentification et la compétence déclarée. En mode `panne`, elle devient indisponible
elle aussi. Le point **⚠3** est donc un vrai choix, pas une impossibilité.

---

## 5 · Ce que le harnais ne contraint pas : le parallélisme

C'est le constat le plus utile de cette lecture, et il tranche un point resté ouvert depuis la
conception.

|                                     | Valeur                                                       |
| ----------------------------------- | ------------------------------------------------------------ |
| `PAN-02`                            | 3 demandes, partenaire **lent à 5 s**                        |
| Budget du harnais pour ce lot       | `10 × 3 + 1,5` = **31,5 s**                                  |
| Coût d'un traitement **séquentiel** | 3 abandons à 3 s, soit ≈ **9 s** — trois fois sous le budget |

**Un traitement séquentiel passe la recette.** Aucun test fourni ne mesure que les demandes avancent
indépendamment.

La conception avait déjà corrigé une erreur sur ce point : l'argument du parallélisme ne tenait pas,
et l'indépendance ne reposait que sur le texte de la section 12 — *« le traitement d'une demande
n'est jamais retardé par celui d'une autre »*. La lecture du harnais le confirme sur le code réel.

**Conséquence pour ⚠1** : la concurrence est un choix de **conformité à l'engagement de service**,
pas une nécessité pour faire passer les tests. Si elle est retenue, c'est en le disant ainsi — et il
faut alors écrire le scénario qui l'éprouve, puisque aucun fourni ne le fait.

---

## 6 · Ce que la conception avait vu juste

| Point de conception                                             | Ce que le dépôt en dit                                                                                                    |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Les sept champs envoyés au partenaire                           | `CHAMPS_CONTRAT` dans `conftest.py` les liste — **les sept, exactement**                                                  |
| « Trois fiches sur cinq ne doivent pas être marquées »          | `PAN-01` : `mode_degrade` à `false` sur trois demandes, `true` sur deux                                                   |
| `NOM-09` ≠ `BCL-01`                                             | `NOM-09` (aucun dépôt) → escalade **sans** `arret`. `BCL-01` (dépôt toujours illisible) → escalade **avec** `arret: true` |
| Validation stricte des réponses                                 | Le partenaire valide lui-même champs refusés, absents et invalides                                                        |
| Les seuils 0,40 et 0,75, les six champs, les quatre indicateurs | Tous présents dans le simulateur, qui annonce `CONTRAT_VERSION = "2.0"`                                                   |
| Bornes `etapes_max` et `duree_max_s`                            | Contrôlées par le test de boucle ; nos 10 étapes et 8 s passent                                                           |

La distinction `NOM-09` / `BCL-01` mérite d'être relevée : c'est une erreur que la conception avait
commise, puis corrigée d'elle-même. Le dépôt donne raison à la version corrigée.

---

## 7 · Ce que cela entraîne

- [ ] **Nommer les agents dans la trace par leur rôle métier** — `eligibilite`, `pieces`,
      `estimation`, `antifraude`, `decision`. Le répartiteur peut apparaître, avec `ecrit: []`
- [ ] Faire passer **toute** sortie anticipée par l'agent de décision, pour que `issue` ait toujours
      un auteur
- [ ] Prévoir les métriques du répartiteur s'il figure dans la trace
- [ ] Dériver le `departement` du code postal, sans jamais recopier celui-ci
- [ ] Écrire les scénarios qui couvrent `I4`, et compléter `I3`, `I5`, `I7`
- [ ] Décider pour **⚠1** en sachant que le séquentiel passe la recette — et, si la concurrence est
      retenue, écrire le scénario qui l'éprouve
- [ ] Reprendre les scénarios ajoutés que le harnais rend maintenant réalisables, et retirer la
      mention « harnais inexistant » là où elle ne tient plus

---

*Lecture faite sur `tests/acceptance/conftest.py` (270 lignes), les deux fichiers de test,
`external_agent/app.py` (423 lignes) et `eval/scenarios.jsonl`. L'état de départ mesuré est dans
[`05_etat_du_depot.md`](05_etat_du_depot.md).*
