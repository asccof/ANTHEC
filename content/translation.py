"""Provider boundary: live translation is intentionally disabled in this increment."""
from dataclasses import dataclass
from typing import Protocol

SUPPORTED_LOCALES = frozenset({"ar", "fr", "en"})


class TranslationUnavailable(RuntimeError):
    pass


class Translator(Protocol):
    def translate(self, *, text: str, source: str, target: str) -> str: ...


@dataclass(frozen=True)
class DisabledTranslator:
    def translate(self, *, text: str, source: str, target: str) -> str:
        raise TranslationUnavailable("No external translation provider is authorized.")


@dataclass(frozen=True)
class FixtureTranslator:
    """Explicit prerecorded synthetic fixtures, not AI or general-purpose translation."""
    fixtures: dict[tuple[str, str, str], str]

    def translate(self, *, text: str, source: str, target: str) -> str:
        if source not in SUPPORTED_LOCALES or target not in SUPPORTED_LOCALES:
            raise ValueError("Unsupported content locale")
        try:
            return self.fixtures[(source, target, text)]
        except KeyError as exc:
            raise TranslationUnavailable("Synthetic fixture does not cover this text.") from exc
