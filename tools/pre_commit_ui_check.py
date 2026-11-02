"""Claude Code hook (PreToolUse, Bash): before Claude commits a change to what
the app shows, check that

  1. every text has its Slovak and Czech translation (tools/check_translations.py;
     English is the source, in the code) - for a change to templates/, static/,
     translations/, server.py or workout_management/. A missing one stops the
     commit and Claude is told to add it to both catalogs first;
  2. the UI check passes (tools/ui_check.py) - templates/, static/, translations/;
  3. and reminds (never stops): a page's look changed but the Manual's
     screenshots (static/manual/, tools/make_manual_shots.py) were not refreshed.

Claude Code sends the command it is about to run as JSON on stdin. Anything
that is not a git commit, or a commit that leaves those folders alone, passes
straight through. Otherwise the UI check runs; if it fails this exits with 2,
which stops the commit and hands the output back to Claude to fix.

The check is run before the command, so before a "git add ... && git commit"
in it has staged anything - which is why the working tree is looked at too,
not only what is staged. A pass is stamped, so the git pre-commit hook that
follows does not run the same check a second time.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKED = ("templates/", "static/", "translations/")
TEXTS = CHECKED + ("server.py", "workout_management/")


def changed_files():
    out = []
    for args in (["diff", "--cached", "--name-only"], ["diff", "--name-only"],
                 ["ls-files", "--others", "--exclude-standard"]):
        out += subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.split()
    return sorted(set(out))


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not re.search(r"\bgit\b(\s+-\S+(\s+\S+)?)*\s+commit\b", command):
        return 0

    changed = changed_files()
    if any(f.startswith(TEXTS) for f in changed):
        result = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_translations.py")],
                                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            report = "\n".join(line for line in result.stdout.splitlines() if "unused:" not in line)
            sys.stderr.write(
                "Commit stopped: some texts the app shows have no translation.\n"
                "Before committing: add every text listed as missing to translations/sk.json (Slovak)\n"
                "and translations/cs.json (Czech) - informal 'ty' form, like the rest of the app;\n"
                "English stays the source text in the code. Also check new template text by eye:\n"
                "bare English not wrapped in _() is not seen by the checker. Then commit again.\n\n"
                + report + "\n")
            return 2

    touched = [f for f in changed if f.startswith(CHECKED)]
    if not touched:
        return 0

    result = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ui_check.py"), "--stamp"],
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        sys.stderr.write("Commit stopped: the UI check (PC, Android, iPhone) failed.\n"
                         "Fix what it reports, then commit again.\n\n" + output + "\n")
        return 2

    # Passed: say so, with the screenshot folder, to the user and to Claude.
    message = output.splitlines()[-1] if output else "UI check passed."
    looks = [f for f in touched if f.startswith(("templates/", "static/"))
             and not f.startswith(("static/manual/", "templates/manual.html", "templates/index.html"))]
    if looks and not any(f.startswith("static/manual/") for f in changed):
        reminder = ("Reminder: pages changed - the Manual's screenshots may be out of date. "
                    "Refresh them with: python tools/make_manual_shots.py")
        message += "\n" + reminder
        output += "\n" + reminder
    print(json.dumps({
        "systemMessage": message,
        "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": output},
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
