# Chantier 1 réalisé — l'équipe et son orchestration

Brief Kaldera · Phase DÉVELOPPEMENT · 7 octobre 2026

L'agent unique du squelette est devenu une équipe de cinq agents coordonnés par un répartiteur.
Ce document dit ce qui a été construit, ce que cela mesure, et ce qui reste au chantier 2.

---

## En bref

- **332 tests passent, 14 échouent** — contre 11 et 45 au départ. Les quatorze restants sont
  **tous** des tests A2A, c'est-à-dire le chantier 2.
- **La suite d'orchestration est entièrement verte** : 40 tests sur 40.
- **290 tests propres au chantier 1** ont été écrits, dont un test d'architecture qui vérifie les
  frontières sur les imports eux-mêmes.
- **11 défauts réintroduits un par un, 11 détectés.** Les tests savent échouer.
- **Six des huit écarts** relevés à l'ouverture du dépôt sont corrigés ; les deux autres sont la
  minimisation des données et le délai d'abandon, tous deux au chantier 2.

---

## 1 · Ce qui a été construit

```
src/kaldera/
├── __init__.py              traiter_demande · traiter_lot · bornes
├── dossier.py               les quatre zones de la mémoire partagée
├── mesures.py               compteurs par demande, agrégation après coup
├── agents/
│   ├── eligibilite.py       → section « eligibilite »
│   ├── pieces.py            → section « pieces »
│   ├── estimation.py        → section « estimation »
│   ├── antifraude.py        → section « avis_fraude », ou aucune
│   └── decision.py          → section « issue »
├── orchestration/
│   ├── repartiteur.py       déléguer → réceptionner → avancer
│   ├── plan.py              le plan conditionnel, transcrit
│   └── bornes.py            valeurs publiées et noms d'arrêt
└── regles/                  formules · eligibilite · pieces · montants · indicateurs · issues
```

1 340 lignes de code, 717 lignes de tests propres au chantier. Trois modules du squelette ont
disparu : `agent_generaliste.py`, `orchestrateur.py` et `regles.py`.

**Ce que la structure garantit, et qui ne dépend plus de la vigilance de personne :** aucun agent
n'importe un autre agent, ni l'orchestration, ni le dossier ; seul l'agent anti-fraude parle au
partenaire ; `regles/` ne dépend de rien ; seul le répartiteur écrit dans le dossier.

---

## 2 · Les mesures

|                       | Au départ | Maintenant                  |
| --------------------- | --------- | --------------------------- |
| Tests passants        | 11        | **332**                     |
| Tests en échec        | 45        | **14**                      |
| Suite d'orchestration | 11 / 40   | **40 / 40**                 |
| Suite A2A             | 0 / 16    | 2 / 16                      |
| `ruff check`          | —         | passe                       |
| `mypy src`            | —         | 25 fichiers, aucun problème |

Les **14 échecs restants** se répartissaient en 7 scénarios anti-fraude et 7 scénarios de
réponse invalide, tous dus à deux manques connus et planifiés : la charge n'était pas encore
construite champ par champ, et les réponses pas encore validées. **Le chantier 2 les a tous
levés** — voir [`08_chantier_2_realise.md`](08_chantier_2_realise.md).

### Les tests écrits pour ce chantier

| Fichier                 | Tests | Ce qu'il vérifie                                                |
| ----------------------- | ----- | --------------------------------------------------------------- |
| `test_architecture.py`  | 19    | Les frontières, lues sur les imports — `EX-2` rendu automatique |
| `test_invariants.py`    | 175   | Les sept invariants d'équipe, appliqués aux 28 scénarios        |
| `test_bornes.py`        | 9     | Les bornes publiées sont celles qui ont été décidées            |
| `test_pieges_metier.py` | 87    | Les pièges que la conception avait identifiés                   |

### L'épreuve des mutations

`uv run python -m tests.chantier_1.epreuve_mutations` réintroduit **un** défaut réel à la fois,
lance **un** test précis, vérifie qu'il tombe, et restaure la source. Onze mutations, onze
détections :

le plafond appliqué avant la franchise · le plafond redevenu critère d'éligibilité · la trace
nommant le répartiteur · le mode dégradé marquant toutes les demandes · le seuil de 1 500 € porté à
15 000 € · l'arrêt non signalé · la borne d'étapes desserrée à 1 000 · un appel compté en trop · un
agent important un autre agent · un agent écrivant dans le dossier · l'agent anti-fraude inventant
un avis.

---

## 3 · Ce que l'autocritique a trouvé, et corrigé

**Un bug dans le répartiteur.** La vérification des garde-fous écrasait la borne déjà détectée par
un verdict d'agent : `BCL-01` ressortait avec le bon motif mais sans signalement d'arrêt. Trouvé en
lisant l'échec, pas en relisant le code.

**Une dépendance interdite.** L'agent de décision importait `orchestration.bornes` pour rédiger le
motif d'une sortie sur borne. Le motif lui arrive maintenant déjà rédigé : un agent n'a pas à
connaître les noms des bornes.

**Un défaut qu'aucun test ne voyait.** L'épreuve des mutations a montré que desserrer `etapes_max`
de 10 à 1 000 ne faisait tomber aucun test — l'invariant « le journal tient dans la borne » restait
vrai, puisque la borne avait grandi. C'est exactement ce que `D24` vise. Un fichier `test_bornes.py`
fige désormais les cinq valeurs décidées : une borne peut changer, mais le mouvement se voit dans
le diff.

**Trois cases cochées à tort.** En parcourant la checklist, j'avais coché d'un bloc les 36 cases du
chantier 1. Trois ne l'étaient pas : le journal de routage séparé n'existait pas, `cloture_manquante`
ne faisait échouer aucune recette, et la distinction `NOM-09` / `BCL-01` n'était vérifiée par aucun
test direct. Les trois sont faites, et vérifiées.

---

## 4 · Les décisions de conception, à l'épreuve du code

| Décision                                            | Ce que le code en dit                                                                   |
| --------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `D1`, `D3` — un agent, un rôle, une section         | Tenue. Un test d'architecture l'empêche de dériver                                      |
| `D5` — le plan appartient au répartiteur            | Tenue. `plan.py` est une table ; aucun agent ne l'importe                               |
| `D7` — auteur et greffier sont distincts            | Tenue, et c'est ce que le harnais exigeait sans le dire : la trace nomme l'agent métier |
| `D8` — rien de partagé entre demandes               | Tenue. Un dossier et des compteurs par demande, agrégation après coup                   |
| `D9` — motif par gabarit                            | Tenue. Aucun modèle de langage dans le chemin de décision *(`D25`)*                     |
| `D11` — toute escalade sur borne va au gestionnaire | Tenue, mais **toujours sans fondement textuel**. À signaler en revue                    |
| `D12` — le greffier n'est pas au journal de bord    | Tenue. Le routage vit dans la zone de travail                                           |
| `C3`, `D3` — franchise puis plafond                 | Tenue, et **démontrée** par `NOM-05`                                                    |
| `D21` — les invariants s'écrivent une fois          | Tenue. Sept invariants, 175 cas                                                         |
| `D24` — une borne ne se desserre pas en douce       | Tenue depuis l'ajout de `test_bornes.py`                                                |

---

## 4 bis · La démonstration

**Une application Streamlit qui rejoue en direct**, par la porte publique, et n'affiche que ce
qu'elle rend : la fiche, la trace et les mesures. Le partenaire anti-fraude simulé est lancé dans
le même processus et se pilote depuis l'interface — normal, lent, invalide, panne.

```
make demo        → http://127.0.0.1:8501
```

Le `Makefile` a été repris : toutes les cibles invoquent les outils **en module**
(`uv run python -m pytest`, `-m ruff`, `-m mypy`), car leurs exécutables sont bloqués par la
stratégie du poste. `make aide` les liste ; `make verifier` enchaîne lint, types et tests.

| Vue                       | Ce qu'elle montre                                                                                                                                                                                              |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Le flux**               | Le répartiteur qui délègue, les cinq agents qui s'allument un à un, le détour vers le partenaire avec son temps d'attente réel, et l'arbre des règles de la section 10 qui s'illumine sur la branche empruntée |
| **Le dossier**            | Les quatre zones de la mémoire et leur remplissage — `EX-2` rendu visible                                                                                                                                      |
| **L'équipe**              | La carte des agents, le plan du répartiteur, les sept frontières                                                                                                                                               |
| **Le lot et les mesures** | Les fiches dans l'ordre, les mesures par agent, ce que le partenaire a reçu                                                                                                                                    |
| **Ce qui reste**          | Les quatorze tests rouges du chantier 2, et les dettes assumées                                                                                                                                                |

Le parcours se déroule **au rythme choisi** ou pas à pas : l'animation rejoue les étapes dans
l'ordre du journal de bord, pas une séquence écrite d'avance.

**Les vues sont testées.** Un schéma qui se trompe de branche serait pire qu'une absence de
schéma — il aurait l'air d'une preuve. `tests/chantier_1/test_demo.py` vérifie sur les fiches
réelles des 28 scénarios que chaque motif se rattache à une règle, que chaque agent du journal
figure au schéma, et que le rendu tient à chaque instant du parcours. Six scénarios éprouvent
en plus l'exécution de la page entière.

**Trois choix à retenir :**

- **Streamlit plutôt qu'une page statique** : la démonstration rejoue réellement, et le partenaire
  se pilote en direct. Un export JSON autonome (`demo/exporter.py`) reste disponible en repli si
  l'application ne démarrait pas le jour de la soutenance.
- **L'écoute est limitée à la boucle locale** par `.streamlit/config.toml`. Par défaut, Streamlit
  publie l'application sur toutes les interfaces du poste, **y compris l'adresse publique** —
  constaté au premier lancement.
- **`st.dataframe` est inutilisable sur ce poste** : il passe par pandas, dont les extensions
  natives sont bloquées par la stratégie de contrôle d'application, comme `_ctypes`. Les tableaux
  sont rendus en Markdown. À noter : **le blocage des exécutables s'est levé en cours de journée**
  — `uv run pytest` passe désormais — mais pas celui des extensions natives.

**Une amélioration du système, pas seulement de la vue.** Pour distinguer un agent qui n'a pas
consulté le partenaire d'un agent dont la consultation a échoué très vite, chaque étape du journal
porte désormais `appels_externes`. Le contrat d'intégration laisse les champs supplémentaires
libres ; la démonstration s'appuie dessus plutôt que sur un seuil de durée arbitraire.

---

## 5 · Ce qui reste, et pour quand

**Au chantier 2**, les deux écarts non corrigés et les quatorze tests rouges :

- la charge envoyée au partenaire, construite champ par champ en partant de rien ;
- la validation des réponses aux quatre niveaux ;
- le délai d'abandon à 3 secondes ;
- le registre garantissant un seul appel par dossier.

**Dettes assumées à ce stade :**

- Quatre des cinq noms d'arrêt — `pieces_tentatives_epuisees`, `etapes_max_atteint`,
  `duree_max_atteinte`, `cloture_manquante` — sont du **code non éprouvé** : aucun scénario de la
  recette ne les atteint. À couvrir au plan d'épreuve.
- `D11` reste une règle que nous avons ajoutée sans qu'aucun texte la fonde.
- `traiter_lot` est **séquentiel** — depuis tranché *(`D27`)* : le scénario `S12` borne le lot
  entier et montre que l'engagement de service tient sans concurrence.

---

*État mesuré le 7 octobre 2026 avec `uv run python -m pytest -q`. Le point de départ est dans
[`05_etat_du_depot.md`](05_etat_du_depot.md), ce que le harnais exige dans
[`06_harnais_et_invariants.md`](06_harnais_et_invariants.md).*
