"""Screenshots for the Manual (templates/manual.html), in English, Slovak and Czech.

Runs a COPY of the app on a COPY of instance/workout.db - the real database is
never opened for writing - the same way tools/ui_check.py does. In that copy
it makes a demo account, gives it a plan from the "Full Body Beast" template
and logs a few weeks of made-up sets through the app's own buttons, so the
pictures show nobody's real training. Then it photographs each page on an
iPhone-sized screen (WebKit, Safari's engine) - whole screens for the top of
each Manual section, small cut-outs for single buttons.

    python tools/make_manual_shots.py

Writes static/manual/<en|sk|cs>/*.jpg. Run it again whenever a page the
Manual shows changes look - the commit hooks remind you. Needs Playwright,
like the UI check.
"""
import datetime
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui_check  # noqa: E402  - start_app(): the copy of the app and its database

ROOT = ui_check.ROOT
OUT = os.path.join(ROOT, "static", "manual")
LANGS = ["en", "sk", "cs"]
TEMPLATE = "full-body-beast"
# The demo sets' weights, two weeks ago and last week (x the base below).
WEEKS = [0.9, 0.95]
BASE_KG = [60, 40, 50]          # the day's first three exercises


# ---------------------------------------------------------------- the data
def make_demo_user(db):
    con = sqlite3.connect(db)
    cur = con.execute(
        """insert into users (username, password, age, weight, email, role, is_approved,
               show_session_icons, animate_session_icons, show_stopwatch, show_set_gaps,
               language, translate_exercises, show_plan_icons)
           values ('Demo', 'x', 30, 80, 'demo@example.invalid', 'user', 1, 1, 0, 1, 1, 'en', 0, 1)""")
    con.commit()
    user_id = cur.lastrowid
    con.close()
    return user_id


def shift_into_past(db, user_id, days):
    """Everything this user logged so far moves `days` days back."""
    con = sqlite3.connect(db)
    offset = f"{days} days"
    con.execute("update sessions set session_date = datetime(session_date, ?), "
                "session_end = datetime(session_end, ?) where user_id = ?", (offset, offset, user_id))
    con.execute("""update exercise_entries set logged_at = datetime(logged_at, ?),
                   started_at = datetime(started_at, ?)
                   where session_id in (select session_id from sessions where user_id = ?)""",
                (offset, offset, user_id))
    con.commit()
    con.close()


def forget_today(db, user_id):
    """The sets the previous language's pictures logged today go again, so
    every language shows the same two."""
    con = sqlite3.connect(db)
    con.execute("""delete from exercise_entries where logged_at > datetime('now', '-1 day')
                   and session_id in (select session_id from sessions where user_id = ?)""", (user_id,))
    con.commit()
    con.close()


def set_language(db, user_id, lang):
    ui_check.set_language(db, user_id, lang)


def log_set(page, kg, reps, rpe):
    page.fill("#weightInput", str(kg))
    page.fill("input[name=reps]", str(reps))
    page.fill("input[name=rpe]", str(rpe))
    page.click("button[name=confirm_button]")
    page.wait_for_load_state("load")


def first_day(db, user_id):
    """The name of the plan's first training day."""
    con = sqlite3.connect(db)
    row = con.execute("select workout_name from workouts where user_id = ? order by workout_id limit 1",
                      (user_id,)).fetchone()
    con.close()
    return row[0]


def open_day(page, base, day):
    # The page suggests the next day due by itself - always this one here.
    page.goto(base + "/training_session?" + urlencode({"training_day": day}))
    page.wait_for_load_state("load")


def log_day(page, base, day, factor, exercises=3, sets=3):
    """Day 1 of the plan: a few sets of its first exercises."""
    open_day(page, base, day)
    for i in range(exercises):
        for s in range(sets):
            kg = round(BASE_KG[i % len(BASE_KG)] * factor / 2.5) * 2.5
            log_set(page, kg, 10 - s, 7 + s)
        if i + 1 < exercises:
            page.click("button[name=next_day]")
            page.wait_for_load_state("load")
    # back to the day's first exercise
    for _ in range(exercises - 1):
        page.click("button[name=previous_day]")
        page.wait_for_load_state("load")


def make_demo_data(browser, base, db, user_id):
    ctx = browser.new_context(**PHONE)
    page = ctx.new_page()
    page.goto(f"{base}/_ui_check_login/{user_id}")
    page.request.post(base + "/table_layout", form={"action": "use_template", "template_id": TEMPLATE})
    # Logged now, then pushed a week back - twice: two weeks ago, last week.
    # Today's sets are logged while photographing, so the stopwatch runs.
    day = first_day(db, user_id)
    for factor in WEEKS:
        log_day(page, base, day, factor)
        shift_into_past(db, user_id, -7)
    # Freestyle day, last week: one exercise.
    page.goto(base + "/intuitive_training?confirm_freestyle=confirm_freestyle")
    page.fill("#new_exercise", FREESTYLE_EXERCISE)
    page.fill("#weightInput", "20")
    page.fill("input[name=reps]", "12")
    page.click("form button.btn-success[type=submit]")
    page.wait_for_load_state("load")
    shift_into_past(db, user_id, -3)
    ctx.close()


# ---------------------------------------------------------------- the pictures
PHONE = None            # set in main(): iPhone 13, at 2x to keep the files small
FREESTYLE_EXERCISE = None


def shot(target, path, **kw):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    target.screenshot(path=path, type="jpeg", quality=82, **kw)


def clip(page, locators, pad=8):
    """The box around a few elements, a little air around it."""
    boxes = [loc.bounding_box() for loc in locators]
    boxes = [b for b in boxes if b]
    x0 = max(0, min(b["x"] for b in boxes) - pad)
    y0 = max(0, min(b["y"] for b in boxes) - pad)
    x1 = min(page.viewport_size["width"], max(b["x"] + b["width"] for b in boxes) + pad)
    y1 = min(page.viewport_size["height"], max(b["y"] + b["height"] for b in boxes) + pad)
    return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}


def sw_key(user_id):
    return f"wd_sw_{user_id}"


def photograph(browser, base, db, user_id, lang):
    out = os.path.join(OUT, lang)
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    p = lambda name: os.path.join(out, name + ".jpg")
    set_language(db, user_id, lang)
    forget_today(db, user_id)

    ctx = browser.new_context(**PHONE)
    page = ctx.new_page()
    page.goto(f"{base}/_ui_check_login/{user_id}")
    page.evaluate("localStorage.clear()")

    day = first_day(db, user_id)
    bar = page.locator("#wd-sw")

    # -- Stopwatch, warm-up: started 1:35 ago, no set yet today.
    open_day(page, base, day)
    page.click("#wd-sw-main")
    page.evaluate(f"""() => {{
        const st = JSON.parse(localStorage.getItem('{sw_key(user_id)}'));
        st.start -= 95000; localStorage.setItem('{sw_key(user_id)}', JSON.stringify(st));
    }}""")
    open_day(page, base, day)
    page.wait_for_timeout(600)
    shot(bar, p("sw-warmup"))

    # -- Training Session: two sets today, so the rest clock runs (green).
    log_set(page, 60, 10, 7)
    log_set(page, 60, 9, 8)
    open_day(page, base, day)          # a GET - reloading a POST would log a third set
    page.wait_for_timeout(1500)
    shot(page, p("training"))
    # Cut-outs are taken from the screen, so each goes to its middle first.
    center = "e => e.scrollIntoView({block: 'center'})"
    page.locator("button[name=confirm_button]").evaluate(center)
    page.wait_for_timeout(300)
    shot(page, p("training-buttons"), clip=clip(page, [page.locator("button[name=next_day]"),
                                                     page.locator("button[name=confirm_button]"),
                                                     page.locator("button[name=repeat_button]")]))
    head = page.locator(".table-responsive thead")
    head.evaluate(center)
    page.wait_for_timeout(300)
    shot(page, p("training-head"), clip=clip(page, [head], pad=2))
    page.click("button[data-bs-target='#collapseExample']")
    page.wait_for_timeout(600)
    page.locator("#collapseExample .card").evaluate(center)
    page.wait_for_timeout(300)
    shot(page, p("training-history"), clip=clip(page, [page.locator("#collapseExample .card")], pad=2))

    # -- Stopwatch: the whole screen while resting, then the bar alone in
    #    each of its states.
    open_day(page, base, day)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1500)
    shot(page, p("stopwatch"))
    shot(bar, p("sw-rest"))
    page.click("#wd-sw-flag")
    page.wait_for_timeout(1200)
    shot(bar, p("sw-lap"))
    page.click("#wd-sw-ss")
    page.wait_for_timeout(1200)
    shot(bar, p("sw-ss"))
    page.click("#wd-sw-main")                       # Cancel the superset
    page.click("#wd-sw-main")                       # Go - a set starts
    page.wait_for_timeout(1200)
    shot(bar, p("sw-set"))
    page.click("#wd-sw-main")                       # Cancel it
    page.click("#wd-sw-clock")
    page.wait_for_timeout(300)
    shot(bar, p("sw-total"))
    page.click("#wd-sw-clock")
    page.click("#wd-sw-stop")
    page.wait_for_timeout(300)
    shot(page.locator(".wd-sw-dialog"), p("sw-finish"))
    page.click("#wd-sw-finish")
    page.wait_for_timeout(300)
    shot(bar, p("sw-off"))

    # -- Intuitive Training: two sets of one exercise today.
    page.goto(base + "/intuitive_training?confirm_freestyle=confirm_freestyle")
    for kg, reps in ((20, 12), (20, 10)):
        page.fill("#new_exercise", FREESTYLE_EXERCISE)
        page.fill("#weightInput", str(kg))
        page.fill("input[name=reps]", str(reps))
        page.click("form button.btn-success[type=submit]")
        page.wait_for_load_state("load")
    page.goto(base + "/intuitive_training")
    page.wait_for_timeout(800)
    shot(page, p("intuitive"))

    # -- Create Workout (Change Current Mesocycle)
    page.goto(base + "/create_workout")
    page.wait_for_timeout(600)
    page.locator("tbody[data-day]").first.evaluate("t => window.scrollTo(0, t.getBoundingClientRect().top + scrollY - 150)")
    page.wait_for_timeout(400)
    shot(page, p("create"))
    rows = page.locator("tbody[data-day]").first.locator("tr[data-we-id]")
    shot(page, p("create-row"), clip=clip(page, [rows.nth(0)], pad=2))
    add_row = page.locator("tbody[data-day]").first.locator("tr:not([data-we-id])")
    add_row.evaluate(center)
    page.wait_for_timeout(300)
    shot(page, p("create-add"), clip=clip(page, [add_row], pad=2))
    rows.nth(0).evaluate(center)
    page.click(".wd-action-bar [data-wd-edit-toggle]")
    page.wait_for_timeout(400)
    shot(page, p("create-order"), clip=clip(page, [rows.nth(0), rows.nth(1)]))
    # Swiped left: the row's Delete button out.
    rows.nth(0).evaluate("r => r.classList.add('wd-swiped')")
    page.wait_for_timeout(400)
    shot(page, p("create-delete"), clip=clip(page, [rows.nth(0)], pad=2))
    rows.nth(0).evaluate("r => r.classList.remove('wd-swiped')")
    page.click(".wd-action-bar [data-wd-edit-toggle]")
    page.locator("tbody[data-day] input[name^=sets_]").first.fill("4")
    page.locator("tbody[data-day] input[name^=sets_]").first.dispatch_event("input")
    page.evaluate("document.activeElement && document.activeElement.blur()")   # no focus ring on a button
    page.mouse.click(5, 300)
    page.wait_for_timeout(300)
    shot(page, p("create-bar"), clip=clip(page, [page.locator(".wd-action-bar"), page.locator("[data-wd-discard]")], pad=12))
    page.locator("[data-wd-pick]:visible").first.click()
    page.wait_for_selector("#wd_picker_list img", timeout=15000)
    page.locator("#wd_picker_list button:visible").nth(4).click()
    page.wait_for_selector("#wd_confirm.show")
    page.wait_for_timeout(500)
    shot(page.locator("#wd_confirm .modal-content"), p("create-confirm"))

    # -- Workout Plan, with the demo mesocycle chosen.
    page.goto(base + "/workout_plan_page")
    page.select_option("#mesocycleSelect", index=1)
    page.wait_for_load_state("load")
    page.wait_for_timeout(600)
    shot(page, p("plan"))

    # -- The rest: one whole screen each.
    for name, path in [("progress", "/progress"), ("statistics", "/statistics"), ("menu", "/profile")]:
        page.goto(base + path)
        page.wait_for_timeout(900)
        shot(page, p(name))

    ctx.close()


def main():
    global PHONE, FREESTYLE_EXERCISE
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from playwright.sync_api import sync_playwright

    started = time.time()
    work = tempfile.mkdtemp(prefix="wd_manual_")
    proc, base, db = ui_check.start_app(work)
    try:
        con = sqlite3.connect(db)
        row = con.execute("select exercise_name from exercises where is_deleted = 0 and exercise_name in "
                          "('Dumbbell Bicep Curl', 'Barbell Curl', 'Dumbbell Lateral Raise') limit 1").fetchone()
        con.close()
        FREESTYLE_EXERCISE = row[0] if row else "Dumbbell Bicep Curl"
        user_id = make_demo_user(db)
        with sync_playwright() as p:
            PHONE = dict(p.devices["iPhone 13"], device_scale_factor=2)
            browser = p.webkit.launch()
            make_demo_data(browser, base, db, user_id)
            for lang in LANGS:
                photograph(browser, base, db, user_id, lang)
                print(f"  {lang}: done")
            browser.close()
    finally:
        proc.kill()
        shutil.rmtree(work, ignore_errors=True)
    total = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(OUT) for f in fs)
    print(f"Manual screenshots in {OUT} - {total // 1024} KB, {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
