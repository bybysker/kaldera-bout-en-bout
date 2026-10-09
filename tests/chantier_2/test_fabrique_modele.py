"""La fabrique du client de modèle : un seul endroit, et il se tait quand il ne peut rien.

Trois appelants en avaient chacun une copie — la revue, les aides au gestionnaire, la prise
de déclaration du cabinet. Ces tests gardent ce que la copie unique doit faire, et surtout ce
qu'elle ne doit **jamais** faire : lever, lire un fichier, ou se retrouver sur le chemin de
décision.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from kaldera import llm

PAQUET = Path(llm.__file__).resolve().parent

AZURE = {"AZURE_AI_ENDPOINT": "https://exemple.invalid/models", "AZURE_AI_API_KEY": "factice"}
OPENAI = {
    "AZURE_AI_ENDPOINT": "https://exemple.invalid/openai/v1",
    "AZURE_AI_API_KEY": "factice",
}


# ------------------------------------------------- le bon client pour la bonne adresse


@pytest.mark.parametrize(
    ("adresse", "attendu"),
    [
        ("https://x.invalid/openai/v1", True),
        ("https://x.invalid/openai/v1/", True),
        ("https://x.invalid/v1", True),
        ("https://x.invalid/models", False),
        ("https://x.invalid/models/", False),
        ("https://x.invalid", False),
    ],
)
def test_la_forme_de_l_adresse_designe_le_protocole(adresse: str, attendu: bool) -> None:
    """Envoyer l'un à l'autre produit un « API version not supported » qui ne dit pas la cause.

    C'est l'erreur qui a coûté une soirée. Elle est désormais figée par un test plutôt que
    réapprise à chaque nouvel appelant.
    """
    assert llm.compatible_openai(adresse) is attendu


def test_une_adresse_compatible_openai_donne_le_client_openai() -> None:
    modele = llm.fabriquer(jetons_max=10, environnement=OPENAI)
    assert type(modele).__name__ == "_ClientCompatibleOpenAI"


def test_une_adresse_azure_ai_donne_le_client_azure() -> None:
    modele = llm.fabriquer(jetons_max=10, environnement=AZURE)
    assert type(modele).__name__ == "AzureAIChatCompletionsModel"


# --------------------------------------------------------- elle ne lève jamais


def test_sans_configuration_elle_rend_rien_plutot_que_de_lever() -> None:
    """`None` n'est pas une erreur : c'est l'absence de modèle, que l'appelant traduit."""
    assert llm.fabriquer(jetons_max=10, environnement={}) is None
    assert llm.fabriquer(jetons_max=10, environnement={"AZURE_AI_ENDPOINT": "x"}) is None
    assert llm.fabriquer(jetons_max=10, environnement={"AZURE_AI_API_KEY": "x"}) is None


def test_configure_dit_si_un_modele_est_joignable() -> None:
    assert llm.configure(environnement=AZURE)
    assert not llm.configure(environnement={})


def test_elle_ne_lit_aucun_fichier() -> None:
    """Une bibliothèque qui va chercher des variables sur le disque dépend du dossier courant.

    Le `.env` de ce dépôt existe peut-être, et il porte une clé réelle. La fabrique à qui l'on
    passe un environnement vide doit rendre `None` quand même — sinon le comportement du
    paquet dépendrait d'un fichier que personne ne lui a montré.
    """
    assert llm.fabriquer(jetons_max=10, environnement={}) is None
    assert not llm.configure(environnement={})


# ------------------------------------------------- les bornes arrivent au modèle


class _FauxClient:
    """Enregistre ce qu'on lui demande, sans rien appeler."""

    def __init__(self) -> None:
        self.recu: dict[str, Any] = {}
        self.chat = self

    @property
    def completions(self) -> _FauxClient:
        return self

    def create(self, **arguments: Any) -> Any:
        self.recu = arguments

        class _Reponse:
            choices = [type("C", (), {"message": type("M", (), {"content": "ok"})()})()]

        return _Reponse()


def test_les_jetons_et_la_temperature_arrivent_a_chaque_appel() -> None:
    """Trop peu de jetons fait revenir une réponse **vide sans qu'aucune erreur ne soit levée**.

    C'est ce qui est arrivé avec Kimi : 1 243 jetons consommés pour 35 jetons utiles. La borne
    doit donc être posée, et vérifiée.
    """
    faux = _FauxClient()
    # L'adaptateur est privé : le tester directement est le seul moyen de voir ce qui part.
    client = llm._ClientCompatibleOpenAI(faux, "un-modele", jetons_max=1234, temperature=0.0)
    reponse = client.invoke([("system", "consigne"), ("human", "récit")])

    assert reponse.content == "ok"
    assert faux.recu["max_tokens"] == 1234
    assert faux.recu["temperature"] == 0.0
    assert faux.recu["model"] == "un-modele"
    assert [m["role"] for m in faux.recu["messages"]] == ["system", "user"]


# ----------------------------------------- elle reste hors du chemin de décision


def test_aucun_agent_ni_l_orchestration_n_importe_la_fabrique() -> None:
    """Même garantie que pour la revue, et pour la même raison.

    Un import suffirait à mettre plusieurs secondes de latence dans le chemin de décision, et
    à faire dépendre l'engagement de service d'un fournisseur de modèles.
    """
    autorises = {"revue/relecteur.py"}
    fautifs = []
    for module in PAQUET.rglob("*.py"):
        chemin = module.relative_to(PAQUET).as_posix()
        if chemin in autorises or module.name == "llm.py":
            continue
        arbre = ast.parse(module.read_text(encoding="utf-8"))
        for noeud in ast.walk(arbre):
            noms = []
            if isinstance(noeud, ast.ImportFrom):
                noms.append(noeud.module or "")
                noms.extend(a.name for a in noeud.names)
            elif isinstance(noeud, ast.Import):
                noms.extend(a.name for a in noeud.names)
            if any(n == "llm" or n.endswith(".llm") for n in noms):
                fautifs.append(chemin)
    assert not fautifs, f"ces modules importent la fabrique de modèle : {sorted(set(fautifs))}"
