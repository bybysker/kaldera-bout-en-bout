# Chantier 2 réalisé — la liaison A2A et l'épreuve du réel

Brief Kaldera · Phase DÉVELOPPEMENT · 9 octobre 2026

Les quatorze tests rouges du chantier 1 sont verts. Ce document dit ce qui a été construit, les
quatre décisions prises en chemin, et ce que l'épreuve a trouvé.

---

## En bref

- **486 tests passent, aucun n'échoue.** Les 56 tests d'acceptance fournis, dont les 16 tests A2A
  qui n'en passaient aucun.
- **19 défauts réintroduits un par un, 19 détectés** par un test précis.
- **Un défaut réel trouvé par un scénario ajouté** : un agent qui lève une exception privait la
  demande de son issue. Corrigé, consigné.
- **Quatre décisions** prises en chemin, `D27` à `D30`, dont deux qui tranchent des points laissés
  ouverts depuis l'architecture.

---

## 1 · Ce qui a été construit

```
src/kaldera/partenaire/
├── passerelle.py     le seul point qui connaît l'adresse et le jeton · les 12 hypothèses
├── charge.py         les sept champs, construits en partant de rien
├── validation.py     les quatre niveaux, premier échec arrête tout
├── registre.py       un seul appel par dossier
└── erreurs.py        quinze causes normalisées, et leur niveau
```

**La charge se construit en partant de rien** (`D14`). La différence avec un filtre n'est pas
théorique : un test ajoute deux champs à la demande — `scoring_interne` et un commentaire de
gestionnaire — et vérifie qu'ils ne partent pas. Un filtre les aurait laissés passer.

**Le département est dérivé du code postal**, jamais recopié : le code postal complet fait partie
des coordonnées que le contrat interdit « sous quelque forme que ce soit ». Le partenaire l'impose
d'ailleurs par sa propre validation — deux caractères, ou `2A`/`2B`, ou trois chiffres outre-mer.

**Les douze hypothèses de conception sont réunies en tête de `passerelle.py`**, avec leur verdict
après confrontation au contrat (`D13`). Les relire le jour où le contrat change coûte alors une
minute.

---

## 2 · Les quatre décisions

|         | Décision                                                          | Pourquoi                                                                                                                                                                                                                                                                                                                                                                                         |
| ------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **D27** | **Traitement séquentiel du lot**, pas de concurrence              | La lecture du harnais avait montré qu'un traitement séquentiel passe la recette. Reste à démontrer que l'engagement de service tient : le scénario `S12` borne le **lot entier** — trois demandes, partenaire lent à 5 s — là où le harnais fourni accorde 10 s par demande. Avec l'abandon à 3 s, le lot tient largement. La concurrence resterait à justifier par une mesure, pas par principe |
| **D28** | **Validation écrite à la main**, pas de bibliothèque              | Une bibliothèque de validation accepte les champs en trop par défaut ; il faudrait le désactiver explicitement, et se souvenir de l'avoir fait. Or le rejet d'un champ en trop est **le pari le plus risqué** de la conception. Vingt lignes lisibles valent mieux qu'une option à ne pas oublier                                                                                                |
| **D29** | **Pas de découverte par *Agent Card*** ; l'adresse est configurée | Le simulateur sert bien la carte, et le contrat la prévoit. Mais rien dans le contrat d'intégration n'impose de la lire, et elle ajouterait un appel réseau — donc un point de défaillance — avant chaque consultation. Choix écrit, à rouvrir si l'adresse devient variable                                                                                                                     |
| **D30** | **Une défaillance d'agent produit une sortie ordonnée**           | Voir §4 : c'est le défaut que l'épreuve a trouvé                                                                                                                                                                                                                                                                                                                                                 |

---

## 3 · Les quatre niveaux de validation

| Niveau             | Ce qu'il vérifie                                                         | Causes possibles                                                                  |
| ------------------ | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| **1 · transport**  | Reçue dans les 3 s, sans erreur du service                               | délai dépassé · service indisponible · authentification refusée · erreur réseau   |
| **2 · lisibilité** | JSON lisible, enveloppe JSON-RPC conforme, une seule partie `data`       | corps illisible · enveloppe non conforme · erreur RPC                             |
| **3 · forme**      | **Exactement** les six champs, aux bons types                            | champs en trop · champs absents · types invalides                                 |
| **4 · sens**       | Score dans `[0 ; 1]`, niveau cohérent avec le score, **dossier apparié** | score hors bornes · niveau incohérent · dossier différent · identifiant différent |

**Le quatrième est celui qu'on oublie.** Une réponse peut être authentifiée, bien formée, dans les
délais — et porter sur le dossier du voisin. Le protocole sécurise le canal, pas le sens.

**Un seul verdict sort de la passerelle** : avis obtenu, ou avis non obtenu avec sa cause. Rien du
contenu rejeté ne la traverse, pas même dans un motif — sinon un gestionnaire le lirait comme un
avis.

---

## 4 · Ce que l'épreuve a trouvé

**Un agent défaillant privait la demande de son issue.** Le scénario ajouté `S16` remplace un agent
par un agent qui lève une exception. L'erreur remontait jusqu'à l'appelant : aucune fiche n'était
produite, la demande disparaissait.

C'est une violation de `EX-1` et de la section 2 des spécifications — *« une demande ne reste jamais
en attente sans qu'un humain en ait été saisi »*. Aucun des 28 scénarios fournis ne pouvait le
trouver : ils n'exercent que des agents qui fonctionnent.

**Qualification : défaut.** Aucune borne en cause. Le répartiteur attrape maintenant la
défaillance, la journalise comme une étape en échec, et confie une dernière main à l'agent de
décision. Le détail est dans [`journal_ajustements.md`](journal_ajustements.md), entrée `AJ-01`.

Une seconde entrée, `AJ-02`, consigne un conflit de nommage entre le registre d'appels et le
dossier — résolu en renommant plutôt qu'en affaiblissant le test d'architecture.

---

## 5 · Les tests ajoutés

**Dix-huit scénarios** que les 28 fournis ne couvrent pas, répartis en quatre fichiers :

| Fichier                  | Scénarios | Ce qu'ils éprouvent                                                                                                                            |
| ------------------------ | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `test_seuils.py`         | S1–S9     | Trois valeurs par seuil — **dessous, exacte, dessus** — sur les trois seuils que la mesure de sensibilité désignait comme les moins bien tenus |
| `test_charge_envoyee.py` | S10–S11   | La liste exacte des champs, et qu'aucune valeur personnelle n'atteint le partenaire                                                            |
| `test_robustesse.py`     | S12–S18   | Indépendance du lot, borne de tentatives, agent hors frontière, agent défaillant, délai, score aux limites                                     |
| `test_registre.py`       | —         | Un seul appel par dossier, et un registre qui ne traverse pas les demandes                                                                     |

**Le harnais supposé manquant existait déjà.** La conception annonçait que six de ces scénarios
demanderaient un outillage à construire. La lecture du dépôt a montré que `partenaire.journal()`
rend déjà les champs transmis, le corps brut, la conformité de la requête et les doublons. Rien
n'a eu à être écrit.

**Une question laissée ouverte est tranchée.** `S15` et `S16` entrent par le répartiteur plutôt que
par la porte publique : publier un motif de refus de réception dans la fiche exposerait à un
gestionnaire une défaillance de code qui ne le concerne pas, et le contrat d'intégration ne prévoit
pas ce champ.

---

## 6 · Les quatre signaux ajoutés

`traiter_lot` rend désormais `signaux` à côté de `metriques` :

| Signal                    | Ce qu'il dit                                            |
| ------------------------- | ------------------------------------------------------- |
| `etapes_par_demande`      | La longueur moyenne d'un parcours                       |
| `part_mode_degrade`       | La part de demandes traitées sans avis                  |
| **`part_rejet_de_forme`** | **La part rejetée pour sa forme**                       |
| `part_garde_fou`          | La part arrêtée par un garde-fou — devrait rester nulle |

Le troisième est le moins évident et le plus utile : **s'il monte, c'est notre lecture du contrat
qui dérive, pas le partenaire qui tombe**. Sans lui, on chercherait la panne du mauvais côté.

Ils vivent à côté des mesures plutôt que dedans, parce que `metriques` est indexé par nom d'agent :
y glisser une clé qui n'est pas un agent casserait l'invariant `I7`.

---

## 7 · L'état mesuré

|                     | Fin du chantier 1 | Maintenant  |
| ------------------- | ----------------- | ----------- |
| Tests passants      | 332               | **486**     |
| Tests en échec      | 14                | **0**       |
| Suite d'acceptance  | 42 / 56           | **56 / 56** |
| Suite A2A           | 2 / 16            | **16 / 16** |
| Mutations détectées | 13 / 13           | **19 / 19** |

La preuve d'exécution datée est dans `kaldera-bout-en-bout/preuves/acceptance.txt`.

**`mypy` n'a pas pu être relancé** : son extension native est désormais bloquée par la stratégie de
contrôle d'application du poste, comme pandas. Le dernier passage, au chantier 1, ne signalait rien
sur 25 fichiers. `ruff` passe.

---

## 7 bis · À soumettre en revue

Trois points que l'équipe a tranchés seule, et qui mériteraient un avis extérieur. Les signaler
était un engagement pris en conception.

| Point                                                         | Ce qui a été fait                             | Pourquoi en parler                                                                                                                                                                                                    |
| ------------------------------------------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`D11`** — toute escalade sur borne part au **gestionnaire** | Appliqué partout                              | **Aucun texte ne le fonde.** Les spécifications nomment une file pour chaque situation métier, aucune pour une borne d'exécution atteinte. Le choix du gestionnaire plutôt que de la cellule anti-fraude est le nôtre |
| **`D29`** — pas de découverte par *Agent Card*                | Adresse configurée par `PARTENAIRE_URL`       | Le contrat partenaire la prévoit explicitement. Ne pas l'utiliser est défendable, mais c'est s'écarter de ce que le partenaire propose                                                                                |
| Le critère de **« cohérence »** des pièces                    | Réduit au tableau des pièces exigées *(`D3`)* | La spécification emploie le mot sans le définir. Notre lecture est la plus étroite possible ; le métier en attend peut-être davantage                                                                                 |

---

## 8 · Ce qui reste

- Le **client externe** de démonstration — optionnel, non demandé par le brief.
- La **revue d'architecture et de code** avant soutenance.
- La question du **critère de « cohérence »** des pièces, à poser au formateur : elle rouvrirait
  rendrait exploitable l'avis de cohérence du relecteur, aujourd'hui consultatif
  *(`D31`)*.

---

*Le point de départ est dans [`05_etat_du_depot.md`](05_etat_du_depot.md), le chantier 1 dans
[`07_chantier_1_realise.md`](07_chantier_1_realise.md), et les ajustements dans
[`journal_ajustements.md`](journal_ajustements.md).*
