"""Les frontières du chantier 1, vérifiées sur les imports eux-mêmes.

C'est l'exigence EX-2 rendue automatique : on ne vérifie plus ce que le système *a fait*, mais
qu'il ne *peut pas* faire autrement. Chaque règle ci-dessous correspond à une frontière du dossier
de conception ; si l'une saute, c'est un test qui tombe, pas une relecture qui l'aurait peut-être vu.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PAQUET = Path(__file__).resolve().parents[2] / "src" / "kaldera"

MODULES_AGENTS = ("eligibilite", "pieces", "estimation", "antifraude", "decision")


def _source(chemin: Path) -> ast.Module:
    return ast.parse(chemin.read_text(encoding="utf-8"), filename=str(chemin))


def imports_de(chemin: Path) -> set[str]:
    """Modules importés, exprimés en chemin pointé relatif au paquet (ex. ``agents.pieces``)."""
    noms: set[str] = set()
    for noeud in ast.walk(_source(chemin)):
        if isinstance(noeud, ast.ImportFrom):
            prefixe = noeud.module or ""
            if noeud.level:  # import relatif
                base = chemin.relative_to(PAQUET).parent.as_posix().replace("/", ".")
                parties = [p for p in base.split(".") if p and p != "."]
                remontee = noeud.level - 1
                racine = parties[: len(parties) - remontee] if remontee else parties
                prefixe = ".".join([*racine, prefixe]) if prefixe else ".".join(racine)
            for alias in noeud.names:
                noms.add(f"{prefixe}.{alias.name}".strip("."))
                noms.add(prefixe.strip("."))
        elif isinstance(noeud, ast.Import):
            for alias in noeud.names:
                noms.add(alias.name)
    return {n for n in noms if n}


def chemin_agent(nom: str) -> Path:
    return PAQUET / "agents" / f"{nom}.py"


def modules_du_paquet() -> list[Path]:
    return sorted(PAQUET.rglob("*.py"))


# --------------------------------------------------------------------- les règles


@pytest.mark.parametrize("agent", MODULES_AGENTS)
def test_aucun_agent_n_importe_un_autre_agent(agent: str) -> None:
    """D5 — un agent ne peut pas renvoyer le travail à un autre."""
    autres = {f"agents.{a}" for a in MODULES_AGENTS if a != agent}
    assert not (imports_de(chemin_agent(agent)) & autres), (
        f"l'agent « {agent} » importe un autre agent"
    )


@pytest.mark.parametrize("agent", MODULES_AGENTS)
def test_aucun_agent_n_importe_l_orchestration(agent: str) -> None:
    """D5 — un agent ne décide pas du chemin."""
    interdits = {i for i in imports_de(chemin_agent(agent)) if i.startswith("orchestration")}
    assert not interdits, f"l'agent « {agent} » importe l'orchestration : {sorted(interdits)}"


@pytest.mark.parametrize("agent", MODULES_AGENTS)
def test_aucun_agent_n_importe_le_dossier(agent: str) -> None:
    """D7 — un agent reçoit ses entrées, il ne tient pas le dossier et ne peut pas l'écraser."""
    assert "dossier" not in imports_de(chemin_agent(agent)), (
        f"l'agent « {agent} » importe le dossier"
    )


def test_seul_l_agent_antifraude_parle_au_partenaire() -> None:
    """Carte des agents — un seul agent a le droit de sortir du système."""
    coupables = [
        a
        for a in MODULES_AGENTS
        if a != "antifraude" and "partenaire" in imports_de(chemin_agent(a))
    ]
    assert not coupables, f"ces agents importent le partenaire : {coupables}"
    assert "partenaire" in imports_de(chemin_agent("antifraude"))


def test_les_regles_n_importent_rien_du_paquet() -> None:
    """Le cœur métier ne dépend ni des agents, ni de l'orchestration, ni du dossier."""
    interdits = {"agents", "orchestration", "dossier", "mesures", "partenaire", "espace_assure"}
    for module in (PAQUET / "regles").glob("*.py"):
        fautifs = {i.split(".")[0] for i in imports_de(module)} & interdits
        assert not fautifs, f"regles/{module.name} importe {sorted(fautifs)}"


def test_seul_le_repartiteur_ecrit_dans_le_dossier() -> None:
    """D7 — le répartiteur est greffier ; un auteur ne devient jamais scribe.

    La détection porte sur les noms de méthode, et non sur le nom de la variable appelée : c'est
    ce qui la rend robuste. En contrepartie ces quatre noms sont réservés au dossier — un autre
    composant qui en aurait besoin doit en choisir d'autres.
    """
    ecritures = {"publier", "noter", "journaliser", "signaler_arret"}
    autorise = PAQUET / "orchestration" / "repartiteur.py"
    for module in modules_du_paquet():
        if module in (autorise, PAQUET / "dossier.py"):
            continue
        appels = {
            noeud.func.attr
            for noeud in ast.walk(_source(module))
            if isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Attribute)
        }
        fautifs = appels & ecritures
        assert not fautifs, (
            f"{module.relative_to(PAQUET)} écrit dans le dossier : {sorted(fautifs)}"
        )


def test_la_porte_publique_expose_les_trois_fonctions() -> None:
    """docs/interface.md — ce que le reste du système d'information est en droit d'appeler."""
    import kaldera

    for nom in ("traiter_demande", "traiter_lot", "bornes"):
        assert callable(getattr(kaldera, nom, None)), f"kaldera.{nom}() absente"


# ------------------------------------------- frontières ajoutées par le chantier 2


def test_seule_la_passerelle_lit_l_adresse_et_le_jeton() -> None:
    """D17 — un filtre dispersé est un filtre invérifiable.

    Si un second module lisait `PARTENAIRE_URL` ou `PARTENAIRE_JETON`, il pourrait émettre un
    appel qui échapperait à la construction de charge et au registre.
    """
    autorise = PAQUET / "partenaire" / "passerelle.py"
    variables = ("PARTENAIRE_URL", "PARTENAIRE_JETON")
    for module in modules_du_paquet():
        if module == autorise:
            continue
        source = module.read_text(encoding="utf-8")
        for variable in variables:
            assert variable not in source, (
                f"{module.relative_to(PAQUET)} lit {variable} — seule la passerelle le peut"
            )


def test_seul_l_agent_antifraude_importe_le_paquet_partenaire() -> None:
    """Un seul agent a le droit de sortir du système."""
    for agent in MODULES_AGENTS:
        importe = any(i.startswith("partenaire") for i in imports_de(chemin_agent(agent)))
        if agent == "antifraude":
            assert importe, "l'agent anti-fraude doit consulter le partenaire"
        else:
            assert not importe, f"l'agent « {agent} » importe le paquet partenaire"


def test_le_paquet_partenaire_n_importe_ni_agent_ni_orchestration() -> None:
    """La passerelle est au bord du système : elle ne remonte pas vers l'équipe."""
    interdits = {"agents", "orchestration", "dossier", "mesures", "espace_assure"}
    for module in (PAQUET / "partenaire").glob("*.py"):
        fautifs = {i.split(".")[0] for i in imports_de(module)} & interdits
        assert not fautifs, f"partenaire/{module.name} importe {sorted(fautifs)}"


def test_aucun_module_ne_porte_de_jeton_en_dur() -> None:
    """Le jeton se lit dans l'environnement. Jamais ailleurs."""
    for module in modules_du_paquet():
        source = module.read_text(encoding="utf-8").lower()
        for motif in ("bearer ey", "jeton-de-demo", "jeton-recette"):
            assert motif not in source, f"{module.relative_to(PAQUET)} contient « {motif} »"
