"""One-off data change: the handstand ladder.

  - registers the rungs the catalog was missing (NEW_EXERCISES): the hollow
    body and pike work, the wall drills, kick-up, freestanding handstand and
    the advanced skills
  - moves Chest-to-Wall / Back-to-Wall Handstand and Handstand Push-Up off the
    shared generated handstand icon onto their own drawings (OWN_DRAWINGS) -
    only while they still have it, so a pick made on /admin/exercises since is
    left alone

The drawings come from tools/make_exercise_icons.py (HANDSTAND_ICONS); the
files must be in static/icons/exercises first. Same rules as
temp/add_front_lever_progressions.py, whose code this uses: safe to run twice,
a dry run without --apply, a backup of the database before --apply.

    python temp/add_handstand_progressions.py            # dry run
    python temp/add_handstand_progressions.py --apply    # make the changes
"""
from add_front_lever_progressions import run

# (name, muscle_group, is_timed, name_sk, name_cs)
NEW_EXERCISES = [
    # foundations
    ("Hollow Body Hold", "abs", 1, "Lodička (výdrž)", "Lodička (výdrž)"),
    ("Pike Push-Up", "shoulders", 0, "Kľuky v stane", "Kliky ve stříšce"),
    ("Elevated Pike Push-Up", "shoulders", 0,
     "Kľuky v stane s nohami na lavičke", "Kliky ve stříšce s nohama na lavičce"),
    ("Box Pike Hold", "shoulders", 1, "Výdrž v stane na boxe", "Výdrž ve stříšce na boxu"),
    # at the wall
    ("Wall Walk", "shoulders", 0, "Výstup po stene do stojky", "Výstup po zdi do stojky"),
    ("Chest-to-Wall Shoulder Taps", "shoulders", 0,
     "Ťukanie do ramien v stojke čelom k stene", "Ťukání do ramen ve stojce čelem ke zdi"),
    ("Wall Handstand Heel Pulls", "shoulders", 0,
     "Odlepovanie piat v stojke pri stene", "Odlepování pat ve stojce u zdi"),
    # freestanding
    ("Kick-Up to Handstand", "shoulders", 0, "Nákop do stojky", "Nákop do stojky na rukou"),
    ("Freestanding Handstand", "shoulders", 1, "Voľná stojka na rukách", "Volná stojka na rukou"),
    # advanced
    ("Handstand Walk", "shoulders", 0, "Chôdza po rukách", "Chůze po rukou"),
    ("Tuck Press to Handstand", "shoulders", 0, "Výtlak do stojky zo skrčenia", "Výtlak do stojky ze skrčení"),
    ("Straddle Press to Handstand", "shoulders", 0, "Výtlak do stojky z roznoženia", "Výtlak do stojky z roznožení"),
    ("Wall Handstand Push-Up Negative", "shoulders", 0,
     "Negatívne kľuky v stojke pri stene", "Negativní kliky ve stojce u zdi"),
    ("Freestanding Handstand Push-Up", "shoulders", 0, "Kľuky vo voľnej stojke", "Kliky ve volné stojce"),
]

# exercise -> the drawing it shared until now
OWN_DRAWINGS = {
    "Chest-to-Wall Handstand": "x-handstand-none",
    "Back-to-Wall Handstand": "x-handstand-none",
    "Handstand Push-Up": "x-handstand-none",
}

if __name__ == "__main__":
    run(NEW_EXERCISES, OWN_DRAWINGS)
