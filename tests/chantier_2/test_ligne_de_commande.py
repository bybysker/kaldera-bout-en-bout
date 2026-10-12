"""La ligne de commande — zéro test avant la revue de code, et c'est elle qu'on lance en premier.

`kaldera.cli` est le point d'entrée le plus visible du dépôt : c'est ce qu'un évaluateur tape
avant d'ouvrir un fichier. Qu'elle n'ait eu aucun test était le défaut le plus embarrassant de la
revue — la couverture le disait sans détour : 0 %.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[2]


def lancer(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "kaldera.cli", "eval/scenarios.jsonl", *arguments],
        cwd=RACINE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def test_un_scenario_rejoue_produit_une_fiche_en_json() -> None:
    acheve = lancer("--scenario", "NOM-01")
    assert acheve.returncode == 0, acheve.stderr

    fiches = [
        json.loads(ligne)
        for ligne in acheve.stdout.splitlines()
        if ligne.startswith("{") and '"reference"' in ligne
    ]
    assert len(fiches) == 1
    assert fiches[0]["reference"] == "KAL-26-0101"
    assert fiches[0]["issue"] in ("decision", "escalade")


def test_la_trace_n_est_affichee_que_si_on_la_demande() -> None:
    """Par défaut la sortie reste lisible ; `--trace` la détaille."""
    sans = lancer("--scenario", "NOM-01")
    avec = lancer("--scenario", "NOM-01", "--trace")
    assert '"trace"' not in sans.stdout
    assert '"trace"' in avec.stdout


def test_le_journal_part_sur_la_sortie_d_erreur_sans_polluer_le_resultat() -> None:
    """Une sortie standard mêlée de journal n'est plus exploitable par un autre programme."""
    acheve = lancer("--scenario", "NOM-01", "--journal")
    assert acheve.returncode == 0
    assert '"evenement": "demande.debut"' in acheve.stderr
    assert "evenement" not in acheve.stdout


def test_le_journal_peut_aller_dans_un_fichier(tmp_path: Path) -> None:
    fichier = tmp_path / "journal.jsonl"
    acheve = lancer("--scenario", "NOM-01", "--journal", str(fichier))
    assert acheve.returncode == 0
    assert fichier.exists()
    evenements = [json.loads(ligne) for ligne in fichier.read_text(encoding="utf-8").splitlines()]
    assert evenements and evenements[0]["evenement"] == "demande.debut"
    assert "evenement" not in acheve.stdout


def test_sans_journal_rien_ne_s_affiche_sur_la_sortie_d_erreur() -> None:
    acheve = lancer("--scenario", "NOM-01")
    assert not acheve.stderr.strip(), acheve.stderr


def test_plusieurs_scenarios_se_rejouent_d_un_coup() -> None:
    acheve = lancer("--scenario", "NOM-01", "--scenario", "NOM-02")
    assert acheve.returncode == 0
    assert "NOM-01" in acheve.stdout and "NOM-02" in acheve.stdout
    assert "NOM-03" not in acheve.stdout


def test_les_metriques_accompagnent_chaque_scenario() -> None:
    acheve = lancer("--scenario", "NOM-01")
    assert '"metriques"' in acheve.stdout


@pytest.mark.parametrize("scenario", ["NOM-05", "NOM-09", "BCL-01"])
def test_les_scenarios_delicats_passent_aussi_en_ligne_de_commande(scenario: str) -> None:
    """Le plafond écrêté, l'escalade sans arrêt, le piège à boucle."""
    acheve = lancer("--scenario", scenario)
    assert acheve.returncode == 0, acheve.stderr
    assert '"motif"' in acheve.stdout


# --------------------------------------------- le lancement de la démonstration


def test_le_port_libre_est_accepte() -> None:
    import socket

    from demo import port

    with socket.socket() as prise:
        prise.bind(("127.0.0.1", 0))
        libre = prise.getsockname()[1]
    assert port.libre(libre)
    assert port.main([str(libre)]) == 0


def test_un_port_pris_est_signale_avec_la_marche_a_suivre(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """« Port 8501 is not available » est exact et inutile : il ne dit pas quoi faire."""
    import socket

    from demo import port

    with socket.socket() as prise:
        prise.bind(("127.0.0.1", 0))
        occupe = prise.getsockname()[1]
        assert not port.libre(occupe)
        assert port.main([str(occupe)]) == 1

    sortie = capsys.readouterr().out
    assert "deja pris" in sortie
    assert f"http://127.0.0.1:{occupe}" in sortie, "il faut donner l'adresse à ouvrir"
    assert f"PORT={occupe + 1}" in sortie, "et la façon d'en lancer une seconde"
