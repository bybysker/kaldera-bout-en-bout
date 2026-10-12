# Journal des ajustements d'orchestration

Brief Kaldera · Phase DÉVELOPPEMENT

Tout écart constaté à l'épreuve se consigne **avant** sa mise en œuvre, et se qualifie en trois
natures (décisions `D23`, `D24`) :

| Nature                      | Ce que c'est                                                                       | Qui décide                                                |
| --------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------- |
| **Réglage de borne métier** | Une valeur qui engage le service rendu — le nombre de chances laissées à un assuré | La direction des opérations, pas l'équipe                 |
| **Recalcul**                | Un garde-fou dont une donnée du calcul a changé                                    | L'équipe, en montrant le calcul                           |
| **Défaut**                  | Un comportement imprévu                                                            | L'équipe : on corrige le code, on ne déplace pas la borne |

Un garde-fou **ne se relève jamais** pour faire passer un scénario.

---

## AJ-01 · Un agent défaillant privait la demande de son issue

**Constaté le** 9 octobre 2026, par le scénario ajouté `S16`.

**Ce qui se passait.** Lorsqu'un agent levait une exception — un défaut de code, pas un cas
métier — l'erreur remontait jusqu'à l'appelant de `traiter_demande`. La demande ne produisait
aucune fiche : elle disparaissait.

**Pourquoi aucun test ne le voyait.** Les 28 scénarios fournis n'exercent que des agents qui
fonctionnent. Le harnais d'acceptance borne la durée d'un traitement, pas sa capacité à survivre
à un défaut interne.

**Ce que cela contredit.** Les spécifications, section 2 : *« Une demande est traitée lorsqu'elle
a reçu une issue. Il n'existe pas d'autre état final : une demande ne reste jamais "en attente"
sans qu'un humain en ait été saisi. »* Et l'exigence `EX-1`.

**Qualification : défaut.** Aucune borne n'est en cause, aucune donnée de calcul n'a changé. Le
code ne faisait pas ce qu'il devait faire.

**Correction appliquée.** Le répartiteur attrape la défaillance d'un agent, la journalise comme
une étape en échec, et bascule en **sortie ordonnée** : l'agent de décision écrit une escalade
vers le gestionnaire, et la fiche signale l'arrêt sous le nom `agent_defaillant`. Le motif reste
lisible pour le gestionnaire — *« Traitement interrompu : incident technique, reprise manuelle »* —
sans exposer la défaillance technique, qui ne le concerne pas.

La même protection couvre la sortie ordonnée elle-même : si l'agent de décision tombe à son tour,
l'escalade de secours `cloture_manquante` prend le relais.

**Vérifié.** `S16` passe, et toute la suite avec lui. Une mutation de l'épreuve
réintroduit le défaut et vérifie que `S16` tombe.

**Ce que cela coûte.** Un nom d'arrêt de plus, et une branche d'exception dans le répartiteur. Le
comportement nominal est inchangé : aucune des 482 autres vérifications n'a bougé.

---

## AJ-02 · Le registre d'appels portait un nom réservé au dossier

**Constaté le** 9 octobre 2026, par le test d'architecture, à l'ajout de la passerelle.

**Ce qui se passait.** `Registre.noter()` déclenchait la règle « seul le répartiteur écrit dans le
dossier », qui détecte les appels par nom de méthode.

**Qualification : défaut de nommage**, pas d'architecture — la passerelle n'écrivait rien dans le
dossier.

**Correction appliquée.** `Registre.noter` devient `Registre.marquer`. Le test d'architecture
garde sa détection par nom de méthode, qui est ce qui le rend robuste, et dit désormais
explicitement que `publier`, `noter`, `journaliser` et `signaler_arret` sont réservés au dossier.

**L'autre voie était d'affaiblir le test** en ne visant que les appels sur une variable nommée
`dossier`. Elle a été écartée : la mutation « un agent écrit directement dans le dossier » n'aurait
plus été détectée.

---

## AJ-03 · Deux dossiers de tests se masquaient leur `conftest`

**Constaté le** 9 octobre 2026, lors d'un audit du dossier — pas par un test.

**Ce qui se passait.** `pytest tests/acceptance tests/chantier_2` échouait à la collecte :
*« cannot import name CHAMPS_CONTRAT from conftest »*. Pytest expose chaque `conftest.py` sous le
nom de module `conftest` ; trois dossiers de tests en portaient un, et la suite d'acceptance —
qui fait `from conftest import ...` — se voyait servir le mauvais.

**Pourquoi la suite complète passait quand même.** L'ordre de collecte décidait du gagnant :
`pytest -q` seul mettait `acceptance` en tête, et tout fonctionnait. Le défaut n'apparaissait que
sur certaines combinaisons d'arguments.

**Qualification : défaut.** Un harnais dont le résultat dépend de l'ordre des arguments n'est pas
un harnais sur lequel on peut s'appuyer, et c'est exactement le genre de panne qu'on découvre en
soutenance.

**Correction appliquée.** `tests/chantier_1/` et `tests/chantier_2/` deviennent des **paquets**
— un `__init__.py` chacun — ce qui rend leurs modules uniques. L'outillage partagé sort du
`conftest.py` vers un module au nom propre, `harnais_c1.py` et `harnais_c2.py`, importé en
relatif. Les tests d'acceptance fournis par le brief ne sont pas touchés.

**Vérifié** sur six combinaisons d'arguments, dont les deux qui échouaient : toutes passent.

---

## AJ-04 · Un test qui passait sans que le modèle réponde

**Constaté le** 9 octobre 2026, en branchant le modèle au client externe.

**Ce qui se passait.** Les cinq tests qui notent l'extraction assistée passaient. Le modèle, lui,
échouait à chaque appel : l'extraction tombait sur le **repli déterministe**, qui donne le même
résultat sur des récits simples. Le test ne vérifiait que le résultat, jamais qui l'avait produit.

**Pourquoi c'est grave.** Un test vert sur un composant en panne est pire qu'une absence de test :
il interdit de chercher. Sans la curiosité d'aller voir ce que le modèle rendait vraiment, le
dossier aurait affirmé qu'un modèle fonctionne alors qu'il ne répondait pas.

**Qualification : défaut de test.**

**Correction appliquée.** Le test vérifie d'abord `extracteur == "modèle"` et l'absence
d'incertitude mentionnant un échec. Il échoue désormais quand le modèle ne répond pas — ce qu'il
a immédiatement fait.

---

## AJ-05 · Le mauvais protocole derrière la bonne clé

**Constaté le** 9 octobre 2026, une fois `AJ-04` corrigé.

**Ce qui se passait.** Le modèle renvoyait *« API version not supported »* quelle que soit la
version d'API essayée — cinq ont été testées.

**La cause réelle.** L'endpoint se termine par `/openai/v1` : c'est une API **compatible
OpenAI**, pas Azure AI Inference. Le client fourni par le dépôt (`AzureAIChatCompletionsModel`)
parle l'autre protocole. Le message d'erreur désignait la version d'API, c'est-à-dire tout sauf
la cause.

**Qualification : défaut.** Le code supposait une famille d'endpoints sans le vérifier.

**Correction appliquée.** La fabrique **regarde l'adresse** : un chemin finissant par `/v1` donne
un client OpenAI, sinon Azure AI Inference. Et un second réglage était nécessaire — Kimi est un
modèle de raisonnement : avec dix jetons de sortie, il consomme tout en réflexion et renvoie une
réponse **vide, sans erreur**. La limite est portée à 3 000.

---

## AJ-06 · Le modèle rendait la suite instable

**Constaté le** 9 octobre 2026, sur une exécution complète.

**Ce qui se passait.** Un test du modèle a échoué une fois, deux minutes après avoir réussi. Huit
essais consécutifs sur le même récit ont ensuite donné huit résultats identiques : l'échec était
ponctuel, lié au service.

**Pourquoi on ne peut pas s'en accommoder.** Le brief demande une suite **reproductible**. Un test
qui échoue une fois sur vingt oblige à relancer pour savoir, et personne ne distingue plus un vrai
défaut d'un aléa.

**Qualification : défaut de conception du test**, pas du modèle.

**Correction appliquée.** Les tests qui appellent un modèle réel portent le marqueur `modele` et
sont **écartés par défaut**. Ils se lancent à la demande par `make modele`. La suite reste
reproductible ; la mesure du modèle reste disponible.

**Ce que cela démontre.** `D25` tenait par le raisonnement ; c'en est la vérification pratique.
Un modèle dans le chemin de décision aurait rendu les tests d'acceptance instables — ici il n'a
suffi que d'un composant hors du système pour que cela se produise.

---

## AJ-07 · Un jeu de test aligné sur ce que le code savait faire

**Constaté le** 9 octobre 2026, en comparant les deux extracteurs.

**Ce qui se passait.** Sur *« On m'a cambriolé hier, effraction par la fenêtre »*, l'attendu du
jeu était « type indéterminé ». Les règles ne tranchent pas, parce que « cambriolé » et
« fenêtre » évoquent deux natures. Le modèle répondait `vol` — **et il avait raison** : la
fenêtre est le moyen d'entrée, le sinistre est un vol.

**Pourquoi c'est grave.** L'attendu avait été écrit d'après le comportement des règles. Un jeu de
test qui fige l'existant ne mesure plus rien : il transforme chaque limite en norme, et pénalise
ce qui fait mieux.

**Qualification : défaut de méthode.**

**Correction appliquée.** L'attendu devient **métier** — `vol`. Les récits où les règles ne
peuvent pas y arriver portent une clé `limite_des_regles`, qui dit explicitement où elles
échouent. Un test garde cette honnêteté : si plus aucun récit ne mettait les règles en défaut, le
jeu cesserait de mesurer l'apport du modèle.

**Mesure après correction** — règles **14 / 15**, modèle **15 / 15**. L'unique écart est la limite
assumée des règles.


---

## AJ-08 · Un échec vu une seule fois, et qui ne se reproduit pas

**Constaté le** 9 octobre 2026, sur une exécution complète de la suite.

**Ce qui s'est passé.** `test_echange_antifraude_respecte_le_contrat…[AF-01]` a échoué **une
fois**. Relancée, la suite est repassée entièrement. Un test qui échoue sans raison visible est
exactement ce que ce projet refuse par ailleurs : il rend toute la suite suspecte.

**Ce qui a été mesuré, plutôt que supposé.**

| Vérification                                               | Résultat                           |
| ---------------------------------------------------------- | ---------------------------------- |
| Suite complète relancée trois fois                         | **720, 720, 721 — toutes vertes**  |
| Le fichier d'acceptance A2A relancé huit fois, sous charge | **128 passages, aucun échec**      |
| Durée réelle d'un aller-retour partenaire (n = 60)         | médiane **370 ms**, max **413 ms** |
| Borne d'abandon de la passerelle                           | **3 000 ms**                       |

La marge est d'un facteur **7** entre le pire cas mesuré et la borne. Franchir les 3 secondes
suppose un gel du poste de plus de 2,6 s — possible, mais non observé.

**Qualification : cause non établie.** Elle est écrite telle quelle, parce qu'affirmer une cause
non vérifiée serait pire que l'admettre.

**Correction appliquée.** Le test ne dira plus seulement qu'il a échoué. Quand le partenaire a
répondu `200` mais que la fiche ne retient aucun avis, le message nomme les deux seules causes
possibles — abandon au-delà de 3 s, ou réponse écartée à la validation — et affiche
`mode_degrade`. La prochaine occurrence sera diagnostiquée en lisant le message, pas en
relançant.

**Ce qui reste ouvert.** Si l'échec revient, la trace dira laquelle des deux branches a joué. Tant
qu'il ne revient pas, il n'y a rien à corriger d'autre.

---

## AJ-09 · Un chiffre juste le jour où on l'écrit

**Constaté le** 9 octobre 2026, en relisant l'espace technique de la démonstration.

**Ce qui se passait.** L'interface affichait « **686** tests reproductibles ». La suite en
comptait **720**. Le chiffre avait été juste, puis les chantiers ont continué sans lui.

**Pourquoi c'est grave.** C'est une démonstration destinée à un jury. Un compteur faux ne se
remarque pas — il se croit. Et l'écart ne joue pas dans le bon sens : il sous-estime le travail
tout en prouvant que rien ne le vérifie.

**Qualification : défaut de méthode** — une valeur écrite à la main dans un support qui se veut
une preuve.

**Correction appliquée.** Le nombre devient la constante `TESTS_REPRODUCTIBLES`, et un test
compare sa valeur au nombre **réellement collecté** par `pytest --collect-only`. Les deux ne
peuvent plus diverger en silence : le jour où un test est ajouté, c'est la suite qui réclame la
mise à jour.

**Ce que cela généralise.** Les trois autres cases de la même rangée étaient écrites en dur de
la même façon. Deux sont désormais vérifiées par le même test — **56** tests d'acceptance
collectés, **19** mutations définies. La quatrième, la couverture, ne peut l'être sans lancer
`coverage` à chaque démarrage de l'interface : elle est **datée** à la place, et la date se lit
au survol. Un chiffre affiché est soit confronté à ce qu'il décrit, soit daté ; jamais ni l'un ni
l'autre.

---

## AJ-10 · La même subtilité apprise à trois endroits

**Constaté le** 9 octobre 2026, en recensant les points d'intégration des modèles.

**Ce qui se passait.** `src/kaldera/llm.py` — la fabrique héritée du squelette — n'était importée
par personne. Pendant ce temps, trois modules construisaient chacun leur client : le relecteur,
les aides au gestionnaire, la prise de déclaration du cabinet. Trois copies de la même
subtilité :

| Forme de l'adresse    | Protocole          | Client qui convient           |
| --------------------- | ------------------ | ----------------------------- |
| `…/openai/v1`, `…/v1` | compatible OpenAI  | `openai.OpenAI`               |
| `…/models`            | Azure AI Inference | `AzureAIChatCompletionsModel` |

Envoyer l'un à l'autre produit un *« API version not supported »* qui ne désigne pas la cause —
c'est `AJ-05`, et il avait coûté une soirée. Trois copies, c'est trois endroits où le réapprendre.

**Pourquoi c'est grave.** Les trois copies avaient déjà divergé : les jetons n'étaient bornés que
sur la branche OpenAI, le délai d'abandon valait 30 s ici, 60 s là, rien ailleurs. Une
divergence silencieuse entre trois copies d'un même code n'est pas une duplication, c'est trois
comportements différents qui se croient identiques.

**Qualification : défaut de conception.**

**Correction appliquée.** `src/kaldera/llm.py` devient la fabrique unique. Elle rend `None`
plutôt que de lever, elle ne lit **aucun fichier** — c'est à l'application de charger son
`.env`, pas à la bibliothèque — et les bornes (jetons, délai, température) sont posées par
l'appelant à chaque appel.

**Ce qui a demandé une décision.** Le cabinet de courtage de `demo/client_externe/` ne peut pas
importer `kaldera.llm` : un test garde qu'il n'accède qu'à la **porte publique** du système, et
c'est précisément ce qu'il démontre. Plutôt que d'affaiblir ce test, le cabinet **reçoit** son
fournisseur de modèle de celui qui le configure — ce qu'un tiers fait dans la réalité. La
duplication disparaît sans que la frontière recule.

**Vérifications.** Treize tests neufs : le bon client pour chaque forme d'adresse, l'absence de
levée, les bornes réellement transmises, et le fait que la fabrique ne lit aucun fichier. Le
garde-fou « aucun agent n'importe la fabrique » a été éprouvé par mutation — import ajouté dans
`agents/decision.py`, test tombé, import retiré, test repassé.

---

## AJ-11 · Quatre suggestions sur dix revenaient tronquées, et personne ne le savait

**Constaté le** 9 octobre 2026, en mesurant pour de bon des latences qui étaient estimées.

**Ce qui se passait.** Le tableau des cinq usages annonçait « ~5 s » pour la synthèse et « ~7 s »
pour l'aide à la décision. Ces chiffres n'avaient jamais été mesurés : ils étaient repris de la
revue. La mesure réelle a donné autre chose — et a fait tomber un défaut avec elle.

| Usage               | n   | médiane | max     | exploitable à 4 000 jetons |
| ------------------- | --- | ------- | ------- | -------------------------- |
| Synthèse de dossier | 10  | 9,12 s  | 13,15 s | 10 / 10                    |
| Aide à la décision  | 10  | 20,61 s | 27,21 s | **6 / 10**                 |

**La cause, vérifiée plutôt que supposée.** Les appels ont été rejoués en lisant la réponse
brute : `finish_reason = "length"`. Le modèle de raisonnement consommait **4 000 jetons** — le
plafond — avant d'avoir fini d'écrire son JSON. L'appelant ne voyait qu'un `ValueError` qui ne
désignait rien.

Le même essai à **8 000 jetons** : cinq dossiers sur cinq aboutissent, 4 386 jetons de sortie au
pire. La marge réelle était de 400 jetons, pas de zéro — c'est pire qu'une erreur franche, parce
que cela passe la plupart du temps.

**Qualification : défaut de conception**, doublé d'un **défaut de méthode** — un chiffre affiché
sans avoir été mesuré.

**Pourquoi rien ne l'avait vu.** Les neuf tests des deux aides emploient des doubles. Un double
rend le JSON qu'on lui demande de rendre : il ne peut pas manquer de jetons. **Aucun test ne les
appelait contre le modèle réel.** C'est la lacune qui a laissé passer le défaut, et c'est elle
qui est comblée.

**Corrections appliquées.**

1. Le plafond passe à **8 000 jetons** pour les aides et pour la revue.
2. La troncature est **nommée** : `kaldera.llm.tronquee()` lit `finish_reason` quelle que soit la
   famille de client, et la cause rendue devient « réponse tronquée : le plafond de jetons a été
   atteint ». Un échec qui se nomme se corrige ; un `ValueError` se relance.
3. Deux tests marqués `modele` : l'un force un plafond de 16 jetons et exige que la cause dise
   « tronquée », l'autre vérifie que les deux aides aboutissent contre le modèle réel.

**Mesure après correction**, même protocole — dix appels par usage, cinq dossiers répétés deux
fois :

| Usage                            | n   | min    | médiane | p90     | max     | exploitable |
| -------------------------------- | --- | ------ | ------- | ------- | ------- | ----------- |
| Prise de déclaration             | 10  | 2,51 s | 5,09 s  | 9,36 s  | 12,71 s | 10 / 10     |
| Revue de fond, cohérence incluse | 10  | 5,56 s | 8,97 s  | 11,64 s | 12,76 s | 10 / 10     |
| Synthèse de dossier              | 10  | 7,68 s | 12,49 s | 22,25 s | 23,14 s | 10 / 10     |
| Aide à la décision               | 10  | 8,07 s | 18,35 s | 29,60 s | 35,49 s | 10 / 10     |

**Quarante appels, quarante exploitables.** Et une conséquence pour la doctrine : dix-neuf de ces
quarante appels dépassent à eux seuls l'engagement de dix secondes. Le premier cercle de `D31`
n'en ressort pas affaibli — il en ressort chiffré.
