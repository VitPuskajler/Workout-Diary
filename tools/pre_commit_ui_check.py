"""Claude Code hook (PreToolUse, Bash): run tools/ui_check.py before Claude
commits a change to what the app shows - templates/, static/, translations/.

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

    touched = [f for f in changed_files() if f.startswith(CHECKED)]
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
    print(json.dumps({
        "systemMessage": output.splitlines()[-1] if output else "UI check passed.",
        "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": output},
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
