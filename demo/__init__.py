"""La démonstration locale : trois espaces, un cabinet de courtage, et de quoi les lancer.

Le chargement du `.env` vit ici plutôt que dans `kaldera` : **le paquet du système ne lit
aucun fichier de configuration.** Une bibliothèque qui va chercher des variables sur le disque
voit son comportement dépendre du répertoire courant. La démonstration, elle, est une
application : charger sa configuration est son travail.
"""

from __future__ import annotations

import os
import pathlib

RACINE = pathlib.Path(__file__).resolve().parents[1]


def charger_env(chemin: str | pathlib.Path | None = None) -> None:
    """Lit un fichier `.env` s'il existe, sans écraser ce qui est déjà dans l'environnement.

    Dix lignes plutôt qu'une dépendance : le `Makefile` charge déjà le `.env`, mais un appel
    direct à `python` ne le fait pas, et la démonstration doit marcher dans les deux cas.

    **Rien de ce fichier n'est journalisé ni affiché.** Il porte une clé d'API.
    """
    fichier = pathlib.Path(chemin) if chemin else RACINE / ".env"
    if not fichier.exists():
        return
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        cle, valeur = cle.strip(), valeur.strip().strip("\"'")
        if cle and valeur and cle not in os.environ:
            os.environ[cle] = valeur


__all__ = ["RACINE", "charger_env"]
