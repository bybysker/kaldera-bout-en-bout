"""L'agence : ce que les humains de Kaldera voient et font.

La plateforme s'arrête à la fiche de décision. Ce paquet montre ce qui vient après — le courrier
qu'un assuré reçoit, la fiche qu'un gestionnaire reprend, la décision qu'il prend.

**Rien ici n'appartient au système automatisé.** Comme le reste de `demo/`, ce paquet n'accède
qu'à la porte publique, et ses décisions manuelles vivent le temps de la démonstration.
"""

from __future__ import annotations

from . import assistance, gestionnaire, redaction

__all__ = ["assistance", "gestionnaire", "redaction"]
