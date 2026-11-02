"""UI check before a commit: the app on a PC, an Android phone and an iPhone.

Runs a COPY of the app on a COPY of instance/workout.db - the real database is
never opened for writing - and drives it with Playwright in three browsers:

    PC        Chromium, 1920 x 1080
    Android   Chromium, Pixel 7 (touch)
    iPhone    WebKit (Safari's engine), iPhone 13 (touch)

For each: every main page in English, Slovak and Czech must answer 200 with no
JavaScript error, plus checks for things that have broken before (a tapped
icon on Create Workout must move - it did not on an iPhone). Screenshots of
every page (in Slovak) go to a folder printed at the end, to look at.

    python tools/ui_check.py                 run it
    python tools/ui_check.py --stamp         ...and remember a pass for this diff
    python tools/ui_check.py --skip-if-stamped
                                             what the git pre-commit hook runs:
                                             skips when the staged change was
                                             already checked (by Claude's hook)

Exit code 0 = passed, 1 = something failed. Needs: pip install playwright,
then playwright install chromium webkit.
"""
import argparse
import hashlib
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKED_DIRS = ["templates", "static", "translations"]
STAMP = os.path.join(ROOT, ".git", "ui_check_ok")

PAGES = ["/table_layout", "/create_workout", "/workout_plan_page", "/progress",
         "/training_session", "/intuitive_training", "/mesocycle_management",
         "/profile", "/customization", "/manual", "/statistics"]
ADMIN_PAGES = ["/admin/exercises"]
LANGS = ["en", "sk", "cs"]

RUNNER = r'''
import os, sys
app_dir, port = sys.argv[1], int(sys.argv[2])
sys.path.insert(0, app_dir)
os.chdir(app_dir)
import server
from flask import redirect
from flask_login import login_user
from models.models import Users

@server.app.route("/_ui_check_login/<int:user_id>")
def _ui_check_login(user_id):
    login_user(server.db.session.get(Users, user_id))
    return redirect("/create_workout")

server.app.run(port=port, debug=False, use_reloader=False)
'''


# ---------------------------------------------------------------- the stamp
# A pass is remembered as a fingerprint of the change to the checked folders,
# so the git pre-commit hook can skip a change Claude's hook already checked.
# Files are compared by git blob id, which is line-ending neutral (autocrlf).
def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True).stdout


def _fingerprint(diff, new_blobs):
    for path, blob in sorted(new_blobs):
        diff += b"\nnew " + path.encode() + b" " + blob
    return hashlib.sha256(diff).hexdigest()


def staged_fingerprint():
    """The change as staged - what the commit will contain."""
    diff = _git("diff", "--binary", "--cached", "--diff-filter=MD", "HEAD", "--", *CHECKED_DIRS)
    added = _git("diff", "--cached", "--name-only", "--diff-filter=A", "--", *CHECKED_DIRS).decode().split()
    return _fingerprint(diff, [(p, _git("rev-parse", ":" + p).strip()) for p in added])


def working_fingerprint():
    """The change in the working tree - what a following git add will stage."""
    diff = _git("diff", "--binary", "--diff-filter=MD", "HEAD", "--", *CHECKED_DIRS)
    new = set(_git("ls-files", "--others", "--exclude-standard", "--", *CHECKED_DIRS).decode().split())
    new |= set(_git("diff", "--cached", "--name-only", "--diff-filter=A", "--", *CHECKED_DIRS).decode().split())
    return _fingerprint(diff, [(p, _git("hash-object", p).strip()) for p in new])


# ---------------------------------------------------------------- the app copy
def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_app(work):
    app_dir = os.path.join(work, "app")
    os.makedirs(os.path.join(app_dir, "instance"))
    for name in ["server.py", "models", "workout_management", "translations", "templates", "static", "data"]:
        src = os.path.join(ROOT, name)
        (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, os.path.join(app_dir, name))
    for name in ["workout.db", "secret_key"]:
        src = os.path.join(ROOT, "instance", name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(app_dir, "instance", name))
    runner = os.path.join(work, "runner.py")
    with open(runner, "w", encoding="utf-8") as fh:
        fh.write(RUNNER)
    port = free_port()
    log = open(os.path.join(work, "server.log"), "w", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, runner, app_dir, str(port)], stdout=log, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            urllib.request.urlopen(base + "/login", timeout=2)
            return proc, base, os.path.join(app_dir, "instance", "workout.db")
        except Exception:
            if proc.poll() is not None:
                break
            time.sleep(0.5)
    proc.kill()
    raise SystemExit("The app copy did not start - see " + os.path.join(work, "server.log"))


def pick_user(db):
    """The user with the most mesocycles - the richest pages to look at."""
    con = sqlite3.connect(db)
    row = con.execute("""select u.user_id, u.username, u.role = 'admin', count(m.mesocycle_id) n
                         from users u left join mesocycles m on m.user_id = u.user_id
                         group by u.user_id order by n desc limit 1""").fetchone()
    con.close()
    if not row:
        raise SystemExit("instance/workout.db has no users to log in with.")
    return row


def show_icons(db, user_id):
    """The icon checks need the icons on - whatever the real account has."""
    con = sqlite3.connect(db)
    con.execute("update users set show_plan_icons = 1 where user_id = ?", (user_id,))
    con.commit()
    con.close()


def set_language(db, user_id, lang):
    con = sqlite3.connect(db)
    con.execute("update users set language = ? where user_id = ?", (lang, user_id))
    con.commit()
    con.close()


# ---------------------------------------------------------------- the checks
def run_checks(base, db, user, shots):
    from playwright.sync_api import sync_playwright

    user_id, username, is_admin, _ = user
    pages = PAGES + (ADMIN_PAGES if is_admin else [])
    failures, warnings = [], []

    with sync_playwright() as p:
        devices = [
            ("PC", p.chromium, {"viewport": {"width": 1920, "height": 1080}}),
            ("Android", p.chromium, dict(p.devices["Pixel 7"])),
            ("iPhone", p.webkit, dict(p.devices["iPhone 13"])),
        ]
        for name, engine, options in devices:
            browser = engine.launch()
            ctx = browser.new_context(**options)
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e).splitlines()[0]))
            page.goto(f"{base}/_ui_check_login/{user_id}")

            for lang in LANGS:
                set_language(db, user_id, lang)
                for path in pages:
                    errors.clear()
                    try:
                        response = page.goto(base + path, wait_until="load")
                        status = response.status if response else 0
                    except Exception as e:
                        status = "error: " + str(e).splitlines()[0]
                    if status != 200:
                        failures.append(f"{name} {lang} {path}: status {status}")
                    for err in errors:
                        failures.append(f"{name} {lang} {path}: JavaScript error: {err}")
                    if lang == "sk":
                        page.screenshot(path=os.path.join(shots, f"{name}_{path.strip('/').replace('/', '_')}.png"))
                        if name != "PC":
                            overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                            if overflow > 1:
                                warnings.append(f"{name} {path}: page is {overflow}px wider than the screen")

            # Create Workout: a moving icon must move - hover on a PC, tap on a phone.
            page.goto(base + "/create_workout")
            icon = page.locator("img[data-wd-moving]").first
            if icon.count():
                icon.scroll_into_view_if_needed()
                if name == "PC":
                    icon.hover()
                else:
                    icon.tap()
                page.wait_for_timeout(300)
                if "/anim/" not in (icon.get_attribute("src") or ""):
                    failures.append(f"{name} /create_workout: the icon did not move when "
                                    + ("hovered" if name == "PC" else "tapped"))
            else:
                warnings.append(f"{name} /create_workout: no moving icon to test with")

            # Create Workout: the numbers in Sets / Pauses fit their fields
            # (a "120" pause used to show as "12").
            clipped = page.evaluate("""() => Array.from(document.querySelectorAll(
                'tbody[data-day] input[type=number]')).filter(i => i.offsetParent && i.value
                && i.scrollWidth > i.clientWidth + 1).map(i => i.name + '=' + i.value)""")
            if clipped:
                failures.append(f"{name} /create_workout: numbers cut off in {', '.join(clipped[:5])}")

            # Create Workout: Delete asks first - the dialog opens, nothing is
            # sent until its own Delete is pressed.
            page.goto(base + "/create_workout")
            delete = page.locator(".wd-swipe-del").first
            if delete.count():
                page.evaluate("document.querySelector('.wd-swipe-del').click()")
                page.wait_for_timeout(500)
                if not page.locator("#wd_confirm.show").count():
                    failures.append(f"{name} /create_workout: Delete did not ask for confirmation")
                elif page.url.rstrip("/") != (base + "/create_workout"):
                    failures.append(f"{name} /create_workout: Delete went ahead without confirmation")

            # Create Workout: in "Choose exercise" the icons on screen move.
            page.goto(base + "/create_workout")
            pick = page.locator("[data-wd-pick]:visible").first
            if pick.count():
                pick.click()
                page.wait_for_selector("#wd_picker_list img", timeout=10000)
                page.wait_for_timeout(800)
                moving = page.evaluate("""() => Array.from(document.querySelectorAll('#wd_picker_list img'))
                    .filter(i => (i.getAttribute('src') || '').includes('/anim/')).length""")
                if not moving:
                    failures.append(f"{name} /create_workout: icons in 'Choose exercise' do not move")

                # Picking one puts it into the row: the name shown and the
                # hidden field the server reads.
                # A row already in the plan asks first: Cancel keeps the
                # exercise, Replace takes the new one.
                target = pick.get_attribute("data-wd-pick")
                before = pick.inner_text().strip()
                choice = page.locator("#wd_picker_list button:visible").nth(2)
                chosen = choice.locator("span.flex-grow-1").inner_text().strip()
                choice.click()
                page.wait_for_timeout(800)
                asks = target.startswith("exercise_new_") or chosen == before
                if not asks:
                    if not page.locator("#wd_confirm.show").count():
                        failures.append(f"{name} /create_workout: replacing an exercise did not ask first")
                    else:
                        page.locator("#wd_confirm button[data-bs-dismiss]").click()
                        page.wait_for_timeout(500)
                        if pick.inner_text().strip() != before:
                            failures.append(f"{name} /create_workout: Cancel still replaced the exercise")
                        pick.click()
                        page.wait_for_timeout(500)
                        page.locator("#wd_picker_list button:visible").nth(2).click()
                        page.wait_for_timeout(800)
                        page.locator("#wd_confirm_ok").click()
                        page.wait_for_timeout(500)
                shown = pick.inner_text().strip()
                stored = page.locator(f"#{target}").input_value()
                if not (shown == chosen == stored):
                    failures.append(f"{name} /create_workout: picking '{chosen}' left the row showing "
                                    f"'{shown}' and sending '{stored}'")

            # Create Workout: nothing is typed in the plan - every exercise is
            # picked - and every name fits whole (it wraps instead).
            page.goto(base + "/create_workout")
            typed = page.locator("tbody[data-day] input[type=text]").count()
            if typed:
                failures.append(f"{name} /create_workout: {typed} typed exercise field(s) in the plan")
            cut = page.evaluate("""() => Array.from(document.querySelectorAll('.wd-ex-name'))
                .filter(b => b.offsetParent && (b.scrollWidth > b.clientWidth + 1 || b.scrollHeight > b.clientHeight + 1))
                .map(b => b.textContent.trim())""")
            if cut:
                failures.append(f"{name} /create_workout: exercise names cut off: {', '.join(cut[:5])}")

            # ...and every row the same height: a long name gets a smaller
            # font, not a second line. Only a warning - a name too long even
            # at the smallest font wraps on purpose rather than being cut.
            heights = page.evaluate("""() => [...new Set(Array.from(document.querySelectorAll('.wd-ex-name'))
                .filter(b => b.offsetParent).map(b => Math.round(b.getBoundingClientRect().height)))]""")
            # The icons switch above the plan: hides the icons on the spot,
            # is saved (Customization shows it off), and turns back on.
            switch = page.locator("#showPlanIconsHere")
            if switch.count() and switch.is_checked():
                switch.click()
                page.wait_for_timeout(500)
                visible = page.locator("tbody[data-day] .wd-ex-icon img:visible").count()
                page.goto(base + "/customization")
                saved_off = not page.is_checked("#showPlanIcons")
                page.goto(base + "/create_workout")
                hidden_after_reload = page.locator("tbody[data-day] .wd-ex-icon img:visible").count() == 0
                if visible or not saved_off or not hidden_after_reload:
                    failures.append(f"{name} /create_workout: the icons switch did not hide the icons "
                                    f"(visible {visible}, saved off {saved_off}, after reload {hidden_after_reload})")
                page.locator("#showPlanIconsHere").click()
                page.wait_for_timeout(500)
                if not page.locator("tbody[data-day] .wd-ex-icon img:visible").count():
                    failures.append(f"{name} /create_workout: the icons switch did not show the icons again")

            if len(heights) > 1:
                wrapped = page.evaluate("""() => Array.from(document.querySelectorAll('.wd-ex-name.wd-ex-wrap'))
                    .map(b => b.textContent.trim())""")
                warnings.append(f"{name} /create_workout: exercise rows of different heights {sorted(heights)}px"
                                + (f" - wrapped: {', '.join(wrapped[:5])}" if wrapped else ""))

            ctx.close()
            browser.close()
            print(f"  {name}: done")
    return failures, warnings


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stamp", action="store_true", help="remember a pass for the current change")
    parser.add_argument("--skip-if-stamped", action="store_true",
                        help="skip if the staged change already passed (git pre-commit)")
    args = parser.parse_args()

    if args.skip_if_stamped and os.path.exists(STAMP):
        if open(STAMP).read().strip() == staged_fingerprint():
            print("UI check: this change already passed (checked before git add) - skipping.")
            return 0

    try:
        import playwright  # noqa: F401
    except ImportError:
        print("UI check needs Playwright: pip install playwright && playwright install chromium webkit")
        return 1

    work = tempfile.mkdtemp(prefix="wd_ui_check_")
    shots = os.path.join(work, "screenshots")
    os.makedirs(shots)
    print("UI check: PC, Android, iPhone x en/sk/cs ...")
    started = time.time()
    proc, base, db = start_app(work)
    try:
        user = pick_user(db)
        show_icons(db, user[0])
        print(f"  logged in as {user[1]} (copy of the database)")
        failures, warnings = run_checks(base, db, user, shots)
    finally:
        proc.kill()

    for w in warnings:
        print("  warning:", w)
    for f in failures:
        print("  FAIL:", f)
    print(f"UI check {'FAILED' if failures else 'passed'} in {time.time() - started:.0f}s. Screenshots: {shots}")

    if not failures and args.stamp:
        with open(STAMP, "w") as fh:
            fh.write(working_fingerprint())
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
