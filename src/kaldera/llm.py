"""La fabrique du client de modèle de langage — le seul endroit qui sait en construire un.

---

**Pourquoi un seul endroit.** Trois appelants en avaient chacun une copie : le relecteur, les
aides au gestionnaire, et la prise de déclaration du cabinet de courtage. Trois copies de la
même subtilité, qui est celle-ci :

| Forme de l'adresse  | Protocole           | Client qui convient            |
| ------------------- | ------------------- | ------------------------------ |
| `…/openai/v1`, `…/v1` | compatible OpenAI   | `openai.OpenAI`                |
| `…/models`          | Azure AI Inference  | `AzureAIChatCompletionsModel`  |

Envoyer l'un à l'autre produit un *« API version not supported »* qui ne désigne pas la cause.
Une subtilité pareille ne doit pas être réapprise à trois endroits.

**Ce que la fabrique ne fait pas.** Elle ne lit **aucun fichier**. Une bibliothèque qui va
chercher des variables sur le disque voit son comportement dépendre du répertoire courant ;
c'est à l'appelant de charger son `.env` s'il en a un. Elle ne lève jamais : une dépendance
absente ou mal configurée rend `None`, et c'est à l'appelant de dire ce qu'il fait sans modèle.

**Elle n'est appelée par aucun agent.** Elle sert la revue — après la décision — et la
démonstration. Un test lit les imports du paquet pour que cela reste vrai.
"""

from __future__ import annotations

import os
from typing import Any, Protocol

#: Le modèle employé faute d'indication. Les mesures du dossier portent sur celui-ci.
MODELE_PAR_DEFAUT = "Kimi-K2.6"


class Modele(Protocol):
    """Ce que les appelants attendent : `invoke` sur des couples (rôle, contenu)."""

    def invoke(self, messages: list[tuple[str, str]]) -> Any: ...


class _ClientCompatibleOpenAI:
    """Donne à un client compatible OpenAI la forme attendue ici.

    Les bornes sont posées à chaque appel plutôt qu'à la construction : un modèle de
    raisonnement consomme des jetons avant de répondre, et trop peu de jetons fait revenir une
    réponse **vide sans qu'aucune erreur ne soit levée**.
    """

    def __init__(self, client: Any, modele: str, jetons_max: int, temperature: float) -> None:
        self._client = client
        self._modele = modele
        self._jetons_max = jetons_max
        self._temperature = temperature

    def invoke(self, messages: list[tuple[str, str]]) -> Any:
        roles = {"system": "system", "human": "user", "ai": "assistant"}
        reponse = self._client.chat.completions.create(
            model=self._modele,
            messages=[
                {"role": roles.get(role, role), "content": contenu} for role, contenu in messages
            ],
            max_tokens=self._jetons_max,
            temperature=self._temperature,
        )
        return reponse.choices[0].message


def compatible_openai(adresse: str) -> bool:
    """L'adresse désigne-t-elle un point d'accès compatible OpenAI ?"""
    return adresse.rstrip("/").endswith("/v1")


def nom_du_modele(environnement: dict[str, str] | None = None) -> str:
    """Le modèle qui sera employé. Sert à l'afficher : une trace doit dire *qui* a répondu.

    Ni l'adresse ni la clé ne sortent d'ici. L'adresse désigne un hôte, la clé est un secret ;
    le nom du modèle, lui, est ce qu'un lecteur de trace a besoin de savoir.
    """
    env = environnement if environnement is not None else os.environ
    return env.get("AZURE_AI_MODEL") or MODELE_PAR_DEFAUT


def configure(environnement: dict[str, str] | None = None) -> bool:
    """Un modèle est-il joignable ? Sert à ne pas promettre ce qui n'est pas disponible."""
    env = environnement if environnement is not None else os.environ
    return bool(env.get("AZURE_AI_ENDPOINT") and env.get("AZURE_AI_API_KEY"))


def fabriquer(
    *,
    jetons_max: int,
    delai_s: float | None = None,
    temperature: float = 0.0,
    environnement: dict[str, str] | None = None,
) -> Modele | None:
    """Construit le client qui correspond à la forme de l'adresse, ou rend `None`.

    `None` n'est pas une erreur : c'est l'absence de modèle, que chaque appelant traduit dans
    ses propres termes — « non disponible » pour la revue, extraction par règles pour la prise
    de déclaration.
    """
    env = environnement if environnement is not None else os.environ
    adresse = env.get("AZURE_AI_ENDPOINT", "")
    cle = env.get("AZURE_AI_API_KEY", "")
    if not adresse or not cle:
        return None

    modele = nom_du_modele(env)
    try:
        if compatible_openai(adresse):
            from openai import OpenAI

            return _ClientCompatibleOpenAI(
                OpenAI(base_url=adresse, api_key=cle, timeout=delai_s),
                modele,
                jetons_max,
                temperature,
            )

        from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel

        return AzureAIChatCompletionsModel(
            endpoint=adresse,
            credential=cle,
            model=modele,
            max_tokens=jetons_max,
            temperature=temperature,
        )
    except Exception:  # noqa: BLE001 — dépendance absente ou mal configurée : pas de modèle
        return None
