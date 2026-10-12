# Checklist de développement

Brief Kaldera « Développer une équipe d'agents de bout en bout » · Phase DÉVELOPPEMENT · 7 octobre 2026

Séquence de travail : **préalables → chantier 1 → chantier 2**, comme en conception. Chaque tâche
renvoie à la décision de conception qui la fonde (`D1` à `D24`) ou à l'exigence qu'elle sert
(`EX-1` à `EX-6`). Les cases marquées **⚠** sont celles où une hypothèse peut tomber.

---

## 0 · Préalables — à faire avant toute ligne de code

### 0.1 Le contrat partenaire — **fait le 7 octobre**

Le contrat a été fourni (version 2.0). La confrontation aux douze hypothèses est dans
[`01_confrontation_contrat.md`](01_confrontation_contrat.md). Onze hypothèses sur douze confirmées,
les deux clauses inconnues comblées — mais **la liste des données à envoyer est à refaire**.

- [x] Lire `external_agent/contrat.md` et le confronter aux douze hypothèses
- [x] Consigner chaque écart
- [x] **Reprendre les sept champs exacts du contrat** : retirer le délai de déclaration, le montant
      justifié et la formule ; ajouter `date_survenance` et `departement`
- [x] **Écrire la décision qui remplace `D15`** — le contrat exige la date de survenance, et accepte
      donc que la souscription soit déductible
- [x] Corriger la justification de `D19` : le contrat interdit explicitement toute relance, ce que
      nous ne pouvions pas affirmer
- [x] Mettre à jour l'annexe du chantier 2 : six champs en réponse, score dans [0 ; 1], seuils
      0,40 et 0,75
- [x] **Conserver l'`evaluation_id`** pour l'audit — dans la zone de travail et le journal, pas dans
      la fiche
- [x] **Garantir un seul appel par dossier** : un doublon est un manquement au contrat, pas une
      maladresse
- [x] Découverte par *Agent Card* : **non implémentée**, l'adresse est configurée par
      `PARTENAIRE_URL`. Choix écrit — le simulateur sert bien la carte, mais rien dans le contrat
      d'intégration n'impose de la lire, et un point de défaillance de plus ne se justifie pas

### 0.1 bis · Ouvrir le dépôt

- [x] Forker, puis cloner le dépôt du brief dans `kaldera-bout-en-bout/` — *fait le 7 octobre*
- [x] Examiner le squelette — **un `AgentGeneraliste` unique** routé par un `Orchestrateur` ;
      `src/kaldera/`, 26 fichiers. C'est le point de départ à refactorer en équipe
- [x] **Lire `docs/interface.md`** — la porte publique est faite de **trois fonctions Python**
      (`traiter_demande`, `traiter_lot`, `bornes()`). Un point d'entrée A2A entrant serait du travail
      en plus, non demandé : **le client externe (3 bis) se fera en appel direct, ou pas du tout**
- [x] Établir l'état de départ — **`45 failed, 11 passed`**, reproductible. `make test` est
      inutilisable sur ce poste (`pytest.exe` bloqué) : le contournement est `python -m pytest`
- [x] **Le partenaire simulé suit bien la version 2.0** — vérifié dans `external_agent/app.py` :
      `CONTRAT_VERSION = "2.0"`, seuils `0.40` et `0.75`, les six champs de réponse, les quatre
      indicateurs (`MONTANT_ELEVE`, `SINISTRE_PRECOCE`, `FREQUENCE_ELEVEE`, `TYPE_SENSIBLE`),
      le doublon `-32029` et la carte d'agent
- [x] Les **sept variantes `invalide`** correspondent aux sept scénarios `INV`, et les **cinq codes
      JSON-RPC** du contrat sont tous implémentés par le simulateur, sans un de plus. Notre
      passerelle les distingue désormais : `-32602` dit que **notre** requête est fautive
- [x] **Le doublon est natif** — le simulateur mémorise les dossiers évalués, répond `-32029` au
      second appel et le marque dans son journal. Rien à ajouter pour l'éprouver

### 0.2 Mettre le projet en place

- [x] Emplacement — le dépôt forké est cloné dans `kaldera-bout-en-bout/`, à côté de la
      conception. Les documents et l'outillage restent **hors** du dépôt git
- [x] Environnement construit depuis le **Python 3.11 du système** *(`uv venv --python <chemin>`
      avant `uv sync`, car `_ctypes` est bloqué pour l'interpréteur téléchargé par `uv`)*
- [x] `ruff`, `pytest`, `mypy` — **le dépôt les prévoit déjà** : cibles `fmt`, `lint`,
      `typecheck`, `test` dans le `Makefile`
- [x] Pas de `.env` : les tests fournissent eux-mêmes `PARTENAIRE_URL` et `PARTENAIRE_JETON`,
      et la démonstration lance son propre partenaire. Un `.env` serait un fichier de plus à
      tenir à jour sans rien apporter. `.env.example` reste la référence
- [x] Le partenaire simulé démarre bien **dans le processus de test** — aucune erreur de
      connexion sur les 16 tests A2A, seulement des échecs d'assertion

### 0.2 bis · Documents de référence produits

- [x] [`02_arbre_decision_antifraude.md`](02_arbre_decision_antifraude.md) — la logique décisionnelle
      complète, six branches, leur couverture par les scénarios et les pièges
- [x] [`03_architecture.md`](03_architecture.md) — modules, dépendances interdites, exécution
- [x] [`04_arbitrage_modeles.md`](04_arbitrage_modeles.md) — Jev et LAYA examinés : aucun modèle
      dans le chemin de décision *(`D25`)*. **Dépassé le 9 octobre** par `D31` :
      cinq usages, trois cercles — voir [`10_doctrine_des_modeles.md`](10_doctrine_des_modeles.md)
- [x] [`05_etat_du_depot.md`](05_etat_du_depot.md) — l'état de départ mesuré, les huit écarts, et
      ce que le dépôt confirme ou corrige de la conception
- [x] [`06_harnais_et_invariants.md`](06_harnais_et_invariants.md) — ce que la suite d'acceptance
      exige vraiment, les sept invariants confrontés, et ce que le harnais ne vérifie pas
- [x] [`08_chantier_2_realise.md`](08_chantier_2_realise.md) — la liaison A2A, les quatre
      décisions `D27`–`D30`, et ce que l'épreuve a trouvé
- [x] [`09_revue_et_auto_evaluation.md`](09_revue_et_auto_evaluation.md) — les trois revues,
      les six défauts trouvés, et l'auto-évaluation
- [x] [`10_doctrine_des_modeles.md`](10_doctrine_des_modeles.md) — la réponse au challenge du
      formateur : cinq usages de modèle, une règle qui les place *(`D31`–`D34`)*
- [x] Les trois points **⚠** de l'architecture sont tranchés : séquentiel *(`D27`)*, validation
      écrite à la main *(`D28`)*, adresse configurée plutôt que carte d'agent *(`D29`)*

### 0.3 Poser les garde-fous du projet

- [x] [`journal_ajustements.md`](journal_ajustements.md) créé *(`D23`, `EX-6`)* — **neuf entrées**,
      `AJ-01` à `AJ-09`
- [x] Le modèle de qualification en trois natures y figure en tête
- [x] Numérotation reprise : `D27` à `D30` sont prises par le chantier 2, consignées dans
      [`08_chantier_2_realise.md`](08_chantier_2_realise.md)
- [x] Garder sous la main le principe qui tranche les frontières — *une règle appartient au métier
      de l'acte qu'elle produit* *(`D2`)* : toute ambiguïté découverte en codant se tranche avec lui,
      et l'arbitrage se consigne
- [x] Grille de preuve : l'épreuve des mutations associe chaque défaut connu au test qui
      l'attrape
      et à mesure

---

## 1 · Chantier 1 — l'équipe et son orchestration

> **À reprendre dès le début** : le squelette refuse une demande dont le montant déclaré dépasse le
> plafond. Les spécifications en font un **écrêtage du remboursement**, et `NOM-05` le prouve
> *(4 200 € déclarés, 3 000 € attendus)*. Le plafond appartient à l'estimation, **après** la
> franchise *(`C3`, `D3`)*.

> *Développer les agents spécialistes et leurs frontières selon la spec · mettre en place
> l'orchestration (routage, terminaison garantie, bornes provisoires anti-boucle) · mettre en place
> la mémoire partagée de la demande (état commun, accès maîtrisé).*

### 1.1 La mémoire partagée — à faire en premier

Tout le reste s'y appuie. `D7`, `D8`

- [x] Les **quatre zones** : demande d'origine *(lecture seule)*, cinq parties du dossier, zone de
      travail *(non publiée)*, journal de bord *(ajout seul)*
- [x] Les agents **ne reçoivent pas** le dossier : ils reçoivent leurs entrées et **rendent** un
      résultat *(`D7` — c'est ce qui rend l'écrasement impossible)*
- [x] Aucune structure partagée entre deux demandes *(`D8`)*
- [x] La zone de travail porte le constat d'indisponibilité et les compteurs, et **n'apparaît pas**
      dans la fiche *(`D4`)*

### 1.2 Les cinq agents métier

Un agent = un rôle = une section. `D1`, `D3`

- [x] `eligibilite` — statut, cotisations, carence, délai de déclaration, garantie. **Ne chiffre
      rien, pas même le plafond**
- [x] `pieces` — présence et lisibilité des pièces exigées, demande de complément, reprise après
      dépôt. Critère de « cohérence » limité au tableau de la section 5 *(`D3`)*
- [x] `estimation` — montant justifié, retenu, estimé. **Franchise puis plafond**, dans cet ordre
      *(`C3` — vérifié sur `NOM-05`)*
- [x] `antifraude` — calcule les quatre indicateurs, décide s'il faut consulter, et **ne publie rien**
      quand aucun contrôle n'est requis *(`D3`)*
- [x] `decision` — applique l'ordre des règles de la section 10, écrit l'issue, le motif, la file, le
      montant, le mode dégradé
- [x] Motif par **gabarit déterministe** ; la rédaction assistée reste une option non activée *(`D9`)*

### 1.3 Le répartiteur

- [x] Le **plan conditionnel** transcrit tel quel depuis l'annexe du chantier 1 *(`D5`)*
- [x] Les trois temps : déléguer → réceptionner → avancer
- [x] **Réception stricte** : la partie attendue est écrite, et rien d'autre. Sinon, refus
- [x] Le répartiteur **dépose sans être l'auteur** : le journal nomme l'agent *(`D7`)*
- [x] Le répartiteur **n'apparaît pas** dans le journal de bord *(`D12`)* ; son journal de
      routage vit dans la zone de travail, qui ne ressort pas dans la fiche
- [x] Aucun agent ne peut en appeler un autre

### 1.4 Les bornes et la terminaison garantie

`D6`, `EX-1`, `EX-6`

- [x] `bornes()` publie : `etapes_max` 10 · `duree_max_s` 8 · `pieces_tentatives_max` 3 ·
      `partenaire_delai_s` 3 · `etape_duree_max_s` 1
- [x] **Sortie ordonnée** : une borne atteinte confie une dernière main à `decision`, qui écrit une
      escalade motivée. **Jamais d'erreur** *(`D6`)*
- [x] Une étape **et** deux secondes réservées pour cette sortie
- [x] Les cinq noms d'arrêt implémentés, avec `arret.borne` renseigné — **mais seul**
      `pieces_sans_depot_restant` **est atteint par la recette** : les quatre garde-fous
      restent du code non éprouvé, à couvrir au plan d'épreuve
- [x] Toute escalade sur borne part vers le **gestionnaire** *(`D11` — règle que nous avons
- [x] Toute escalade sur borne part vers le **gestionnaire** *(`D11`)* — règle ajoutée sans
      fondement textuel, **signalée en revue** dans §7 bis de
      [`08_chantier_2_realise.md`](08_chantier_2_realise.md)
- [x] **⚠ Distinguer les deux cas des pièces** — le piège le plus coûteux :
  - [x] aucun dépôt du type demandé → **règle métier**, escalade gestionnaire, **sans** `arret`
        *(c'est `NOM-09`, un cas nominal)*
  - [x] dépôts épuisés et pièce toujours illisible → **borne**, escalade **avec** `arret`
        *(c'est `BCL-01`)*
- [x] `cloture_manquante` produit une escalade de secours **et** fait échouer la recette —
      un test vérifie qu'aucune fiche des 28 scénarios ne porte cette borne

### 1.5 L'interface publique

- [x] `traiter_demande(demande, *, partenaire_url=None) -> dict`
- [x] `traiter_lot(demandes, *, partenaire_url=None) -> {"fiches": [...], "metriques": {...}}`,
      fiches **dans l'ordre**
- [x] `bornes() -> dict`
- [x] La fiche porte les huit champs métier **plus** `trace` et `arret`
- [x] Chaque étape de `trace` porte au moins `agent` et `ecrit`

### 1.6 Tests du chantier 1

- [x] **Test d'architecture** : lire les imports et vérifier les sept dépendances interdites du
      schéma `07`. C'est `EX-2` rendu automatique — on ne vérifie plus ce que le système a fait,
      mais qu'il ne peut pas faire autrement
- [x] Les **sept invariants** d'équipe, écrits une fois, appliqués à tous les scénarios *(`D21`)*
- [x] Les 11 scénarios nominaux passent
- [x] `BCL-01` : escalade **et** `arret` signalé
- [x] `NOM-09` : escalade **sans** `arret`
- [x] Preuve que les tests savent échouer : réintroduire chaque défaut un par un, un test précis doit
      tomber pour la bonne raison

---

## 2 · Chantier 2 — la liaison A2A et l'épreuve

> *Brancher la liaison A2A (contrat respecté, filtre des données envoyées, gestion des délais,
> validation de chaque réponse) · implémenter le mode dégradé · écrire les tests d'intégration
> multi-agents et instrumenter le monitorage par agent · éprouver l'équipe et consigner chaque
> ajustement.*

### 2.1 La passerelle partenaire

Un seul point de passage. `D17`

- [x] Composant unique dans `antifraude` ; rien d'autre n'utilise l'adresse du partenaire
- [x] Les douze hypothèses **regroupées au même endroit**, chacune en commentaire numéroté *(`D13`)*
- [x] Construction de la charge **en partant de rien** — jamais un filtrage de la demande *(`D14`)*
- [x] **⚠ Confronter la liste des champs envoyés au contrat réel**
- [x] ~~Aucune date transmise~~ — **décision renversée** : le contrat **exige**
      `date_survenance`, et accepte donc que la souscription soit déductible. C'était
      l'arbitrage annoncé en conception *(`D15`, hypothèse H12)*
- [x] Jeton lu dans l'environnement, jamais en dur ni dans un journal

### 2.2 La validation des réponses

Quatre niveaux, premier échec arrête tout. `D18`

- [x] Niveau 1 · transport : réponse reçue dans le délai, service sans erreur signalée
- [x] Niveau 2 · lisibilité : message structuré, emballage conforme
- [x] Niveau 3 · forme : **validation stricte**, pas un champ de plus *(⚠ dépend du contrat)*
- [x] Niveau 4 · sens : score dans ses bornes, niveau cohérent, **réponse appariée à notre question**
- [x] **Verdict unique** en sortie : avis obtenu, ou avis non obtenu avec une cause normalisée
- [x] **Rien** du contenu rejeté ne sort de la passerelle, motif compris *(`EX-4`)*
- [x] Les causes normalisées portées par un champ libre du journal, pour être vérifiables en test
- [x] **Aucune reprise d'appel** *(`D19`)* — à rouvrir si le contrat accorde un délai plus court
- [x] **Aucun disjoncteur** *(`D20`)*

### 2.3 Le mode dégradé

`EX-5`

- [x] Trois causes d'indisponibilité → **un seul traitement**
- [x] Seuil 1 500 € sur le **montant estimé** : en deçà la demande continue, au-delà escalade
      `cellule_fraude`
- [x] `mode_degrade` posé par `decision`, jamais par `antifraude` *(`D4`)*
- [x] **⚠ Les demandes sans contrôle requis ne sont pas marquées** — `PAN-01` attend trois fiches non
      marquées sur cinq
- [x] Demandes d'un lot traitées **indépendamment** *(`D10`)* — choix technique à faire et à justifier
- [x] Vérifier qu'aucune demande n'attend au-delà du délai

### 2.4 Monitorage par agent

`EX-6`

- [x] `metriques` indexé par nom d'agent, avec `appels`, `echecs`, `latence_ms`, `appels_externes`
- [x] Définition d'`echecs` appliquée : étape refusée à la réception, ou réponse extérieure non
      retenue. Une pièce illisible n'est **pas** un échec
- [x] Les quatre signaux ajoutés : étapes consommées par demande, part en mode dégradé, **part
      rejetée pour la forme**, part arrêtée par un garde-fou
- [x] La part rejetée pour la forme est celle qui révèle que l'hypothèse sur les champs est fausse —
      ne pas l'oublier

### 2.5 Les tests d'intégration

- [x] Les 28 scénarios fournis passent
- [x] Les **18 scénarios ajoutés** écrits et passants *(`D22`)* :
  - [x] S1–S9 · trois valeurs par seuil (en dessous, **exacte**, au-dessus) sur les trois seuils les
        plus mal couverts
  - [x] S10–S11 · ce qui part chez le partenaire : liste exacte, et aucune valeur témoin
  - [x] S12 · indépendance entre demandes, lot chronométré
  - [x] S13–S14 · la borne de trois tentatives, isolée
  - [x] S15–S16 · agent hors frontière, agent défaillant
  - [x] S17–S18 · réponse juste sous le délai, score à la limite exacte
- [x] Le harnais supposé par six scénarios **existait déjà** : `partenaire.journal()` rend
      les champs transmis, le corps brut, la conformité de la requête et les doublons
- [x] Question tranchée : `S15` et `S16` sont des **contrôles internes**. Publier un motif de refus
      de réception exposerait à un gestionnaire une défaillance de code qui ne le concerne pas, et
      le contrat d'intégration ne prévoit pas ce champ
- [x] Grille de preuve : **l'épreuve des mutations en tient lieu** — 19 défauts réintroduits
      un par un, 19 détectés par un test précis

### 2.6 Éprouver, et consigner

`D23`, `D24`, `EX-6`

- [x] Rejouer les scénarios de panne, de réponse invalide et de boucle
- [x] Pour chaque échec : **constater → qualifier → écrire → appliquer → rejouer tout**
- [x] Qualification en **trois natures** : réglage de borne métier · recalcul · défaut
- [x] Une borne métier se décide **à la direction des opérations**, pas dans l'équipe
- [x] Un garde-fou ne se relève pas pour faire passer un scénario ; il se **recalcule** si une donnée
      de son calcul change
- [x] Chaque ajustement consigné **avant** mise en œuvre

---

## 3 · L'interface de visualisation

Demandée pour voir le résultat de chaque chantier. Elle se construit sur des données que le système
doit produire de toute façon : la `trace` et les `metriques`.

### 3.1 Socle commun

- [x] Mode de service **tranché** : application **Streamlit** qui rejoue en direct par la
      porte publique. Un export JSON autonome (`demo/exporter.py`) reste en repli
- [x] Lancement par **une seule commande** : `make demo` *(le `Makefile` a été repris pour
      invoquer les outils en module, leurs exécutables étant bloqués sur ce poste)*
- [x] Charger un scénario de `eval/scenarios.jsonl`
- [x] Rejouer et récupérer fiche + trace + métriques
- [x] Reprendre la palette et la typographie des schémas de conception, pour la continuité visuelle

### 3.2 Vue « flux » — le cœur de la demande

- [x] Les agents disposés comme sur la **carte des agents**, le **répartiteur** au-dessus :
      il délègue, il n'écrit pas — l'effacer laisserait croire que les agents s'enchaînent seuls
- [x] **Animation du parcours réel** : chaque étape de la trace s'allume dans l'ordre, avec le nom de
      l'agent et la partie écrite
- [x] Les sorties anticipées visibles quand elles se produisent *(non éligible, pièces manquantes,
      montant nul)*
- [x] La **reprise du contrôle des pièces** visible comme telle, avec le compteur de tentatives
- [x] Le **détour partenaire** matérialisé hors du système, avec le temps d'attente réel et le
      verdict — avis obtenu, ou non obtenu
- [x] Une **borne atteinte** signalée, et la sortie ordonnée qui suit
- [x] Lecture pas à pas possible, et pas seulement en continu

### 3.3 Vue « dossier » — l'état partagé

- [x] Les quatre zones de la mémoire, et leur remplissage au fil des étapes
- [x] Qui a écrit quoi, et quand — c'est la démonstration visuelle de `EX-2`
- [x] La zone de travail affichée **distinctement**, pour montrer qu'elle ne sort pas dans la fiche

### 3.4 Vue « échange A2A » — chantier 2

- [x] Ce qui part réellement chez le partenaire, champ par champ *(démonstration de `EX-3`)*
- [x] Les quatre niveaux de validation, et **à quel niveau une réponse est tombée**
- [x] Le chemin du mode dégradé quand il se déclenche
- [x] Pilotage du partenaire simulé depuis l'interface : normal · lent · panne · chaque variante
      invalide

### 3.5 Vue « lot et mesures »

- [x] Traitement d'un lot, avec les fiches dans l'ordre
- [x] Les quatre mesures par agent *(les quatre signaux ajoutés relèvent du chantier 2)*
- [x] **Montrer que trois fiches sur cinq ne sont pas marquées** pendant une panne — la démonstration
      la plus parlante du mode dégradé

### 3.6 La démonstration dit-elle la vérité ?

- [x] Les vues sont **séparées de l'application** (`demo/vues.py`) pour être testables
- [x] Chaque motif produit se rattache à une règle de la section 10 — sinon l'arbre
      n'allumerait rien
- [x] Chaque agent du journal figure au schéma — sinon une étape disparaîtrait
- [x] Le rendu tient à **chaque instant** du parcours, sur les 28 scénarios
- [x] La page entière s'exécute sans exception sur un échantillon de six scénarios

---

## 3 bis · Le client externe — **optionnel**

Un agent qui joue un **courtier** déposant des demandes pour ses clients. Il n'est pas demandé par
le brief : il se fait **après** le chantier 2 et l'interface, et seulement si le temps le permet.
Ce qu'il apporte : Kaldera devient *fournisseur* A2A après avoir été *client*, et la minimisation
des données devient visible — on voit un nom entrer, et on le voit ne pas sortir.

### 3bis.1 La condition bloquante

- [x] **Vérifier la forme de la porte publique dans `docs/interface.md`.** Si le contrat
      d'intégration impose des fonctions, exposer un point d'entrée A2A est du travail en plus,
      **non demandé** — et le client externe devient un bonus coûteux, à arbitrer
- [x] Si le coût est confirmé : trancher explicitement entre un client qui parle **en A2A** (le
      gain de démonstration) et un client qui appelle la porte publique **directement** (presque
      gratuit, mais démontre moins)

### 3bis.2 Ce qu'il fait, et où il vit

- [x] Il vit dans **`demo/client_externe/`**, hors du paquet `kaldera` — même contrainte que
      l'interface : **s'il a besoin d'autre chose que la porte publique, c'est la porte publique qui
      est insuffisante**
- [x] Il **traduit seulement** : déclaration libre → les champs d'une demande. Jamais de décision,
      jamais de jugement sur le dossier *(`D25` reste vrai : le modèle est hors du système)*
- [x] Il porte des **données personnelles crédibles** — nom, adresse, téléphone — pour que le
      filtre ait quelque chose à filtrer *(démonstration de `EX-3`)*
- [x] Données **fictives uniquement**, et aucune clé d'API dans le dépôt

### 3bis.3 Rester reproductible

- [x] La demande structurée **s'affiche et se valide** avant l'envoi — un modèle qui traduit
      différemment à chaque exécution est un risque en démonstration publique
- [x] Pas de bouton dédié, mais le résultat est le même : **l'extraction déterministe est le
      défaut**, la bascule vers le modèle est explicite et désactivée sans clé configurée. La
      démonstration fonctionne modèle indisponible — un test le vérifie
- [x] **Jamais sur le chemin des tests d'acceptance** — ceux-là entrent par la porte publique,
      directement. Un test le vérifie si le client parle en A2A

### 3bis.4 Ce que l'interface en montre

- [x] La déclaration libre, la demande produite, et **ce que le filtre retient** — côte à côte
- [x] Le nom et l'adresse visibles à l'entrée, **absents** de la charge envoyée au partenaire

---

## 4 · Livrables attendus

- [x] **Dossier de conception** — *fait, validé* : carte des agents, orchestration et mémoire
      partagée, A2A et mode dégradé, plan d'épreuve
- [x] **L'équipe d'agents fonctionnelle**, avec mémoire partagée et collaboration A2A
- [x] **Les tests d'intégration multi-agents**
- [x] **Le monitorage par agent**
- [x] **Le journal des ajustements d'orchestration**
- [x] **La preuve d'exécution des tests d'acceptance** — `kaldera-bout-en-bout/preuves/`
      `acceptance.txt`, datée, avec la suite complète et l'épreuve des mutations
- [x] *(ajout)* **L'interface de visualisation**, et la façon de la lancer
- [x] *(optionnel, non demandé)* **Le client externe de démonstration** — voir 3 bis

---

## 5 · Critères de sortie

Le chantier n'est pas fini tant que ces cinq lignes ne sont pas vraies **et démontrées**.

- [x] **Tous les tests d'acceptance fournis passent**
- [x] **Les six exigences sont respectées et démontrées** — pour chacune, le contrôle automatique
      décrit à l'étape 1 tourne et passe
- [x] **La collaboration A2A respecte le contrat**, valide les réponses, et **n'envoie que des
      données autorisées** *(les deux contrôles S10 et S11 passent)*
- [x] **Le mode dégradé préserve le service** quand le partenaire est indisponible, et **le piège à
      boucle s'arrête dans les bornes**
- [x] **Les bornes et frontières finales sont justifiées par l'épreuve**, scénarios rejoués à
      l'appui, et **chaque ajustement est consigné** — pas de réglage au doigt mouillé

### Préparation de l'évaluation

- [x] Revue d'architecture — la carte des agents et le plan de routage **s'affichent depuis
      le code** ; onze frontières vérifiées par 23 tests sur les imports
- [x] Revue de code — **six défauts trouvés et corrigés**, couverture de 90 % à **96 %**,
      `cli.py` de 0 % à couvert, les quatre garde-fous enfin éprouvés
- [x] Auto-évaluation face aux neuf critères du brief, avec ce qui les prouve — dans
      [`09_revue_et_auto_evaluation.md`](09_revue_et_auto_evaluation.md). La co-évaluation
      reste à mener avec un pair
- [x] Journal de fin de session à chaque séance de développement

---

## À confirmer avant de démarrer

**Une seule question reste ouverte**, et elle appartient au métier. Les deux autres ont
été tranchées — l'une le 7 octobre, l'autre le 12.

|       | Question                                                                                                           | Pourquoi cela compte                                                                                                                                                                                                          |
| ----- | ------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ~~1~~ | ~~Page statique ou application locale ?~~ **Répondu** : application Streamlit                                      | Tranché le 7 octobre                                                                                                                                                                                                          |
| ~~2~~ | ~~À la fin, ou en continu ?~~ **Répondu** : elle suit chaque chantier                                              | Tranché le 7 octobre                                                                                                                                                                                                          |
| ~~3~~ | ~~Le récit de l'assuré peut-il partir chez un modèle hébergé ?~~ **Répondu** : non                                 | Tranché le 12 octobre. Le drapeau qui pouvait l'ouvrir est retiré, et un test garde qu'il ne revienne pas *(`D32`)*                                                                                                           |
| 4     | La « cohérence » des pièces : le métier veut-il un signalement quand la facture ne couvre pas le montant déclaré ? | La recette répond déjà **non** pour les trois cas qu'elle porte — `NOM-08` (−5 %), `AF-06` (−25 %), `INV-06` (−29 %), tous attendus `acceptee` sans escalade. La question ne vaut que si le métier veut changer cette réponse |
