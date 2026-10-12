"""Rejoue les scénarios de recette et exporte ce que la plateforme en montre.

La démonstration ne fabrique rien : elle appelle la porte publique et met en forme ce qu'elle
rend. Si elle avait besoin d'autre chose que la fiche, la trace et les mesures, ce serait le signe
que la plateforme n'expose pas assez — la contrainte est volontaire.

    uv run python -m demo.exporter
"""

from __future__ import annotations

import json
import socket
import threading
import time
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import uvicorn

import kaldera

RACINE = Path(__file__).resolve().parents[1]
SORTIE = Path(__file__).resolve().parent / "donnees.json"
JETON_RECETTE = "jeton-recette"

AGENTS = ("eligibilite", "pieces", "estimation", "antifraude", "decision")
SECTIONS = ("eligibilite", "pieces", "estimation", "avis_fraude", "issue")


# ------------------------------------------------------------- partenaire simulé


def _port_libre() -> int:
    with socket.socket() as prise:
        prise.bind(("127.0.0.1", 0))
        return int(prise.getsockname()[1])


class PartenaireSimule:
    """Le service anti-fraude du brief, lancé dans ce processus le temps de l'export."""

    def __init__(self) -> None:
        import os

        from external_agent.app import app

        os.environ["PARTENAIRE_JETON"] = JETON_RECETTE
        self.port = _port_libre()
        self.url = f"http://127.0.0.1:{self.port}"
        configuration = uvicorn.Config(
            app, host="127.0.0.1", port=self.port, log_level="error", ws="none"
        )
        self.serveur = uvicorn.Server(configuration)
        threading.Thread(target=self.serveur.run, daemon=True).start()
        limite = time.monotonic() + 10
        while not self.serveur.started:
            if time.monotonic() > limite:
                raise RuntimeError("le partenaire simulé n'a pas démarré")
            time.sleep(0.05)
        self.client = httpx.Client(base_url=self.url, timeout=10.0)
        os.environ["PARTENAIRE_URL"] = self.url

    def preparer(self, reglage: dict[str, Any]) -> None:
        self.client.post("/_sim/reset").raise_for_status()
        self.client.post("/_sim/mode", json=reglage).raise_for_status()

    def journal(self) -> list[dict[str, Any]]:
        return list(self.client.get("/_sim/journal").json())

    def arreter(self) -> None:
        self.serveur.should_exit = True


# ------------------------------------------------------------------- l'export


def scenarios() -> list[dict[str, Any]]:
    fichier = RACINE / "eval" / "scenarios.jsonl"
    return [
        json.loads(ligne)
        for ligne in fichier.read_text(encoding="utf-8").splitlines()
        if ligne.strip()
    ]


def resume_demande(demande: dict[str, Any]) -> dict[str, Any]:
    """Ce que la démonstration montre d'une demande — sans les données personnelles."""
    contrat, sinistre = demande["contrat"], demande["sinistre"]
    anciennete = (
        date.fromisoformat(sinistre["date_survenance"])
        - date.fromisoformat(contrat["date_souscription"])
    ).days
    return {
        "reference": demande["reference"],
        "formule": contrat["formule"],
        "statut": contrat["statut"],
        "cotisations_a_jour": contrat["cotisations_a_jour"],
        "anciennete_jours": anciennete,
        "type_sinistre": sinistre["type"],
        "montant_declare": sinistre["montant_declare"],
        "date_survenance": sinistre["date_survenance"],
        "date_declaration": sinistre["date_declaration"],
        "sinistres_12_mois": demande.get("historique", {}).get("sinistres_12_mois", 0),
        "pieces": [
            {"type": p["type"], "lisible": p.get("lisible", False), "montant": p.get("montant")}
            for p in demande.get("pieces", [])
        ],
        "depots_espace_assure": [
            {"type": p["type"], "lisible": p.get("lisible", False), "montant": p.get("montant")}
            for p in demande.get("espace_assure", {}).get("depots", [])
        ],
    }


def rejouer(scenario: dict[str, Any], partenaire: PartenaireSimule) -> dict[str, Any]:
    partenaire.preparer(scenario["partenaire"])
    debut = time.perf_counter()
    resultat = kaldera.traiter_lot(scenario["demandes"], partenaire_url=partenaire.url)
    duree_ms = (time.perf_counter() - debut) * 1000

    attendus = {a["reference"]: a for a in scenario["attendu"]}
    fiches = []
    for fiche in resultat["fiches"]:
        attendu = attendus.get(fiche["reference"], {})
        fiches.append({**fiche, "attendu": attendu, "conforme": _conforme(fiche, attendu)})

    return {
        "id": scenario["id"],
        "categorie": scenario["categorie"],
        "titre": scenario["titre"],
        "partenaire": scenario["partenaire"],
        "demandes": [resume_demande(d) for d in scenario["demandes"]],
        "fiches": fiches,
        "metriques": resultat["metriques"],
        "duree_ms": round(duree_ms, 1),
        "appels_partenaire": [
            {
                "reference": appel.get("reference"),
                "champs": sorted(appel.get("champs") or []),
                "conforme": bool(appel.get("conforme")),
                "statut_http": appel.get("statut_http"),
                "doublon": bool(appel.get("doublon")),
            }
            for appel in partenaire.journal()
        ],
    }


def _conforme(fiche: dict[str, Any], attendu: dict[str, Any]) -> bool:
    """La fiche produite correspond-elle à ce que la recette attend ?"""
    for champ in ("issue", "decision", "file", "mode_degrade"):
        if champ in attendu and bool(fiche.get(champ)) != bool(attendu[champ]):
            if fiche.get(champ) != attendu[champ]:
                return False
    if "montant_rembourse" in attendu:
        obtenu, prevu = fiche.get("montant_rembourse"), attendu["montant_rembourse"]
        if prevu is None and obtenu is not None:
            return False
        if prevu is not None and (obtenu is None or abs(obtenu - prevu) >= 0.01):
            return False
    if attendu.get("arret") and not (fiche.get("arret") or {}).get("borne"):
        return False
    return True


def main() -> int:
    partenaire = PartenaireSimule()
    try:
        rejoues = [rejouer(scenario, partenaire) for scenario in scenarios()]
    finally:
        partenaire.arreter()

    export = {
        "genere_le": time.strftime("%Y-%m-%d %H:%M"),
        "bornes": kaldera.bornes(),
        "agents": list(AGENTS),
        "sections": list(SECTIONS),
        "scenarios": rejoues,
        "totaux": {
            "scenarios": len(rejoues),
            "demandes": sum(len(s["fiches"]) for s in rejoues),
            "conformes": sum(1 for s in rejoues for f in s["fiches"] if f["conforme"]),
        },
    }
    SORTIE.write_text(json.dumps(export, ensure_ascii=False, indent=1), encoding="utf-8")
    taille = SORTIE.stat().st_size / 1024
    print(f"{SORTIE.relative_to(RACINE)} — {taille:.0f} Kio")
    print(
        f"{export['totaux']['scenarios']} scénarios, "
        f"{export['totaux']['demandes']} demandes, "
        f"{export['totaux']['conformes']} conformes à la recette"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
