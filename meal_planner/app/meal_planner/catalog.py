"""Stable meal classification values shared by persistence, API, and UI."""

from __future__ import annotations

from enum import StrEnum


class ProteinSource(StrEnum):
    POULTRY = "poultry"
    FISH = "fish"
    BEEF = "beef"
    PORK = "pork"
    LAMB = "lamb"
    SEAFOOD = "seafood"
    EGGS = "eggs"
    HALLOUMI = "halloumi"
    TOFU = "tofu"
    TEMPEH = "tempeh"
    QUORN = "quorn"
    LEGUMES = "legumes"
    OTHER = "other"


PROTEIN_SOURCES = tuple(source.value for source in ProteinSource)

_PROTEIN_ALIASES = {
    "poultry": ProteinSource.POULTRY,
    "chicken": ProteinSource.POULTRY,
    "turkey": ProteinSource.POULTRY,
    "fågel": ProteinSource.POULTRY,
    "fagel": ProteinSource.POULTRY,
    "kyckling": ProteinSource.POULTRY,
    "fish": ProteinSource.FISH,
    "fisk": ProteinSource.FISH,
    "beef": ProteinSource.BEEF,
    "nöt": ProteinSource.BEEF,
    "not": ProteinSource.BEEF,
    "nötkött": ProteinSource.BEEF,
    "notkott": ProteinSource.BEEF,
    "pork": ProteinSource.PORK,
    "gris": ProteinSource.PORK,
    "fläsk": ProteinSource.PORK,
    "flask": ProteinSource.PORK,
    "lamb": ProteinSource.LAMB,
    "lamm": ProteinSource.LAMB,
    "seafood": ProteinSource.SEAFOOD,
    "shellfish": ProteinSource.SEAFOOD,
    "skaldjur": ProteinSource.SEAFOOD,
    "egg": ProteinSource.EGGS,
    "eggs": ProteinSource.EGGS,
    "ägg": ProteinSource.EGGS,
    "agg": ProteinSource.EGGS,
    "halloumi": ProteinSource.HALLOUMI,
    "tofu": ProteinSource.TOFU,
    "tempeh": ProteinSource.TEMPEH,
    "quorn": ProteinSource.QUORN,
    "mycoprotein": ProteinSource.QUORN,
    "legumes": ProteinSource.LEGUMES,
    "beans": ProteinSource.LEGUMES,
    "lentils": ProteinSource.LEGUMES,
    "baljväxter": ProteinSource.LEGUMES,
    "baljvaxter": ProteinSource.LEGUMES,
    "other": ProteinSource.OTHER,
    "annat": ProteinSource.OTHER,
    "vegetarian": ProteinSource.OTHER,
    "vegetarisk": ProteinSource.OTHER,
    "vegan": ProteinSource.OTHER,
    "plant": ProteinSource.OTHER,
    "plant-based": ProteinSource.OTHER,
    "plant_based": ProteinSource.OTHER,
    "växtbaserat": ProteinSource.OTHER,
    "vaxtbaserat": ProteinSource.OTHER,
}

_LEGACY_VEGETARIAN_SOURCES = {
    "egg",
    "eggs",
    "ägg",
    "agg",
    "halloumi",
    "tofu",
    "tempeh",
    "quorn",
    "mycoprotein",
    "legumes",
    "beans",
    "lentils",
    "baljväxter",
    "baljvaxter",
    "vegetarian",
    "vegetarisk",
    "vegan",
    "plant",
    "plant-based",
    "plant_based",
    "växtbaserat",
    "vaxtbaserat",
}


def normalize_legacy_protein_source(value: str) -> ProteinSource:
    """Map free-text values from schema v1 to a stable catalog value."""

    return _PROTEIN_ALIASES.get(value.strip().casefold(), ProteinSource.OTHER)


def infer_legacy_vegetarian(value: str) -> bool:
    """Best-effort migration for values that previously encoded vegetarian."""

    return value.strip().casefold() in _LEGACY_VEGETARIAN_SOURCES
