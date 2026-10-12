# État du dépôt — le point de départ, mesuré

Brief Kaldera · Phase DÉVELOPPEMENT · 7 octobre 2026

Le dépôt du brief a été forké, cloné et installé. Ce document établit **l'état de départ avant toute
modification** : ce que le squelette fait, ce qu'il ne fait pas, et ce que sa lecture change dans la
conception.

---

## En bref

- **Le point de départ est un agent unique.** `AgentGeneraliste` mène tous les contrôles ; le
  répartiteur route les six actions vers lui seul. C'est exactement le travail du chantier 1.
- **45 tests échouent, 11 passent.** Mesuré, reproductible, avant toute modification.
- **Huit écarts** au contrat d'intégration et aux spécifications — un de plus que ce que la seule
  lecture laissait voir.
- **La conception se vérifie.** Le contrat d'intégration reprend mot pour mot la règle
  « une section, un agent ». Et un scénario de recette tranche en sa faveur une divergence métier.
- **Le modèle de langage est fourni, déclaré facultatif, et importé par personne.** `D25` tient.

---

## 1 · Ce qui a été fait

| Étape         | Détail                                                                             |
| ------------- | ---------------------------------------------------------------------------------- |
| Fork          | `bybysker/kaldera-bout-en-bout` → `Bealph/kaldera-bout-en-bout`                    |
| Clone         | `kaldera-bout-en-bout/`, à côté de la conception · `upstream` pointé sur la source |
| Environnement | `uv venv` depuis le **Python 3.11 du système**, puis `uv sync`                     |
| Tests         | `uv run python -m pytest -q`                                                       |
| Modifications | **aucune** — le dépôt est à son commit d'origine, rien n'a été commité ni poussé   |

**Deux adaptations au poste**, à retenir pour la suite :

- **`make install` n'a pas été lancé tel quel.** `uv sync` seul laisse `uv` choisir l'interpréteur,
  et celui qu'il télécharge a `_ctypes` bloqué sur ce poste. Par précaution, l'environnement a été
  construit avec `uv venv --python <Python311 du système>` **avant** le `uv sync`, qui s'est alors
  déroulé sans erreur. Le comportement de `uv sync` seul n'a donc pas été éprouvé ici.
- `make test` échouait : `uv run pytest` → *« Une stratégie de contrôle d'application a bloqué
  ce fichier » (os error 4551)*. Le contournement est `uv run python -m pytest`, qui fonctionne.
  **Ce blocage s'est levé en cours de journée** : quelques heures plus tard, le même exécutable
  passait. Il semble viser les binaires fraîchement écrits, le temps d'une analyse. L'invocation
  en module reste préférée, parce qu'elle fonctionne dans les deux cas.

**Le `Makefile` a été repris** pour invoquer tous les outils en module. C'est une contrainte
d'environnement, pas un défaut du brief.

---

## 2 · L'état de départ mesuré

```
uv run python -m pytest -q
45 failed, 11 passed in 14.03s
```

Deux exécutions successives : 17,40 s puis 14,03 s, mêmes 45 échecs. Reproductible.

**56 tests au total**, répartis en deux fichiers — et la répartition est parlante :

| Fichier                        | Tests | Échecs | Lecture                                                |
| ------------------------------ | ----- | ------ | ------------------------------------------------------ |
| `test_equipe_orchestration.py` | 40    | 29     | Le chantier 1 est partiellement tenu                   |
| `test_collaboration_a2a.py`    | 16    | **16** | **Aucun test A2A ne passe** : le chantier 2 est à zéro |

Le détail, test par test :

| Fichier de test             | Test                                                        | Échecs |
| --------------------------- | ----------------------------------------------------------- | ------ |
| `test_equipe_orchestration` | `test_toute_demande_aboutit_a_une_decision_ou_une_escalade` | 17     |
| `test_equipe_orchestration` | `test_scenario_nominal_produit_la_decision_attendue`        | 11     |
| `test_equipe_orchestration` | `test_scenario_piege_a_boucle_s_arrete_dans_les_bornes`     | 1      |
| `test_collaboration_a2a`    | `test_echange_antifraude_respecte_le_contrat...`            | 7      |
| `test_collaboration_a2a`    | `test_reponse_invalide_du_partenaire_est_rejetee...`        | 7      |
| `test_collaboration_a2a`    | `test_partenaire_en_panne_le_mode_degrade_s_applique...`    | 2      |

**Où tombent les onze scénarios nominaux.** Mesuré en rattachant chaque échec à sa fonction de
vérification dans `conftest.py`, un scénario à la fois :

| Cause de l'échec                             | Scénarios        |
| -------------------------------------------- | ---------------- |
| `verifier_roles` — la répartition du travail | **10** sur 11    |
| `verifier_issue_attendue` — le métier        | **1** : `NOM-05` |

Les dix premiers produisent **la bonne décision** et tombent sur le rôle :
*« l'agent "generaliste" a écrit plusieurs sections métier (eligibilite, estimation, issue,
pieces) »*. Le squelette est juste métier sur les nominaux, à une exception près — et cette
exception est le plafond (écart 8).

Autrement dit : ce qui manque au squelette, c'est **répartir le travail**. C'est précisément
l'objet du brief.

Le dépôt contient **28 scénarios** et **34 demandes** — conforme au décompte de la conception.

---

## 3 · Les huit écarts

Les sept premiers sont des manques par rapport au contrat d'intégration. Le huitième est une
**erreur métier**, et c'est le plus grave.

| #     | Écart                                       | Où                     | Conséquence                                              |
| ----- | ------------------------------------------- | ---------------------- | -------------------------------------------------------- |
| **1** | `bornes()` n'existe pas                     | `__init__.py`          | Le contrat d'intégration l'exige                         |
| **2** | `metriques` n'est pas indexé par agent      | `__init__.py`          | Rend `demandes` et `duree_totale_ms`, rien par agent     |
| **3** | La fiche n'a ni `mode_degrade` ni `arret`   | `orchestrateur.py`     | Deux champs du contrat absents                           |
| **4** | Aucune borne de durée ; `MAX_TOURS = 50`    | `orchestrateur.py`     | `etapes_max` non respecté, pas de sortie ordonnée        |
| **5** | Partenaire muet → `issue: "en_attente"`     | `orchestrateur.py`     | **La demande ressort sans décision**                     |
| **6** | `"data": demande` — la demande entière part | `partenaire.py`        | **Aucune minimisation** : nom, IBAN, description sortent |
| **7** | `timeout=None`                              | `partenaire.py`        | Aucun abandon : le scénario « lent » bloque              |
| **8** | Le plafond refuse au lieu d'écrêter         | `agent_generaliste.py` | **Erreur métier**, démontrée ci-dessous                  |

### L'écart 5 contredit les spécifications

`consulter_partenaire` pose `attente_partenaire = True` quand l'avis n'est pas obtenu.
`prochaine_action` rend alors `None`, la boucle s'arrête, et `construire_fiche` produit
`issue: "en_attente"`.

Or la section 2 des spécifications écrit : *« Une demande est traitée lorsqu'elle a reçu une issue.
Il n'existe pas d'autre état final : une demande ne reste jamais "en attente" sans qu'un humain en
ait été saisi. »* **Le mode dégradé est entièrement à écrire.**

### L'écart 6 est la violation directe d'`EX-3`

```python
"parts": [{"kind": "data", "data": demande}]
```

La demande entière part chez le partenaire : `assure` avec le nom, l'IBAN, le téléphone, l'adresse,
et la `description` en texte libre. Le contrat partenaire interdit ces champs *« sous quelque forme
que ce soit »*. C'est exactement le défaut que la conception avait anticipé en imposant une charge
**construite en partant de rien** plutôt qu'une demande filtrée.

La suite d'acceptance le dit sans détour, sur `AF-01` :

```
AssertionError: KAL-26-0201 : données hors contrat transmises :
assure, contrat, espace_assure, historique, pieces, reference, sinistre
```

### L'écart 8 — le plafond, démontré par un scénario

Le squelette traite le plafond comme un **critère d'éligibilité** :

```python
if sinistre["montant_declare"] > formule["plafond"]:
    motifs.append("montant supérieur au plafond de garantie")
```

Les spécifications écrivent autre chose, section 4 : *« Aucune demande ne peut donner lieu à un
**remboursement** supérieur au plafond de sa formule. »* C'est un écrêtage du montant remboursé, pas
un refus — et c'est ce que la conception avait tranché (`C3`, `D3` : le plafond appartient à
l'estimation, parce qu'il modifie un montant et ne décide pas de la recevabilité).

**Le scénario `NOM-05` tranche :**

|                              | Valeur                                                       |
| ---------------------------- | ------------------------------------------------------------ |
| Formule                      | `essentiel` — franchise 300 €, plafond 3 000 €               |
| Montant déclaré              | 4 200 € · facture lisible de 4 200 €                         |
| **Attendu par la recette**   | `acceptee`, **3 000 €**                                      |
| **Produit par le squelette** | `refusee`, 0 €, « montant supérieur au plafond de garantie » |

Et le montant attendu lève une ambiguïté restée ouverte en conception : 4 200 − 300 = 3 900, écrêté
à 3 000. Si le plafond s'appliquait avant la franchise, l'attendu serait 2 700. **L'ordre est donc
bien franchise puis plafond**, comme `C3` le posait.

---

## 4 · Ce que le dépôt confirme de la conception

| Décision                                        | Ce que le dépôt en dit                                                                                                                                         |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cinq sections métier, un agent par section      | `docs/interface.md` : *« une section métier n'est écrite que par un seul agent, et un agent n'écrit qu'une seule section métier »*, et nomme les cinq          |
| `bornes()` avec `etapes_max` et `duree_max_s`   | Exigé par le contrat, `duree_max_s` ≤ 10. Nos 10 étapes et 8 s passent                                                                                         |
| `C3` — franchise puis plafond, à l'estimation   | Démontré par `NOM-05`                                                                                                                                          |
| `trace` portant `agent` et `ecrit`              | C'est la forme exacte imposée. `EX-2` se vérifie dessus                                                                                                        |
| 28 scénarios, catégories dont `boucle`          | Conforme, `BCL-01` existe                                                                                                                                      |
| `D25` — aucun modèle dans le chemin de décision | `llm.py` existe, LangChain et LangGraph sont déclarés, **aucun module ne les importe**, et `.env.example` écrit : *« LLM (Azure AI — Kimi-K2.6), facultatif »* |

Sur ce dernier point, l'arbitrage gagne un argument : il y avait une fabrique prête à l'emploi, et
le brief la qualifie lui-même de facultative.

---

## 5 · Ce qui bouge dans l'architecture

**L'arborescence.** Le code vit sous `src/kaldera/`, pas `kaldera/`. La structure proposée en
[`03_architecture.md`](03_architecture.md) se réancre dessous, sans autre changement : les six
couches et les sept règles de dépendance ne sont pas remises en cause par ce que contient le
dépôt.

**Ce qui existe déjà et qu'il faut garder.** `regles.py` contient le référentiel métier — formules,
pièces exigées, seuils — **conforme aux spécifications** : c'est son usage dans l'éligibilité qui
est fautif, pas la table elle-même. `espace_assure.py` simule le portail de l'assuré, et sa
docstring explique la source des boucles : *« un assuré qui n'a rien de nouveau à transmettre
re-soumet son dernier dépôt »*. `cli.py` rejoue des scénarios ; l'interface de visualisation pourra
s'en inspirer plutôt que de repartir de zéro.

**Ce qui manque et que la conception avait prévu.** Aucune constante de seuil pour le mode dégradé
(1 500 €), aucune borne, aucun registre d'appels, aucune construction de charge.

**Le point ⚠1 reste ouvert, mais s'éclaire.** `traiter_lot` est aujourd'hui une boucle séquentielle.
Rien dans le contrat n'impose la concurrence — seul l'engagement *« le traitement d'une demande
n'est jamais retardé par celui d'une autre »* (section 12) la rend nécessaire, et `PAN-02` l'éprouve
avec un partenaire lent.

---

## 6 · Les points à trancher — **tous tranchés depuis**

|        | Point                         | Décision                                                                                      |
| ------ | ----------------------------- | --------------------------------------------------------------------------------------------- |
| **✓1** | Concurrence du lot            | **Séquentiel** *(`D27`)*, démontré par `S12` qui borne le lot entier                          |
| **✓2** | Bibliothèque de validation    | **Écrite à la main** *(`D28`)* : une bibliothèque accepte les champs en trop par défaut       |
| **✓3** | Découverte par *Agent Card*   | **Adresse configurée** *(`D29`)* : rien ne l'impose, et c'est un point de défaillance de plus |
| **✓4** | Emplacement du code           | Cloné à côté de la conception                                                                 |
| **✓5** | Client externe en A2A entrant | La porte publique est faite de fonctions : appel direct, ou rien                              |

## 7 · Ce que cela entraîne

- [ ] Reprendre le plafond : le retirer de l'éligibilité, l'appliquer à l'estimation **après** la
      franchise *(`C3`, `D3`)*
- [ ] Documenter les deux contournements du poste dans le dépôt — `uv venv` depuis le Python
      système, et `python -m pytest` au lieu de `pytest`
- [ ] Garder `45 failed, 11 passed` comme repère : toute mesure ultérieure se compare à celui-là
- [ ] Vérifier que le partenaire simulé (`external_agent/app.py`) suit bien la version 2.0 du
      contrat, et s'il sait simuler un doublon (`-32029`)
- [ ] Lire `tests/acceptance/conftest.py` en entier — il porte les invariants que la suite vérifie,
      et c'est la définition opérationnelle de « tester une équipe »

---

*Commandes de reproduction, depuis `kaldera-bout-en-bout/` :*

```
uv venv --python "C:/Users/<vous>/AppData/Local/Programs/Python/Python311/python.exe"
uv sync
uv run python -m pytest -q
uv run python -m kaldera.cli eval/scenarios.jsonl --scenario NOM-05
```
