"""Simple i18n translation system using flat JSON dictionaries."""

import contextvars
import json
from functools import lru_cache
from pathlib import Path

_LOCALES_DIR = Path(__file__).parent.parent.parent.parent / "locales"

_current_lang: contextvars.ContextVar[str] = contextvars.ContextVar("_current_lang", default="ua")


@lru_cache(maxsize=4)
def _load_locale(lang: str) -> dict:
    path = _LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def set_language(lang: str) -> None:
    if lang not in ("ua", "en"):
        raise ValueError(f"Unsupported language: {lang}")
    _current_lang.set(lang)


def get_language() -> str:
    return _current_lang.get()


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """Translate a dotted key path, e.g. t("error.author_not_found", author="Smith").

    Args:
        key: Dotted locale key (e.g. "error.author_not_found").
        lang: Override language for this call (thread-safe for async use).
        **kwargs: Format arguments for the translated string.
    """
    locale = _load_locale(lang or _current_lang.get())
    parts = key.split(".")
    value = locale
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return key
        if value is None:
            return key
    if isinstance(value, str):
        return value.format(**kwargs) if kwargs else value
    return key
