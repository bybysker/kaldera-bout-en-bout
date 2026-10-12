# Confrontation du contrat partenaire aux douze hypothèses

Brief Kaldera · Phase DÉVELOPPEMENT · 7 octobre 2026

Le contrat d'échange du partenaire a été fourni : **version 2.0, en vigueur depuis le
1er septembre 2026**, remplaçant une version 1.4. Ce document le confronte aux douze hypothèses
posées au chantier 2, une par une, et en tire ce qui change.

---

## En bref

- **Onze hypothèses sur douze sont confirmées.** La douzième est à nuancer, pas fausse.
- **Les deux clauses que nous disions entièrement inconnues sont comblées** : le partenaire se
  découvre par une *Agent Card*, et ses erreurs ont un tableau de codes précis.
- **Mais la liste des données à envoyer est à refaire** : trois champs que nous prévoyions ne sont
  pas acceptés, et deux champs obligatoires nous manquaient.
- **Une décision de conception est contredite par le contrat** : `D15`, « aucune date ne part ». Le
  contrat exige la date de survenance.
- **Trois obligations que nous n'avions pas anticipées** : un identifiant d'évaluation à conserver
  pour l'audit, un seul appel par dossier avec sanction contractuelle en cas de doublon, et une
  découverte par *Agent Card*.

---

## 1 · Les douze hypothèses

| N°  | Hypothèse                                                | Verdict                        | Ce que dit le contrat                                                                                               |
| --- | -------------------------------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------- |
| H1  | JSON-RPC sur une URL de base                             | **confirmée**                  | JSON-RPC 2.0 sur `POST /a2a`, méthode `message/send`                                                                |
| H2  | Jeton, transmis en en-tête                               | **confirmée**                  | `Authorization: Bearer <jeton>`                                                                                     |
| H3  | La réponse porte un niveau et un score                   | **confirmée, mais incomplète** | Elle porte **six** champs, pas deux : + `indicateurs`, `evaluation_id`, `version_modele`                            |
| H4  | Niveau = `faible`, `modere` ou `eleve`                   | **confirmée**                  | Exactement ces trois valeurs                                                                                        |
| H5  | Le score est borné, bornes inconnues                     | **confirmée**                  | Entre **0 et 1 inclus**                                                                                             |
| H6  | Niveau et score s'accordent selon une règle du contrat   | **confirmée**                  | `faible` si < 0,40 · `modere` si 0,40 ≤ s < 0,75 · `eleve` si ≥ 0,75                                                |
| H7  | La clé d'appariement est la référence du dossier         | **confirmée**                  | `reference_dossier` identique à la requête — **et** l'`id` JSON-RPC doit l'être aussi. Deux appariements, pas un    |
| H8  | Délai inférieur à 5 secondes                             | **confirmée, et précisée**     | Le partenaire s'engage à **2 s** ; le client abandonne **au plus tard à 3 s**                                       |
| H9  | Pas de reprise d'appel non maîtrisée                     | **confirmée, et durcie**       | « Aucune relance automatique : ni après un délai dépassé, ni après une erreur, ni après une réponse écartée »       |
| H10 | Le contrat limite le nombre d'appels                     | **confirmée**                  | **Un seul appel par dossier.** Un doublon est refusé et **signalé comme manquement au contrat**                     |
| H11 | Le contrat liste exhaustivement les champs de la réponse | **confirmée**                  | « La réponse ne comporte aucun champ en dehors de ceux listés »                                                     |
| H12 | L'appel attend sa réponse, et il n'y en a qu'une         | **à nuancer**                  | La réponse est une **tâche A2A** déjà `completed`. Synchrone en pratique, mais le vocabulaire est celui d'une tâche |

**Les deux clauses que nous disions inconnues sont comblées :**

- **Se présenter** — découverte par *Agent Card*, `GET /.well-known/agent.json`.
- **Signaler l'échec** — HTTP 401 (jeton), HTTP 503 (service indisponible), et les codes JSON-RPC
  `-32700` (corps illisible), `-32600` (enveloppe), `-32601` (méthode), `-32602` (données non
  conformes), `-32029` (dossier déjà évalué).

---

## 2 · Ce qui change dans ce que nous envoyons

C'est l'écart le plus important. Le contrat impose **exactement sept champs**, tous obligatoires, et
n'en accepte aucun autre.

| Champ                                 | Nous l'avions prévu ?          | Décision                                               |
| ------------------------------------- | ------------------------------ | ------------------------------------------------------ |
| `reference_dossier`                   | oui                            | **conservé** — `D16` était juste                       |
| `type_sinistre`                       | oui                            | conservé                                               |
| `montant_declare`                     | oui                            | conservé                                               |
| `anciennete_contrat_jours`            | oui                            | conservé                                               |
| `sinistres_12_mois`                   | oui                            | conservé                                               |
| `date_survenance`                     | **non — nous l'avions exclue** | **à ajouter.** Contredit `D15`                         |
| `departement`                         | **non**                        | **à ajouter.** Deux premiers caractères du code postal |
| ~~délai de déclaration en jours~~     | oui                            | **à retirer** — non accepté                            |
| ~~montant justifié par les factures~~ | oui                            | **à retirer** — non accepté                            |
| ~~formule du contrat~~                | oui                            | **à retirer** — non accepté                            |

### Sur la date de survenance — notre décision `D15` est contredite

Nous avions décidé de ne transmettre **aucune date**, après avoir vérifié qu'avec une date et une
durée, la date de souscription se reconstitue par soustraction. Le raisonnement était juste. Le
contrat impose l'inverse : `date_survenance` **et** `anciennete_contrat_jours` sont tous deux
obligatoires.

Autrement dit, **le contrat accepte sciemment que la date de souscription soit déductible**. Nous
nous y plions — c'était l'arbitrage annoncé au chantier 2 : « si le partenaire a besoin de dates
réelles, le contrat le dira, et ce sera une décision consciente. »

Elle est consciente. Elle est consignée ici, et `D15` est remplacée.

### Sur le département — une donnée que nous n'envisagions pas

Le contrat interdit le code postal complet mais **exige le département**. C'est un arbitrage de
minimisation que le partenaire a fait pour nous : assez pour un zonage de risque, trop grossier
pour localiser un assuré. Nous n'y avions pas pensé.

### Ce que le contrat interdit, et que nous excluions déjà

Identité et coordonnées, IBAN, identifiants internes, description libre du sinistre, pièces
justificatives. **Notre liste d'exclusion était bonne** — et le contrat ajoute une précision utile :
l'interdiction vaut « sous quelque forme que ce soit : champ dédié, champ texte, valeur détournée ».
C'est exactement ce que notre second contrôle de fuite vérifie.

---

## 3 · Ce qui change dans la validation des réponses

Notre mécanisme à quatre niveaux tient. Les valeurs se précisent.

| Niveau         | Ce qui change                                                                                                                    |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 1 · transport  | HTTP 401 et 503 à reconnaître comme indisponibilité ; abandon **à 3 s**                                                          |
| 2 · lisibilité | Codes `-32700` et `-32600` à traiter                                                                                             |
| 3 · forme      | **Six champs à valider, pas deux.** Validation stricte confirmée par le contrat                                                  |
| 4 · sens       | Score dans **[0 ; 1]** · correspondance score/niveau **chiffrée** · `reference_dossier` identique **et** `id` JSON-RPC identique |

**Une règle du contrat conforte notre choix le plus discuté** : « Une réponse qui ne respecte pas
l'une de ces règles n'engage pas le partenaire : elle doit être écartée par le client, jamais
exploitée. » C'est mot pour mot notre `D18`.

---

## 4 · Ce qui change dans nos décisions

| Décision                                      | État                                  | Ce qui change                                                                                                                                |
| --------------------------------------------- | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `D15` · aucune date ne part                   | **remplacée**                         | Le contrat exige `date_survenance`. Nouvelle décision à écrire : nous transmettons exactement les sept champs du contrat                     |
| `D16` · la référence du dossier est transmise | **confirmée**                         | Le contrat l'exige, et s'en sert pour l'appariement                                                                                          |
| `D18` · validation stricte, verdict unique    | **confirmée**                         | Le contrat emploie la même formule                                                                                                           |
| `D19` · aucune reprise d'appel                | **confirmée, justification corrigée** | Nous l'avions fondée sur le budget de temps, en disant ne pas pouvoir affirmer que le contrat l'interdisait. **Il l'interdit explicitement** |
| `D20` · pas de disjoncteur                    | **confirmée, et renforcée**           | Un seul appel par dossier : un disjoncteur n'aurait de toute façon rien à couper                                                             |
| Délai de 3 secondes                           | **confirmé exactement**               | Le contrat fixe l'abandon « au plus tard 3 secondes ». Notre déduction depuis `PAN-02` tombait juste                                         |

---

## 5 · Trois obligations que nous n'avions pas anticipées

- [ ] **Conserver l'`evaluation_id`** — le contrat le demande explicitement « pour audit ». La fiche
      de décision ne prévoit que `niveau` et `score` : l'identifiant va dans la zone de travail et
      le journal de bord, pas dans la fiche.
- [ ] **Garantir un seul appel par dossier.** Un doublon est refusé (`-32029`) **et signalé à
      l'assureur comme manquement au contrat**. Ce n'est plus une question de politesse technique :
      c'est une clause. Un compteur par référence s'impose, et un test dédié.
- [ ] **Implémenter la découverte par *Agent Card*** — ou décider de ne pas l'utiliser et de
      configurer l'adresse en dur, ce qui doit alors être un choix écrit.

---

## 6 · Ce que cela coûte au plan d'épreuve

- Le scénario **S18** (« score à la limite exacte de ses bornes ») devient précis : les bornes sont
  0, 0,40, 0,75 et 1. Il faut une demande par frontière.
- Un scénario **nouveau** est nécessaire : l'appel en doublon, refusé par `-32029`.
- Le scénario **S17** (« réponse juste sous le délai ») se cale sur 2 s côté partenaire et 3 s côté
  client.
- La validation de forme porte sur six champs : les scénarios `INV-03` et `INV-05` fournis
  prennent tout leur sens.

---

## 7 · Ce qui restait à vérifier dans le dépôt — **répondu le 9 octobre**

| Question                                                            | Réponse                                                                                                                            |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Le partenaire simulé suit-il la version 2.0 ?                       | **Oui.** `CONTRAT_VERSION = "2.0"`, seuils `0.40` et `0.75`, six champs de réponse, quatre indicateurs                             |
| Les sept variantes `invalide` correspondent-elles aux codes du §4 ? | **Oui**, et les cinq codes JSON-RPC du contrat sont tous implémentés, sans un de plus                                              |
| `partner_ctl.py` sait-il simuler un doublon ?                       | Inutile : **le simulateur l'applique nativement** — il mémorise les dossiers évalués et répond `-32029`                            |
| La *Agent Card* est-elle servie ?                                   | **Oui**, à `/.well-known/agent.json`, et elle devient indisponible en mode panne. Nous avons choisi de ne pas l'utiliser *(`D29`)* |

---

*Les douze hypothèses d'origine, avec leur appui et leur coût, sont dans le dossier de
conception `03_chantier_2_a2a_et_epreuve.md`, annexe technique — document de la phase amont,
non versionné ici.*
