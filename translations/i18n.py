"""The app's languages: English, Slovak, Czech.

Every text a user sees is written in English in the code and goes through
_("..."), which hands back the same text in the user's language:

    _("Training Session")                       -> "Tréning"
    _("Deleted {names}.", names="Push A")       -> placeholders filled AFTER
                                                   translating, so the
                                                   translation can move them

translations/sk.json and cs.json map the English text to the translation. A
text missing there simply stays English, so a new button never breaks a page -
tools/check_translations.py lists what is missing.

Exercise names are never translated - they stay English on purpose.

The language is users.language (picked on /customization). Anyone not logged
in - login, register - sees English.
"""
import json
import os
import re

from flask import has_request_context
from flask_login import current_user

LANGUAGES = {"en": "English", "sk": "Slovenčina", "cs": "Čeština"}
DEFAULT_LANGUAGE = "en"

_DIR = os.path.dirname(os.path.abspath(__file__))                  # translations/, beside this file


def _load(code):
    try:
        with open(os.path.join(_DIR, f"{code}.json"), encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


# Read once: translations only change with a deploy, which restarts the app.
CATALOGS = {code: _load(code) for code in LANGUAGES if code != DEFAULT_LANGUAGE}


def _js_texts():
    """The texts static/js asks for with wdT("...") - only these go to the page."""
    js_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "js")
    found = set()
    for name in os.listdir(js_dir) if os.path.isdir(js_dir) else []:
        if name.endswith(".js"):
            with open(os.path.join(js_dir, name), encoding="utf-8") as handle:
                found.update(re.findall(r'wdT\(\s*"((?:[^"\\]|\\.)*)"', handle.read()))
    return found


JS_TEXTS = _js_texts()


def current_language():
    if has_request_context() and current_user.is_authenticated:
        code = getattr(current_user, "language", None)
        if code in LANGUAGES:
            return code
    return DEFAULT_LANGUAGE


def translate(text, **values):
    """text in the current user's language, {placeholders} filled from values."""
    found = CATALOGS.get(current_language(), {}).get(text)
    text = found if isinstance(found, str) and found else text
    return text.format(**values) if values else text


def js_translations():
    """{English: translation} for the static scripts, in the user's language -
    partials/_js_translations.html puts it on the page for wdT()."""
    catalog = CATALOGS.get(current_language(), {})
    return {text: catalog[text] for text in JS_TEXTS if isinstance(catalog.get(text), str)}


def translate_plural(count, one, many, **values):
    """_n(3, "{count} set", "{count} sets") -> "3 sets" / "3 série".

    Slovak and Czech have three forms - 1 séria, 2-4 série, 5+ sérií - so
    their entry, under the English plural, is a list of the three:
        "{count} sets": ["{count} séria", "{count} série", "{count} sérií"]
    {count} is filled in too."""
    # A count that is not a number (a mesocycle saved without its length)
    # takes the "many" form rather than failing the page.
    n = count if isinstance(count, int) else None
    forms = CATALOGS.get(current_language(), {}).get(many)
    if isinstance(forms, list) and len(forms) == 3:
        text = forms[0] if n == 1 else forms[1] if n is not None and 2 <= n <= 4 else forms[2]
    else:
        text = one if n == 1 else many
    return text.format(count=count, **values)


def plural_forms(one, many):
    """[1, 2-4, 5+] forms for page scripts that count in the browser - pick
    with n === 1 / 2 <= n <= 4 / else. English: [one, many, many]."""
    forms = CATALOGS.get(current_language(), {}).get(many)
    if isinstance(forms, list) and len(forms) == 3:
        return forms
    return [one, many, many]
