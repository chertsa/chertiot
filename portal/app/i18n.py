"""Portal i18n (Design System §7): Babel catalogs, cookie-selected locale, RTL for Arabic.

Templates and routers call the request-scoped `_`. Catalogs live in app/locales/<lang>/LC_MESSAGES
(messages.po in git, messages.mo compiled by `make i18n-compile` / the Docker build)."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from babel.support import NullTranslations, Translations
from fastapi import Request

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
SUPPORTED = ("en", "ar")
RTL = {"ar"}


@lru_cache
def catalog(locale: str) -> NullTranslations:
    if locale == "en":
        return NullTranslations()
    return Translations.load(str(LOCALES_DIR), [locale])


def locale_of(request: Request) -> str:
    lang = request.cookies.get("lang", "")
    if lang in SUPPORTED:
        return lang
    accept = request.headers.get("accept-language", "")
    return "ar" if accept[:2].lower() == "ar" else "en"


def translator(request: Request) -> Callable[[str], str]:
    return catalog(locale_of(request)).gettext


def template_globals(request: Request) -> dict[str, object]:
    locale = locale_of(request)
    return {
        "_": catalog(locale).gettext,
        "locale": locale,
        "text_dir": "rtl" if locale in RTL else "ltr",
        "other_locale": "en" if locale == "ar" else "ar",
        "other_locale_label": "English" if locale == "ar" else "العربية",
    }
