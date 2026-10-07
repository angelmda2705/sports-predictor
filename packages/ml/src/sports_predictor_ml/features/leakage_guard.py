"""Guardas anti-fuga temporal (data leakage).

Regla innegociable del producto: para predecir el partido con kickoff ``t`` solo
pueden usarse datos cuyo timestamp sea estrictamente anterior a ``t``. Este módulo
ofrece utilidades reutilizables que los *feature builders* DEBEN usar, y que las
pruebas de CI ejercitan para que cualquier violación falle la build.

La fuga de información es el error #1 que infla artificialmente las métricas y
arruina un sistema de predicción; por eso se trata como una condición de error
explícita (`LeakageError`), no como una advertencia silenciosa.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Protocol, TypeVar


class LeakageError(AssertionError):
    """Se lanza cuando un dato observado en/después del kickoff se usaría como feature."""


def assert_as_of(observed_at: datetime, kickoff: datetime, *, label: str = "dato") -> None:
    """Verifica que ``observed_at`` sea estrictamente anterior a ``kickoff``.

    Args:
        observed_at: instante en que el dato estuvo disponible.
        kickoff: inicio del partido que se intenta predecir.
        label: nombre del dato, para un mensaje de error claro.

    Raises:
        LeakageError: si ``observed_at >= kickoff`` (fuga temporal).
        ValueError: si los datetimes no son comparables (uno naive y otro aware).
    """
    if (observed_at.tzinfo is None) != (kickoff.tzinfo is None):
        raise ValueError(
            "No se pueden comparar datetimes naive y aware; usa UTC consistentemente."
        )
    if observed_at >= kickoff:
        raise LeakageError(
            f"Fuga temporal: '{label}' observado en {observed_at.isoformat()} "
            f"no puede usarse para predecir un partido con kickoff "
            f"{kickoff.isoformat()} (debe ser estrictamente anterior)."
        )


class _HasKickoff(Protocol):
    kickoff_utc: datetime


T = TypeVar("T", bound=_HasKickoff)


def filter_historical(matches: Iterable[T], kickoff: datetime) -> list[T]:
    """Devuelve solo los partidos ANTERIORES a ``kickoff``.

    Es el filtro base de todo *feature builder*: forma reciente, medias móviles,
    Elo, xG acumulado, etc., se calculan exclusivamente sobre el resultado de
    esta función. Excluye el propio partido y cualquier partido posterior.
    """
    return [m for m in matches if m.kickoff_utc < kickoff]
