"""Les cinq agents métier. Un agent = un rôle = une section du dossier (décisions D1, D3).

| Agent         | Section dont il est l'auteur | Appels extérieurs       |
| ------------- | ---------------------------- | ----------------------- |
| `eligibilite` | `eligibilite`                | aucun                   |
| `pieces`      | `pieces`                     | l'espace assuré         |
| `estimation`  | `estimation`                 | aucun                   |
| `antifraude`  | `avis_fraude`, ou aucune     | le partenaire anti-fraude |
| `decision`    | `issue`                      | aucun                   |

Aucun agent n'importe un autre agent : ils ne peuvent donc pas se renvoyer le travail. Aucun
n'importe l'orchestration : ils ne décident pas du chemin. Aucun ne touche au dossier : ils
reçoivent leurs entrées et rendent un résultat.
"""

from __future__ import annotations

from . import antifraude, decision, eligibilite, estimation, pieces

__all__ = ["antifraude", "decision", "eligibilite", "estimation", "pieces"]
