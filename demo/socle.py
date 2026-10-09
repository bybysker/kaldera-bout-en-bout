"""Le socle de la démonstration : partenaire simulé, chargement, traitement.

Séparé de l'interface pour deux raisons. La première est qu'il se teste : un partenaire qui ne
démarre pas, un scénario mal chargé, un journal mal capturé sont des pannes qu'on ne veut pas
découvrir devant un jury. La seconde est que l'interface change souvent, et pas ce socle.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import uvicorn

import kaldera
from kaldera import observabilite

RACINE = Path(__file__).resolve().parents[1]
JETON_RECETTE = "jeton-recette"
ADRESSE = "127.0.0.1"


# ------------------------------------------------------------ partenaire simulé


def port_libre() -> int:
    with socket.socket() as prise:
        prise.bind((ADRESSE, 0))
        return int(prise.getsockname()[1])


class Partenaire:
    """Le service anti-fraude du brief, lancé dans ce processus."""

    def __init__(self) -> None:
        from external_agent.app import app

        os.environ["PARTENAIRE_JETON"] = JETON_RECETTE
        self.port = port_libre()
        self.url = f"http://{ADRESSE}:{self.port}"
        configuration = uvicorn.Config(
            app, host=ADRESSE, port=self.port, log_level="error", ws="none"
        )
        self.serveur = uvicorn.Server(configuration)
        threading.Thread(target=self.serveur.run, daemon=True).start()
        limite = time.monotonic() + 15
        while not self.serveur.started:
            if time.monotonic() > limite:
                raise RuntimeError("le partenaire simulé n'a pas démarré")
            time.sleep(0.05)
        self.client = httpx.Client(base_url=self.url, timeout=15.0)
        os.environ["PARTENAIRE_URL"] = self.url

    def preparer(self, reglage: dict[str, Any]) -> None:
        self.client.post("/_sim/reset").raise_for_status()
        self.client.post("/_sim/mode", json=reglage).raise_for_status()

    def journal(self) -> list[dict[str, Any]]:
        return list(self.client.get("/_sim/journal").json())


# ------------------------------------------------------------------ scénarios


def scenarios() -> list[dict[str, Any]]:
    fichier = RACINE / "eval" / "scenarios.jsonl"
    return [
        json.loads(ligne)
        for ligne in fichier.read_text(encoding="utf-8").splitlines()
        if ligne.strip()
    ]


# ------------------------------------------------------------ capture du journal


class JournalEnMemoire(logging.Handler):
    """Recueille les événements du traitement en cours, pour les montrer dans l'interface."""

    def __init__(self) -> None:
        super().__init__()
        self.evenements: list[dict[str, Any]] = []
        self.setFormatter(observabilite.FormatJSON())

    def emit(self, enregistrement: logging.LogRecord) -> None:
        self.evenements.append(json.loads(self.format(enregistrement)))


def traiter(
    demandes: list[dict[str, Any]], partenaire: Partenaire, reglage: dict[str, Any]
) -> dict[str, Any]:
    """Traite un lot et rend tout ce que la démonstration montre.

    Le journal est capturé le temps du traitement, puis les gestionnaires d'origine sont
    remis : une interface ne doit pas laisser l'enregistreur du système dans un état qu'elle a
    choisi.
    """
    partenaire.preparer(reglage)

    capture = JournalEnMemoire()
    enregistreur = observabilite.journal()
    anciens, ancien_niveau = list(enregistreur.handlers), enregistreur.level
    enregistreur.handlers = [capture]
    enregistreur.setLevel(logging.INFO)
    enregistreur.propagate = False

    debut = time.perf_counter()
    try:
        resultat = kaldera.traiter_lot(demandes, partenaire_url=partenaire.url)
    finally:
        enregistreur.handlers = anciens
        enregistreur.setLevel(ancien_niveau)

    return {
        **resultat,
        "duree_ms": (time.perf_counter() - debut) * 1000,
        "journal": capture.evenements,
        "journal_partenaire": partenaire.journal(),
    }


# --------------------------------------------------------------- conformité


def attendu_de(scenario: dict[str, Any], reference: str) -> dict[str, Any]:
    for attendu in scenario.get("attendu", []):
        if attendu["reference"] == reference:
            return attendu
    return {}


def conforme(fiche: dict[str, Any], attendu: dict[str, Any]) -> bool:
    """La fiche produite correspond-elle à ce que la recette attend ?

    Seuls les champs présents dans l'attendu sont vérifiés — c'est la règle de la suite
    d'acceptance, et la respecter évite de juger sur ce que la recette ne dit pas.
    """
    if not attendu:
        return True
    for champ in ("issue", "decision", "file"):
        if champ in attendu and fiche.get(champ) != attendu[champ]:
            return False
    if "mode_degrade" in attendu and bool(fiche.get("mode_degrade")) != attendu["mode_degrade"]:
        return False
    if "montant_rembourse" in attendu:
        obtenu, prevu = fiche.get("montant_rembourse"), attendu["montant_rembourse"]
        if prevu is None:
            if obtenu is not None:
                return False
        elif obtenu is None or abs(obtenu - prevu) >= 0.01:
            return False
    if attendu.get("arret") and not (fiche.get("arret") or {}).get("borne"):
        return False
    return True
