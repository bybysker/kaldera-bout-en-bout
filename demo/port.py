"""Vérifie qu'un port est libre avant de lancer la démonstration.

Le message de Streamlit quand le port est pris — *« Port 8501 is not available »* — est exact et
inutile : il ne dit ni pourquoi, ni quoi faire. Le cas le plus fréquent est qu'une démonstration
tourne déjà, et qu'il suffit d'ouvrir son adresse.

    uv run python demo/port.py 8501
"""

from __future__ import annotations

import socket
import sys

ADRESSE = "127.0.0.1"


def libre(port: int) -> bool:
    with socket.socket() as prise:
        try:
            prise.bind((ADRESSE, port))
        except OSError:
            return False
    return True


def main(arguments: list[str]) -> int:
    port = int(arguments[0]) if arguments else 8501
    if libre(port):
        return 0

    print(f"Le port {port} est deja pris.")
    print()
    print(f"  Une demonstration tourne sans doute deja : ouvrez http://{ADRESSE}:{port}")
    print(f"  Pour en lancer une seconde a cote        : make demo PORT={port + 1}")
    print()
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
