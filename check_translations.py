"""Which texts are missing from translations/sk.json and cs.json?

Collects every text the app translates - _("...") in templates and server.py,
tr("...") in workout_management, wdT("...") in static/js, _n(count, "one",
"many") and plural_forms("one", "many") - and lists, per language:

  missing   a text with no translation (the page shows it in English)
  plural    a counted text whose translation is not the list of three forms
  unused    a translation no page asks for any more (safe to delete)

    python check_translations.py            # report
    python check_translations.py --list     # every text, one per line
"""
import ast
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# Texts translated through a variable, so no _("...") shows them: the ranges
# of the statistics dropdown (STATISTICS_RANGES in workout_management.py).
DYNAMIC = ["Last month", "Last 3 months", "Last 1/2 year", "Last year", "All time"]

STRING = r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
SINGLE = re.compile(r"(?<![\w.])(?:_|tr|wdT)\(\s*" + STRING)
PLURAL = re.compile(r"(?<![\w.])(?:_n\(\s*[^,()]+(?:\([^()]*\))?\s*,|plural_forms\()\s*" + STRING + r"\s*,\s*" + STRING)


def unquote(literal):
    return ast.literal_eval(literal)


def collect():
    singles, plurals = set(DYNAMIC), set()
    files = (glob.glob(os.path.join(ROOT, "templates", "**", "*.html"), recursive=True)
             + [os.path.join(ROOT, "server.py"),
                os.path.join(ROOT, "workout_management", "workout_management.py")]
             + glob.glob(os.path.join(ROOT, "static", "js", "*.js")))
    for path in files:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        singles.update(unquote(m) for m in SINGLE.findall(text))
        plurals.update(unquote(many) for _one, many in PLURAL.findall(text))
    return singles, plurals


def main():
    singles, plurals = collect()
    if "--list" in sys.argv:
        for text in sorted(singles):
            print(text)
        for text in sorted(plurals):
            print("[plural]", text)
        return

    problems = 0
    for code in ("sk", "cs"):
        path = os.path.join(ROOT, "translations", f"{code}.json")
        with open(path, encoding="utf-8") as handle:
            catalog = json.load(handle)
        missing = sorted(t for t in singles if not isinstance(catalog.get(t), str) or not catalog.get(t))
        plural = sorted(t for t in plurals
                        if not (isinstance(catalog.get(t), list) and len(catalog[t]) == 3))
        unused = sorted(set(catalog) - singles - plurals)
        print(f"{code}: {len(singles)} texts + {len(plurals)} counted - "
              f"{len(missing)} missing, {len(plural)} counted wrong, {len(unused)} unused")
        for label, items in (("missing", missing), ("plural", plural), ("unused", unused)):
            for item in items:
                print(f"  {label}: {item}")
        problems += len(missing) + len(plural)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
