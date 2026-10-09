"""Tests du chantier 1.

Ce dossier est un paquet : sans ``__init__.py``, pytest exposerait son ``conftest.py``
sous le nom de module ``conftest``, qui masquerait celui de la suite d'acceptance —
laquelle fait ``from conftest import ...``. Le symptome depend de l'ordre de collecte,
ce qui en fait un defaut difficile a reproduire.
"""
