"""La liaison avec le service anti-fraude partenaire (A2A, JSON-RPC 2.0).

Un seul agent importe ce paquet : ``agents/antifraude.py``. Un test d'architecture le vérifie.

| Module | Rôle |
| --- | --- |
| `passerelle` | le seul point qui connaît l'adresse et le jeton |
| `charge` | les sept champs du contrat, construits en partant de rien |
| `validation` | les quatre niveaux, premier échec arrête tout |
| `registre` | un seul appel par dossier |
| `erreurs` | les causes normalisées, et leur niveau |
"""

from __future__ import annotations

from . import charge, erreurs, validation
from .passerelle import DELAI_ABANDON_S, Passerelle, url_partenaire
from .registre import Registre

__all__ = [
    "DELAI_ABANDON_S",
    "Passerelle",
    "Registre",
    "charge",
    "erreurs",
    "url_partenaire",
    "validation",
]
