# Kaldera

Plateforme de traitement des demandes de remboursement d'assurance habitation :
contrôle d'éligibilité, vérification des pièces justificatives, estimation du
montant et consultation d'un service anti-fraude partenaire selon le protocole
agent-à-agent (A2A).

## Features

- Traitement d'une demande ou d'un lot de demandes jusqu'à une fiche de décision
  (décision ou escalade vers une file humaine).
- Règles métier chiffrées : formules, franchises, plafonds, seuils d'escalade.
- Demandes de complément de pièces via l'espace assuré.
- Consultation du service anti-fraude partenaire (JSON-RPC 2.0, Agent Card).
- Service partenaire simulé, pilotable en direct (normal, lent, invalide, panne).
- Jeu de scénarios de recette et suite d'acceptance.

## Stack

- Python 3.11 (uv)
- FastAPI 0.115+ / uvicorn 0.30+ (service partenaire simulé)
- httpx 0.27+ (client A2A)
- pydantic 2.x
- LangChain 0.3.x, langchain-azure-ai 0.1.x (Kimi-K2.6), LangGraph 0.2.x
- pytest 8.x
- Docker Compose (service partenaire)

## Setup

```bash
make install              # uv sync — installe les dépendances
cp .env.example .env      # puis renseigner les valeurs
make up                   # docker compose up -d — service partenaire sur :8100
make test                 # suite d'acceptance (lance son propre partenaire simulé)
```

Sans Docker, le service partenaire se lance aussi en local : `make partenaire`.

## Utilisation

```bash
make scenarios                                    # rejoue eval/scenarios.jsonl
make scenarios ARGS="--scenario NOM-01 --trace"   # un scénario, avec sa trace
make ctl ARGS=panne                               # met le service partenaire en panne
make ctl ARGS=journal                             # appels reçus par le partenaire
```

Les cibles `make` chargent `.env`. Hors `make` : `set -a; . ./.env; set +a`.

## Layout

- `src/kaldera/` — le système :
  - `dossier.py` — la mémoire partagée à quatre zones ; une section publiée a un seul auteur
  - `agents/` — éligibilité, pièces, estimation, anti-fraude, décision
  - `orchestration/` — le répartiteur, son plan conditionnel, les bornes métier
  - `regles/` — formules, montants, calendrier, indicateurs, issues
  - `partenaire/` — passerelle A2A, validation en quatre niveaux, registre
  - `observabilite.py` — journal structuré qui refuse d'écrire une donnée personnelle
  - `revue/` — relecture d'une décision close, **hors** du chemin de décision
- `demo/` — la démonstration locale (trois espaces) et le client externe qui dépose des dossiers
- `docs/specs_metier.md` — spécifications fonctionnelles
- `docs/interface.md` — contrat d'intégration (points d'entrée, fiche de décision, trace, métriques)
- `external_agent/` — service anti-fraude partenaire simulé et son contrat d'échange (`contrat.md`)
- `scripts/partner_ctl.py` — pilotage du service partenaire simulé
- `eval/scenarios.jsonl` — scénarios de recette
- `tests/acceptance/` — suite d'acceptance

## Useful commands

```bash
make aide       # liste toutes les cibles
make fmt        # ruff format + autofix
make lint       # ruff check
make typecheck  # mypy
make down       # arrête les services docker
```

## Demonstration

```bash
make demo                 # http://127.0.0.1:8501
make demo PORT=8502       # une seconde, a cote de la premiere
```

L'interface rejoue les scenarios de recette **en direct**, par la porte publique du paquet
`kaldera`, et n'affiche que ce qu'elle rend : la fiche, la trace et les mesures. Le partenaire
anti-fraude simule est lance dans le meme processus et se pilote depuis la barre laterale
(normal, lent, invalide, panne).

Trois espaces, a l'image d'une agence.

| Espace           | Ce qu'on y fait                                                                |
| ---------------- | ------------------------------------------------------------------------------ |
| **Assure**       | Declarer un sinistre en racontant, importer des pieces, lire la decision ecrite |
| **Gestionnaire** | Prendre les dossiers escalades, lire la fiche, decider et motiver par ecrit    |
| **Technique**    | Neuf vues : l'arbre de decision du repartiteur, le dossier partage, l'echange A2A, le mode degrade, l'equipe, le lot et ses mesures, l'observabilite, les cinq usages du modele, les dettes assumees |

L'ecoute est limitee a la boucle locale par `.streamlit/config.toml` : par defaut Streamlit
publie l'application sur toutes les interfaces du poste, y compris l'adresse publique.

**Sans Streamlit**, un export JSON autonome reste disponible comme solution de repli :

```bash
make export      # ecrit demo/donnees.json
```

**`st.dataframe` est inutilisable sur ce poste** : il passe par pandas, dont les extensions
natives sont bloquees par la strategie de controle d'application. Les tableaux sont rendus en
Markdown.

## Poste de developpement Windows

Deux adaptations sont necessaires sur un poste soumis a une strategie de controle
d'application :

```bash
# Premiere installation : construire l'environnement depuis le Python 3.11 du systeme.
# `_ctypes` est bloque pour l'interpreteur telecharge par uv, ce qui casse toute
# dependance a extension native.
make venv PYTHON="C:/Users/<vous>/AppData/Local/Programs/Python/Python311/python.exe"

# Par la suite, pour mettre a jour les dependances :
make install
```

**`make venv` refuse de s'executer** si `PYTHON` n'est pas indique, ou si un `.venv` existe
deja. Ce n'est pas de la prudence excessive : un `uv venv --python ""` lance par megarde
supprime le `.venv` **a moitie** - les scripts d'activation disparaissent, `python.exe` reste -
et laisse un environnement d'ou Streamlit a disparu sans message clair. Pour reconstruire
volontairement :

```bash
make refaire-venv PYTHON="<chemin>/python.exe"
```

**Arretez ce qui tourne avant** (`make demo`, un pytest en cours) : sinon Windows refuse de
supprimer les fichiers ouverts, et la reconstruction echoue a mi-chemin.

Le `Makefile` invoque tous les outils **en module** (`uv run python -m pytest`, `-m ruff`,
`-m mypy`) plutot que par leur executable. Au premier lancement du 7 octobre, `uv run pytest`
echouait avec *« Une strategie de controle d'application a bloque ce fichier »* (os error 4551) ;
quelques heures plus tard, le meme executable passait. Le blocage semble donc viser les binaires
fraichement ecrits, le temps d'une analyse. L'invocation en module fonctionne dans les deux cas :
c'est une precaution, pas un contournement obligatoire. `make aide` liste les cibles.

**Une extension native reste bloquee durablement** : pandas (`DLL load failed`), ce qui rend
`st.dataframe` inutilisable. Les tableaux de la demonstration sont rendus en Markdown.

## Activer l'environnement

`uv run <commande>` et le `Makefile` n'exigent aucune activation. Pour travailler directement
dans le terminal :

```powershell
# PowerShell — la politique d'execution est « Restricted » sur ce poste, il faut l'assouplir
# pour la session en cours uniquement (rien n'est modifie durablement)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

```bash
# Git Bash
source .venv/Scripts/activate
```

```bat
REM cmd.exe
.venv\Scripts\activate.bat
```

Une fois active, les outils s'appellent directement : `pytest -q`, `ruff check .`, `mypy src`,
`streamlit run demo/app.py`. `deactivate` rend la main.

Verification rapide que c'est bien le bon interpreteur :

```bash
python -c "import sys; print(sys.prefix)"
# doit afficher ...\kaldera-bout-en-bout\.venv
```

## Tests

| Suite                | Contenu                                                                     |
| -------------------- | ----------------------------------------------------------------------------- |
| `tests/acceptance/`  | La suite fournie par le brief — elle fait reference                         |
| `tests/chantier_1/`  | Architecture (frontieres verifiees sur les imports), sept invariants d'equipe, bornes publiees, epreuve par mutations |
| `tests/chantier_2/`  | Liaison A2A : charge envoyee, validation des reponses, registre, garde-fous, robustesse, observabilite, client externe, espace agence |

```bash
make test        # tout
make mutations   # les tests savent-ils echouer ?
make verifier    # lint + types + tests
```

L'epreuve des mutations reintroduit un defaut reel a la fois et verifie qu'un test precis
tombe. Elle restaure les sources dans tous les cas.

## Limites assumees

Les deux limites heritees du squelette sont levees : les echanges avec le service anti-fraude
sont revalides contre la version 2.0 de son contrat, et le comportement face a un partenaire
lent, en panne ou repondant hors contrat est eprouve par `tests/chantier_2/`.

Ce qui reste, et qui est assume :

- **Le traitement est sequentiel.** L'engagement de dix secondes par demande tient, mais il
  repose sur l'abandon de l'appel partenaire a trois secondes.
- **Le critere de « coherence » des pieces n'est pas defini par le metier.** Le controle est
  reduit au tableau des pieces exigees ; l'avis plus large rendu par le modele est consultatif
  et n'entre dans aucune decision.
- **`mypy` ne tourne pas sur ce poste** : son extension native est bloquee par la strategie de
  controle d'application.
- **Les tests qui appellent un modele reel sont ecartes de la suite** (`make modele` les lance
  a part), parce qu'un modele n'est pas deterministe et rendrait la suite irreproductible.

## License

Usage interne — tous droits réservés.
