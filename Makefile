-include .env
export

# Les outils sont invoques en module (`python -m ...`) et non par leur executable : sur un poste
# soumis a une strategie de controle d'application, `pytest.exe` et consorts sont bloques
# (os error 4551) alors que le module equivalent passe. Voir la section " Poste de developpement
# Windows " du README.
PY := uv run python

.PHONY: install venv refaire-venv activer up down partenaire scenarios ctl demo export journaux test modele mutations fmt lint typecheck verifier aide

aide:
	@echo "Cibles disponibles :"
	@echo "  make venv        cree l'environnement depuis un Python systeme (PYTHON=<chemin>)"
	@echo "  make refaire-venv  supprime .venv et le reconstruit (PYTHON=<chemin>)"
	@echo "  make install     installe ou met a jour les dependances"
	@echo "  make activer     rappelle comment activer le venv selon le terminal"
	@echo "  make demo        lance la demonstration Streamlit sur http://127.0.0.1:8501"
	@echo "  make export      ecrit demo/donnees.json (repli autonome, sans Streamlit)"
	@echo "  make journaux    rejoue les scenarios avec le journal d exploitation"
	@echo "  make test        lance la suite complete"
	@echo "  make modele      note l extracteur assiste sur le jeu de recits (appels reels)"
	@echo "  make mutations   reintroduit des defauts un par un et verifie qu'un test tombe"
	@echo "  make verifier    lint + types + tests, dans cet ordre"
	@echo "  make partenaire  demarre le service anti-fraude simule sur le port 8100"
	@echo "  make scenarios   rejoue les scenarios en ligne de commande (ARGS=--trace)"
	@echo "  make ctl         pilote le partenaire simule (ARGS=...)"

# Cette cible detruit et recree l'environnement : elle refuse de s'executer tant que
# l'interpreteur n'est pas nomme, et tant qu'un .venv existe. Un `uv venv --python ""` lance
# par megarde supprime le .venv a moitie - les scripts d'activation partent, l'interpreteur
# reste - et laisse un environnement inutilisable.
venv:
ifeq ($(strip $(PYTHON)),)
	@echo "Indiquez l'interpreteur systeme a utiliser :"
	@echo ""
	@echo '  make venv PYTHON="C:/Users/<vous>/AppData/Local/Programs/Python/Python311/python.exe"'
	@echo ""
	@echo 'Pourquoi un Python du systeme : l_interpreteur telecharge par uv a _ctypes bloque'
	@echo 'sur ce poste, ce qui casse toute dependance a extension native.'
	@exit 1
else ifneq ($(wildcard .venv),)
	@echo "Un environnement existe deja dans .venv/ - rien n'a ete touche."
	@echo ""
	@echo "  make install           met a jour les dependances (le cas courant)"
	@echo "  make refaire-venv      supprime .venv et le reconstruit"
	@echo ""
	@echo "Avant de refaire : arretez ce qui tourne (make demo, un pytest), sinon la"
	@echo "suppression echoue a mi-chemin et laisse un environnement casse."
	@exit 1
else
	uv venv --python "$(PYTHON)"
	uv sync
endif

refaire-venv:
ifeq ($(strip $(PYTHON)),)
	@echo 'Indiquez l interpreteur : make refaire-venv PYTHON="<chemin>/python.exe"'
	@exit 1
else
	rm -rf .venv
	uv venv --python "$(PYTHON)"
	uv sync
endif

activer:
	@echo "L'environnement vit dans kaldera-bout-en-bout/ : s'y placer d'abord."
	@echo ""
	@echo "PowerShell  : Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass"
	@echo "              .\\.venv\\Scripts\\Activate.ps1"
	@echo "Git Bash    : source .venv/Scripts/activate"
	@echo "cmd.exe     : .venv\\Scripts\\activate.bat"
	@echo ""
	@echo "Ensuite : pytest -q, ruff check ., mypy src, streamlit run demo/app.py"
	@echo "Sortir  : deactivate"

install:
	uv sync

up:
	docker compose up -d --build

down:
	docker compose down

partenaire:
	$(PY) -m external_agent --port 8100

scenarios:
	$(PY) -m kaldera.cli eval/scenarios.jsonl $(ARGS)

ctl:
	$(PY) scripts/partner_ctl.py $(ARGS)

# PORT permet d'en lancer une seconde sans arreter la premiere : make demo PORT=8502
PORT ?= 8501

demo:
	@$(PY) demo/port.py $(PORT)
	uv run streamlit run demo/app.py --server.port $(PORT)

export:
	$(PY) -m demo.exporter

journaux:
	$(PY) -m kaldera.cli eval/scenarios.jsonl --journal $(ARGS)

test:
	$(PY) -m pytest -q

modele:
	$(PY) -m pytest -q -m modele -p no:randomly

mutations:
	$(PY) -m tests.chantier_1.epreuve_mutations

fmt:
	$(PY) -m ruff format .
	$(PY) -m ruff check --fix .

lint:
	$(PY) -m ruff check .

typecheck:
	$(PY) -m mypy src

verifier: lint typecheck test
