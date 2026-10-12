"""Outillage des tests du chantier 2.

    Ce module porte un nom unique : pytest expose les ``conftest.py`` sous le nom de
    module ``conftest``, et deux dossiers de tests qui en ont un se masquent l'un
    l'autre selon l'ordre de collecte. Les tests importent donc ``harnais_cN``.

Le partenaire simulé et le chargement des scénarios sont déjà fournis par la suite d'acceptance :
les réutiliser plutôt que les réécrire évite d'éprouver deux harnais au lieu d'un.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

RACINE = Path(__file__).resolve().parents[2]
_ACCEPTANCE = RACINE / "tests" / "acceptance" / "conftest.py"


def _charger_acceptance() -> Any:
    if str(_ACCEPTANCE.parent) not in sys.path:
        sys.path.insert(0, str(_ACCEPTANCE.parent))
    specification = importlib.util.spec_from_file_location("harnais_acceptance", _ACCEPTANCE)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _charger_env() -> None:
    """Rend le `.env` visible aux tests lancés sans passer par `make`.

    Le paquet `kaldera` ne lit aucun fichier de configuration : une bibliothèque qui va chercher
    des variables sur le disque est une bibliothèque dont le comportement dépend du répertoire
    courant. Le `Makefile` charge le `.env` lui-même ; un `pytest` lancé à la main, non — d'où
    ce chargement ici, côté tests.
    """
    fichier = RACINE / ".env"
    if not fichier.exists():
        return
    import os

    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        cle, valeur = cle.strip(), valeur.strip().strip("\"'")
        if cle and valeur and cle not in os.environ:
            os.environ[cle] = valeur


_charger_env()
harnais = _charger_acceptance()

SCENARIOS = harnais.SCENARIOS
traiter = harnais.traiter
traiter_lot = harnais.traiter_lot
Partenaire = harnais.Partenaire

# La fixture de session du partenaire simulé, telle quelle.
partenaire = harnais.partenaire


def scenarios(*categories: str) -> list[Any]:
    return harnais.scenarios(*categories)
