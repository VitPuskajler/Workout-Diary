"""Generate the stick-figure exercise icons (64x64 SVG, a few hundred bytes each)
into static/icons/exercises - the icon library /admin/exercises picks from -
plus icons.json (their labels) and data/exercise_icons.json (which icon each
catalog exercise without its own drawing gets; read from instance/workout.db).

Each icon is a list of strokes: ("b", points) body, ("e", points) equipment,
("w", points) weight, ("h", (x, y)) head, ("c", (x, y, r)) weight plate,
("p", d, kind) a raw path, ("a", d) a motion arrow.

The key is the icon's name; its file name is the slug of it. An exercise with
exactly that name gets the icon on its own, any other exercise is pointed at it
through exercises.icon (see add_exercise_icon_columns.py).

To add a drawing: add an entry below, run it, restart the app.

    python make_exercise_icons.py
"""
import json, os, re, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "static", "icons", "exercises")
BODY, EQUIP, WEIGHT, ARROW = "#212529", "#9aa3ad", "#fd7e14", "#0d6efd"


def pts(p):
    return " ".join(f"{x:g},{y:g}" for x, y in p)


def render(strokes):
    parts = []
    for s in strokes:
        k = s[0]
        if k == "b":
            parts.append(f'<polyline points="{pts(s[1])}" stroke="{BODY}" stroke-width="4.5"/>')
        elif k == "e":
            parts.append(f'<polyline points="{pts(s[1])}" stroke="{EQUIP}" stroke-width="3"/>')
        elif k == "w":
            parts.append(f'<polyline points="{pts(s[1])}" stroke="{WEIGHT}" stroke-width="4"/>')
        elif k == "h":
            x, y = s[1]
            parts.append(f'<circle cx="{x:g}" cy="{y:g}" r="4.6" fill="{BODY}"/>')
        elif k == "c":
            x, y, r = s[1]
            parts.append(f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}" stroke="{WEIGHT}" stroke-width="3.5"/>')
        elif k == "p":
            color, width = {"b": (BODY, 4.5), "e": (EQUIP, 3), "w": (WEIGHT, 4)}[s[2]]
            parts.append(f'<path d="{s[1]}" stroke="{color}" stroke-width="{width}"/>')
        elif k == "a":
            parts.append(f'<path d="{s[1]}" stroke="{ARROW}" stroke-width="2.2" stroke-dasharray="3 3"/>')
        elif k == "f":                                   # medicine ball
            x, y, r = s[1]
            parts.append(f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}" fill="{WEIGHT}"/>')
        elif k == "g":                                   # stability ball
            x, y, r = s[1]
            parts.append(f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}" stroke="{EQUIP}" stroke-width="3"/>')
        elif k == "d":                                   # band
            parts.append(f'<path d="{s[1]}" stroke="{WEIGHT}" stroke-width="2.4" stroke-dasharray="2 3"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" '
            'stroke-linecap="round" stroke-linejoin="round">' + "".join(parts) + "</svg>")


def dumbbell(x, y, horizontal=True):
    if horizontal:
        return [("w", [(x - 6, y), (x + 6, y)]), ("w", [(x - 6, y - 3), (x - 6, y + 3)]), ("w", [(x + 6, y - 3), (x + 6, y + 3)])]
    return [("w", [(x, y - 6), (x, y + 6)]), ("w", [(x - 3, y - 6), (x + 3, y - 6)]), ("w", [(x - 3, y + 6), (x + 3, y + 6)])]


FLOOR = ("e", [(4, 60), (60, 60)])

ICONS = {
    "Pull-Up": [
        ("e", [(8, 9), (56, 9)]),
        ("b", [(20, 9), (17, 21), (26, 26), (38, 26), (47, 21), (44, 9)]),
        ("h", (32, 17)),
        ("b", [(32, 25), (32, 42)]),
        ("b", [(32, 42), (28, 51), (31, 59)]), ("b", [(32, 42), (36, 51), (33, 59)]),
    ],
    "Dip": [
        ("e", [(14, 34), (14, 60)]), ("e", [(50, 34), (50, 60)]),
        ("e", [(10, 34), (18, 34)]), ("e", [(46, 34), (54, 34)]),
        ("h", (32, 13)),
        ("b", [(14, 34), (17, 27), (26, 22), (38, 22), (47, 27), (50, 34)]),
        ("b", [(32, 22), (32, 40), (28, 49), (35, 54)]), ("b", [(32, 40), (36, 49), (29, 54)]),
    ],
    "Push-Up": [
        FLOOR,
        ("b", [(20, 58), (21, 43)]),
        ("b", [(21, 43), (37, 48), (56, 57)]),
        ("h", (13, 40)),
    ],
    "Tuck Front Lever": [
        ("e", [(12, 8), (52, 8)]),
        ("b", [(30, 8), (22, 28)]),
        ("h", (14, 28)),
        ("b", [(22, 28), (37, 29), (32, 19), (42, 16)]),
    ],
    "Front Lever Raise": [
        ("e", [(8, 8), (40, 8)]),
        ("b", [(24, 8), (18, 26)]),
        ("h", (10, 27)),
        ("b", [(18, 26), (36, 27), (56, 27)]),
        ("a", "M50 50 Q60 42 58 33"),
    ],
    "Dumbbell Bench Press": [
        ("e", [(8, 46), (50, 46)]), ("e", [(14, 46), (14, 60)]), ("e", [(44, 46), (44, 60)]),
        ("h", (11, 40)),
        ("b", [(18, 41), (36, 41), (46, 36), (50, 59)]),
        ("b", [(20, 41), (20, 22)]),
        *dumbbell(20, 18),
    ],
    "Dumbbell Incline Bench Press": [
        ("e", [(17, 24), (36, 48), (50, 48)]), ("e", [(38, 48), (38, 60)]),
        ("h", (17, 19)),
        ("b", [(22, 27), (36, 44), (48, 42), (50, 59)]),
        ("b", [(23, 28), (25, 11)]),
        *dumbbell(25, 8),
    ],
    "Barbell Stiff-Leg Deadlift": [
        FLOOR,
        ("h", (10, 30)),
        ("b", [(17, 33), (33, 36), (32, 47), (33, 58)]),
        ("b", [(18, 34), (18, 48)]),
        ("c", (18, 52, 6.5)),
    ],
    "Machine Calf Raise": [
        ("e", [(22, 15), (42, 15)]), ("e", [(24, 54), (40, 54), (40, 60), (24, 60), (24, 54)]),
        ("h", (32, 8)),
        ("b", [(32, 15), (32, 32), (32, 41), (31, 48), (36, 53)]),
        ("b", [(26, 15), (25, 22)]),
        ("a", "M48 46 L48 30 M44 34 L48 29 L52 34"),
    ],
    "Cable Rope Face Pull": [
        FLOOR, ("e", [(56, 4), (56, 60)]), ("e", [(56, 20), (37, 17)]),
        ("h", (29, 13)),
        ("b", [(28, 21), (28, 39), (26, 49), (27, 58)]), ("b", [(28, 39), (32, 49), (33, 58)]),
        ("b", [(28, 22), (19, 19), (35, 16)]),
    ],
    "Parallel Bar Leg Raise": [
        ("e", [(12, 28), (40, 28)]), ("e", [(16, 28), (16, 60)]),
        ("h", (26, 7)),
        ("b", [(25, 15), (25, 28)]),
        ("b", [(25, 15), (25, 34), (39, 34), (54, 33)]),
    ],
    "Dumbbell Lateral Raise": [
        FLOOR,
        ("h", (32, 12)),
        ("b", [(13, 23), (26, 21), (38, 21), (51, 23)]),
        ("b", [(32, 21), (32, 40), (27, 58)]), ("b", [(32, 40), (37, 58)]),
        *dumbbell(10, 23, horizontal=False), *dumbbell(54, 23, horizontal=False),
    ],
    "Machine Lateral Shoulder Raise": [
        ("e", [(20, 44), (44, 44)]), ("e", [(32, 44), (32, 60)]),
        ("h", (32, 12)),
        ("b", [(13, 22), (26, 21), (38, 21), (51, 22)]),
        ("e", [(14, 17), (24, 17)]), ("e", [(40, 17), (50, 17)]),
        ("b", [(32, 21), (32, 41), (24, 45), (24, 58)]), ("b", [(32, 41), (40, 45), (40, 58)]),
        ("a", "M8 32 Q6 24 9 17 M56 32 Q58 24 55 17"),
    ],
    "Machine Seated Leg Curl": [
        ("e", [(12, 18), (18, 42), (38, 42)]), ("e", [(26, 42), (26, 60)]),
        ("h", (16, 13)),
        ("b", [(18, 21), (22, 40), (38, 40), (31, 54)]),
        ("b", [(19, 23), (28, 37)]),
        ("c", (36, 55, 3.5)),
        ("a", "M46 44 Q46 54 40 58"),
    ],
    "Hack Squat": [
        ("e", [(48, 18), (40, 52)]), ("e", [(12, 60), (34, 60)]),
        ("h", (42, 16)),
        ("b", [(41, 24), (35, 46), (19, 40), (23, 58)]),
        ("b", [(41, 25), (35, 31), (40, 24)]),
    ],
    "EZ Bar Curl": [
        FLOOR,
        ("h", (32, 12)),
        ("b", [(27, 21), (37, 21)]),
        ("b", [(27, 21), (24, 34), (22, 25)]), ("b", [(37, 21), (40, 34), (42, 25)]),
        ("p", "M14 25 H19 L23 22 L28 27 L32 25 L36 22 L41 27 L45 25 H50", "w"),
        ("w", [(12, 19), (12, 31)]), ("w", [(52, 19), (52, 31)]),
        ("b", [(32, 21), (32, 41), (27, 58)]), ("b", [(32, 41), (37, 58)]),
    ],
    "Cable Seated Row": [
        ("e", [(8, 48), (26, 48)]), ("e", [(50, 40), (50, 54)]), ("e", [(57, 46), (27, 37)]),
        ("e", [(58, 30), (58, 60)]),
        ("h", (19, 15)),
        ("b", [(18, 23), (20, 45), (35, 37), (48, 46)]),
        ("b", [(18, 25), (10, 34), (26, 37)]),
    ],
    "Machine Seated Row": [
        ("e", [(8, 46), (28, 46)]), ("e", [(18, 46), (18, 60)]),
        ("e", [(38, 22), (38, 42)]), ("e", [(44, 30), (56, 30)]), ("e", [(56, 14), (56, 60)]),
        ("h", (21, 13)),
        ("b", [(20, 21), (20, 43), (34, 45), (38, 58)]),
        ("b", [(20, 23), (12, 30), (30, 29)]),
    ],
    "Barbell Bulgarian Split Squat": [
        FLOOR, ("e", [(40, 44), (58, 44)]), ("e", [(52, 44), (52, 60)]),
        ("c", (36, 20, 6)),
        ("h", (25, 12)),
        ("b", [(27, 20), (30, 39), (18, 43), (20, 58)]),
        ("b", [(28, 22), (33, 26), (35, 20)]),
        ("b", [(30, 39), (35, 53), (44, 44)]),
    ],
    "Cable Tricep Extension": [
        FLOOR, ("e", [(52, 4), (52, 60)]), ("e", [(52, 8), (38, 44)]),
        ("h", (30, 12)),
        ("b", [(30, 20), (31, 32), (38, 44)]),
        ("b", [(30, 20), (30, 39), (27, 49), (28, 58)]), ("b", [(30, 39), (33, 49), (34, 58)]),
    ],
    "Machine Fly": [
        ("e", [(20, 44), (44, 44)]), ("e", [(32, 44), (32, 60)]),
        ("e", [(11, 8), (11, 28)]), ("e", [(53, 8), (53, 28)]),
        ("h", (32, 12)),
        ("b", [(15, 9), (15, 22), (26, 21), (38, 21), (49, 22), (49, 9)]),
        ("b", [(32, 21), (32, 41), (24, 45), (24, 58)]), ("b", [(32, 41), (40, 45), (40, 58)]),
        ("a", "M20 32 Q26 36 30 32 M44 32 Q38 36 34 32"),
    ],
    "Cable Crunch": [
        FLOOR, ("e", [(56, 4), (56, 60)]), ("e", [(56, 8), (44, 34)]),
        ("p", "M31 42 Q36 30 44 33", "b"),
        ("h", (47, 41)),
        ("b", [(31, 42), (29, 57), (14, 57)]),
    ],

    # ---- second batch
    "Explosive Pull-Up": [
        ("e", [(8, 22), (56, 22)]),
        ("h", (32, 11)),
        ("b", [(20, 22), (17, 30), (26, 24), (38, 24), (47, 30), (44, 22)]),
        ("b", [(32, 24), (32, 42), (29, 56)]), ("b", [(32, 42), (35, 56)]),
        ("a", "M54 50 L54 30 M50 34 L54 29 L58 34"),
        ("a", "M10 50 L10 30 M6 34 L10 29 L14 34"),
    ],
    "Decline Push-Up (Handles)": [
        FLOOR, ("e", [(42, 38), (60, 38)]), ("e", [(52, 38), (52, 60)]),
        ("e", [(15, 60), (17, 55), (25, 55), (27, 60)]),
        ("h", (13, 43)),
        ("b", [(21, 55), (21, 45)]),
        ("b", [(20, 45), (36, 40), (50, 35)]),
    ],
    "Bench Push-Up": [
        FLOOR, ("e", [(4, 38), (24, 38)]), ("e", [(14, 38), (14, 60)]),
        ("h", (16, 22)),
        ("b", [(18, 38), (22, 28)]),
        ("b", [(22, 28), (39, 43), (56, 57)]),
    ],
    "Barbell Bench Press": [
        ("e", [(8, 46), (50, 46)]), ("e", [(14, 46), (14, 60)]), ("e", [(44, 46), (44, 60)]),
        ("h", (11, 40)),
        ("b", [(18, 41), (36, 41), (46, 36), (50, 59)]),
        ("b", [(20, 41), (20, 24)]),
        ("c", (20, 18, 7)),
    ],
    "Barbell Squat": [
        FLOOR,
        ("c", (36, 23, 6)),
        ("h", (27, 15)),
        ("b", [(30, 23), (36, 42), (20, 44), (24, 58)]),
        ("b", [(31, 25), (37, 30), (38, 23)]),
    ],
    "Barbell Bent-Over Row": [
        FLOOR,
        ("h", (11, 29)),
        ("b", [(18, 32), (35, 37), (29, 47), (34, 58)]),
        ("b", [(19, 33), (28, 41), (21, 43)]),
        ("c", (21, 47, 6)),
    ],
    "Barbell Military Press": [
        FLOOR,
        ("w", [(10, 9), (54, 9)]), ("w", [(10, 3), (10, 15)]), ("w", [(54, 3), (54, 15)]),
        ("h", (32, 18)),
        ("b", [(21, 9), (19, 20), (27, 26), (37, 26), (45, 20), (43, 9)]),
        ("b", [(32, 26), (32, 42), (27, 58)]), ("b", [(32, 42), (37, 58)]),
    ],
    "Dumbbell Shoulder Press": [
        ("e", [(20, 46), (44, 46)]), ("e", [(32, 46), (32, 60)]),
        ("h", (32, 18)),
        ("b", [(19, 9), (17, 20), (27, 26), (37, 26), (47, 20), (45, 9)]),
        ("b", [(32, 26), (32, 43), (24, 47), (24, 58)]), ("b", [(32, 43), (40, 47), (40, 58)]),
        *dumbbell(19, 6), *dumbbell(45, 6),
    ],
    "Barbell Upright Row": [
        FLOOR,
        ("h", (32, 11)),
        ("b", [(28, 30), (16, 18), (27, 20), (37, 20), (48, 18), (36, 30)]),
        ("w", [(14, 30), (50, 30)]), ("w", [(12, 24), (12, 36)]), ("w", [(52, 24), (52, 36)]),
        ("b", [(32, 20), (32, 41), (27, 58)]), ("b", [(32, 41), (37, 58)]),
    ],
    "Dumbbell Bicep Curl": [
        FLOOR,
        ("h", (32, 12)),
        ("b", [(23, 44), (24, 34), (27, 21), (37, 21), (40, 34), (44, 24)]),
        *dumbbell(23, 47), *dumbbell(44, 21),
        ("b", [(32, 21), (32, 41), (27, 58)]), ("b", [(32, 41), (37, 58)]),
    ],
    "Dumbbell Preacher Curl": [
        ("e", [(26, 30), (42, 46)]), ("e", [(36, 40), (36, 60)]), ("e", [(8, 46), (24, 46)]),
        ("h", (18, 14)),
        ("b", [(20, 22), (18, 44), (32, 46), (32, 58)]),
        ("b", [(21, 24), (35, 39), (44, 28)]),
        *dumbbell(46, 25, horizontal=False),
    ],
    "EZ Bar Tricep Extension": [
        ("e", [(8, 46), (50, 46)]), ("e", [(14, 46), (14, 60)]), ("e", [(44, 46), (44, 60)]),
        ("h", (11, 40)),
        ("b", [(18, 41), (36, 41), (46, 36), (50, 59)]),
        ("b", [(21, 41), (22, 24), (11, 28)]),
        ("c", (9, 27, 5)),
    ],
    "Machine Leg Extension": [
        ("e", [(12, 18), (18, 42), (38, 42)]), ("e", [(26, 42), (26, 60)]),
        ("h", (16, 13)),
        ("b", [(18, 21), (22, 40), (38, 40), (52, 30)]),
        ("b", [(19, 23), (28, 37)]),
        ("c", (52, 34, 3.5)),
        ("a", "M42 54 Q54 52 58 42"),
    ],
    "Machine Leg Curl (Prone)": [
        ("e", [(4, 46), (48, 46)]), ("e", [(10, 46), (10, 60)]), ("e", [(42, 46), (42, 60)]),
        ("h", (8, 38)),
        ("b", [(15, 42), (34, 42), (47, 42), (44, 27)]),
        ("b", [(16, 43), (8, 46)]),
        ("c", (47, 25, 3.5)),
        ("a", "M57 42 Q58 30 52 23"),
    ],
    "Machine Leg Press": [
        ("e", [(6, 26), (18, 52), (30, 52)]), ("e", [(24, 52), (24, 60)]),
        ("e", [(42, 30), (56, 48)]), ("e", [(52, 36), (60, 26)]),
        ("h", (10, 22)),
        ("b", [(13, 30), (24, 49), (34, 31), (47, 38)]),
        ("b", [(15, 33), (24, 46)]),
    ],
    "Machine Lat Pulldown": [
        ("e", [(32, 2), (32, 20)]), ("e", [(22, 50), (42, 50)]), ("e", [(32, 50), (32, 60)]),
        ("w", [(8, 20), (56, 20)]),
        ("h", (32, 13)),
        ("b", [(14, 20), (17, 34), (27, 25), (37, 25), (47, 34), (50, 20)]),
        ("b", [(32, 25), (32, 47), (25, 51), (25, 60)]), ("b", [(32, 47), (39, 51), (39, 60)]),
    ],
    "Dumbbell One-Arm Row": [
        FLOOR, ("e", [(6, 40), (40, 40)]), ("e", [(10, 40), (10, 60)]), ("e", [(36, 40), (36, 60)]),
        ("h", (11, 27)),
        ("b", [(14, 40), (18, 30)]),
        ("b", [(18, 30), (36, 31), (30, 38), (42, 38)]),
        ("b", [(36, 31), (46, 44), (47, 58)]),
        ("b", [(22, 31), (29, 22), (26, 34)]),
        *dumbbell(26, 36),
    ],
    "Bench Crunch": [
        FLOOR,
        ("p", "M34 56 Q24 54 21 45", "b"),
        ("h", (19, 38)),
        ("b", [(34, 56), (44, 42), (55, 57)]),
        ("b", [(22, 46), (28, 40)]),
    ],
    "Leg Raise": [
        FLOOR,
        ("h", (9, 54)),
        ("b", [(16, 57), (34, 57), (38, 22)]),
        ("b", [(18, 57), (28, 59)]),
        ("a", "M54 50 Q56 34 46 24"),
    ],
    "Hanging Leg Raise": [
        ("e", [(14, 6), (46, 6)]),
        ("b", [(30, 6), (30, 20)]),
        ("h", (36, 16)),
        ("b", [(30, 20), (30, 38), (43, 38), (56, 37)]),
        ("a", "M42 58 Q56 56 58 44"),
    ],
    "Plank": [
        FLOOR,
        ("h", (11, 43)),
        ("b", [(28, 58), (18, 58), (19, 47)]),
        ("b", [(19, 47), (37, 49), (56, 57)]),
    ],
    "Ab Roll": [
        FLOOR,
        ("c", (12, 55, 4.5)),
        ("h", (16, 37)),
        ("b", [(12, 52), (22, 41)]),
        ("b", [(22, 41), (39, 47), (42, 57), (56, 57)]),
    ],
    "Dumbbell Lunge": [
        FLOOR,
        ("h", (30, 10)),
        ("b", [(30, 18), (31, 37), (18, 41), (20, 58)]),
        ("b", [(31, 37), (40, 52), (50, 58)]),
        ("b", [(30, 20), (31, 34)]),
        *dumbbell(31, 38, horizontal=False),
    ],
    "Machine Hip Adduction": [
        ("e", [(20, 34), (44, 34)]), ("e", [(32, 34), (32, 60)]),
        ("h", (32, 8)),
        ("b", [(32, 16), (32, 32)]),
        ("b", [(26, 17), (24, 30)]), ("b", [(38, 17), (40, 30)]),
        ("b", [(32, 32), (18, 40), (14, 54)]), ("b", [(32, 32), (46, 40), (50, 54)]),
        ("e", [(9, 42), (11, 56)]), ("e", [(55, 42), (53, 56)]),
        ("a", "M4 52 L10 48 M60 52 L54 48"),
        ("a", "M22 56 L28 52 M42 56 L36 52"),
    ],
    "Machine Hip Abduction": [
        ("e", [(20, 34), (44, 34)]), ("e", [(32, 34), (32, 60)]),
        ("h", (32, 8)),
        ("b", [(32, 16), (32, 32)]),
        ("b", [(26, 17), (24, 30)]), ("b", [(38, 17), (40, 30)]),
        ("b", [(32, 32), (18, 40), (14, 54)]), ("b", [(32, 32), (46, 40), (50, 54)]),
        ("e", [(19, 42), (17, 56)]), ("e", [(45, 42), (47, 56)]),
        ("a", "M10 46 L4 50 M54 46 L60 50"),
    ],
    "Machine Reverse Fly": [
        ("e", [(20, 44), (44, 44)]), ("e", [(32, 44), (32, 60)]),
        ("e", [(8, 14), (8, 30)]), ("e", [(56, 14), (56, 30)]),
        ("h", (32, 12)),
        ("b", [(8, 22), (26, 21), (38, 21), (56, 22)]),
        ("b", [(32, 21), (32, 41), (24, 45), (24, 58)]), ("b", [(32, 41), (40, 45), (40, 58)]),
        ("a", "M20 32 Q12 34 6 38 M44 32 Q52 34 58 38"),
    ],
    "Muscle-Up": [
        ("e", [(8, 32), (56, 32)]),
        ("h", (32, 9)),
        ("b", [(22, 32), (26, 18), (38, 18), (42, 32)]),
        ("b", [(32, 18), (32, 38), (29, 52), (31, 60)]), ("b", [(32, 38), (35, 52), (33, 60)]),
    ],
}


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


# ===========================================================================
#  Generated icons - one for every exercise in the catalog.
#
#  The ICONS above are drawn one by one. The other ~1200 exercises are mostly
#  variations ("Dumbbell Seated Alternating Curl"), so they are built from
#  parts instead: a POSE (body + where the hands are) and the EQUIPMENT named
#  in the exercise, drawn at the hands. Exercises that come out the same share
#  one file, and the mapping exercise -> file goes to data/exercise_icons.json
#  for add_exercise_icon_columns.py to store in exercises.icon.
# ===========================================================================

# ---- bodies the poses are built on (side views face left)
HEAD_F, HEAD_S = ("h", (32, 12)), ("h", (27, 11))
SHOULDERS_F = ("b", [(26, 21), (38, 21)])
BASES = {
    "front_stand": [FLOOR, HEAD_F, SHOULDERS_F, ("b", [(32, 21), (32, 40)]),
                    ("b", [(32, 40), (27, 59)]), ("b", [(32, 40), (37, 59)])],
    "front_seat": [("e", [(20, 44), (44, 44)]), ("e", [(32, 44), (32, 60)]), HEAD_F, SHOULDERS_F,
                   ("b", [(32, 21), (32, 41)]), ("b", [(32, 41), (24, 45), (24, 58)]),
                   ("b", [(32, 41), (40, 45), (40, 58)])],
    "side_stand": [FLOOR, HEAD_S, ("b", [(29, 19), (30, 40)]),
                   ("b", [(30, 40), (27, 59)]), ("b", [(30, 40), (33, 59)])],
    "side_seat": [("e", [(24, 43), (42, 43)]), ("e", [(33, 43), (33, 60)]), HEAD_S,
                  ("b", [(29, 19), (30, 41)]), ("b", [(30, 41), (16, 42), (16, 58)])],
    "bench_flat": [("e", [(8, 46), (50, 46)]), ("e", [(14, 46), (14, 60)]), ("e", [(44, 46), (44, 60)]),
                   ("h", (11, 40)), ("b", [(18, 41), (36, 41), (46, 36), (50, 59)])],
    "bench_incline": [("e", [(17, 24), (36, 48), (50, 48)]), ("e", [(38, 48), (38, 60)]),
                      ("h", (17, 19)), ("b", [(22, 27), (36, 44), (48, 42), (50, 59)])],
    "bench_decline": [("e", [(10, 50), (46, 38)]), ("e", [(40, 40), (40, 60)]),
                      ("h", (10, 44)), ("b", [(17, 46), (36, 40), (44, 32), (52, 38)])],
    "none": [],
}

ARROW_UP_L = ("a", "M18 16 L18 8 M15 11 L18 7 L21 11")
ARROW_UP_R = ("a", "M46 16 L46 8 M43 11 L46 7 L49 11")

# Every pose: base, extra strokes, anchors (where the load sits, first = the
# hand that holds it in a one-arm version), view ("front" puts a barbell across
# both hands, "side" shows its plate), cable = pulley point per anchor,
# ball = where a stability ball goes, bar = anchors for a bar on the back.
POSES = {
    "curl": dict(label="Curl", base="front_stand", view="front",
                 parts=[("b", [(26, 21), (24, 34), (22, 25)]), ("b", [(38, 21), (40, 34), (42, 25)])],
                 anchors=[(22, 24), (42, 24)], cable=[(6, 58), (58, 58)]),
    "preacher": dict(label="Preacher curl", base="none", view="side",
                     parts=[("e", [(26, 30), (42, 46)]), ("e", [(36, 40), (36, 60)]), ("e", [(8, 46), (24, 46)]),
                            ("h", (18, 14)), ("b", [(20, 22), (18, 44), (32, 46), (32, 58)]),
                            ("b", [(21, 24), (35, 39), (44, 28)])],
                     anchors=[(45, 26)], cable=[(60, 50)]),
    "concentration": dict(label="Concentration curl", base="none", view="side",
                          parts=[("e", [(30, 46), (50, 46)]), ("e", [(40, 46), (40, 60)]), ("h", (25, 18)),
                                 ("b", [(30, 25), (38, 44), (22, 44), (22, 58)]),
                                 ("b", [(30, 27), (24, 41), (25, 31)])],
                          anchors=[(25, 29)], cable=[(10, 58)]),
    "wrist_curl": dict(label="Wrist curl", base="side_seat", view="side",
                       parts=[("b", [(29, 21), (27, 37), (12, 38)])],
                       anchors=[(10, 36)], cable=[(10, 58)]),
    "press_bench": dict(label="Bench press", base="bench_flat", view="side",
                        parts=[("b", [(20, 41), (20, 24)])], anchors=[(20, 19)], cable=[(4, 58)],
                        ball=(26, 52, 8)),
    "press_incline": dict(label="Incline press", base="bench_incline", view="side",
                          parts=[("b", [(23, 28), (25, 12)])], anchors=[(25, 8)], cable=[(4, 58)]),
    "press_decline": dict(label="Decline press", base="bench_decline", view="side",
                          parts=[("b", [(19, 46), (19, 30)])], anchors=[(19, 26)], cable=[(4, 58)]),
    "press_overhead": dict(label="Overhead press", base="front_stand", view="front",
                           parts=[("b", [(26, 21), (17, 20), (19, 9)]), ("b", [(38, 21), (47, 20), (45, 9)])],
                           anchors=[(19, 7), (45, 7)], cable=[(6, 58), (58, 58)]),
    "chest_press": dict(label="Chest press", base="side_seat", view="side",
                        parts=[("b", [(29, 21), (20, 27), (10, 23)])], anchors=[(8, 23)], cable=[(60, 22)]),
    "fly": dict(label="Fly", base="front_stand", view="front",
                parts=[("b", [(26, 21), (16, 25), (8, 29)]), ("b", [(38, 21), (48, 25), (56, 29)]),
                       ("a", "M14 37 Q20 41 26 37 M50 37 Q44 41 38 37")],
                anchors=[(8, 29), (56, 29)], cable=[(4, 4), (60, 4)], db_vertical=True),
    "fly_bench": dict(label="Lying fly", base="bench_flat", view="side",
                      parts=[("b", [(20, 41), (13, 27)]), ("a", "M24 22 Q34 26 34 36")],
                      anchors=[(12, 25)], cable=[(4, 58)], ball=(26, 52, 8)),
    "lateral": dict(label="Lateral raise", base="front_stand", view="front",
                    parts=[("b", [(26, 21), (12, 24)]), ("b", [(38, 21), (52, 24)])],
                    anchors=[(10, 24), (54, 24)], cable=[(58, 58), (6, 58)], db_vertical=True),
    "front_raise": dict(label="Front raise", base="side_stand", view="side",
                        parts=[("b", [(29, 21), (12, 20)])], anchors=[(9, 20)], cable=[(36, 58)]),
    "rear_raise": dict(label="Rear delt raise", base="none", view="side",
                       parts=[FLOOR, ("h", (10, 29)), ("b", [(17, 32), (34, 37), (32, 48), (34, 59)]),
                              ("b", [(19, 33), (12, 44)]), ("a", "M4 40 Q4 30 10 26")],
                       anchors=[(11, 47)], cable=[(58, 58)]),
    "row_bent": dict(label="Bent-over row", base="none", view="side",
                     parts=[FLOOR, ("h", (11, 29)), ("b", [(18, 32), (35, 37), (29, 47), (34, 58)]),
                            ("b", [(19, 33), (28, 41), (21, 43)])],
                     anchors=[(21, 46)], cable=[(4, 58)]),
    "row_seated": dict(label="Seated row", base="side_seat", view="side",
                       parts=[("b", [(29, 21), (39, 29), (24, 30)])], anchors=[(22, 30)], cable=[(4, 31)]),
    "row_upright": dict(label="Upright row", base="front_stand", view="front",
                        parts=[("b", [(28, 31), (16, 18), (26, 21)]), ("b", [(36, 31), (48, 18), (38, 21)])],
                        anchors=[(28, 31), (36, 31)], cable=[(32, 58), (32, 58)]),
    "row_inverted": dict(label="Inverted row", base="none", view="side",
                         parts=[FLOOR, ("e", [(6, 22), (30, 22)]), ("e", [(8, 22), (8, 60)]),
                                ("h", (11, 37)), ("b", [(18, 22), (18, 37)]),
                                ("b", [(18, 37), (36, 47), (56, 57)])],
                         anchors=[(18, 22)]),
    "shrug": dict(label="Shrug", base="front_stand", view="front",
                  parts=[("b", [(26, 21), (23, 39)]), ("b", [(38, 21), (41, 39)]), ARROW_UP_L, ARROW_UP_R],
                  anchors=[(23, 42), (41, 42)], cable=[(6, 58), (58, 58)]),
    "carry": dict(label="Carry / hold", base="none", view="front",
                  parts=[FLOOR, HEAD_F, SHOULDERS_F, ("b", [(32, 21), (32, 40)]),
                         ("b", [(32, 40), (25, 59)]), ("b", [(32, 40), (40, 58)]),
                         ("b", [(26, 21), (22, 39)]), ("b", [(38, 21), (42, 39)])],
                  anchors=[(22, 42), (42, 42)]),
    "tricep_overhead": dict(label="Overhead tricep extension", base="none", view="side",
                            parts=[FLOOR, ("h", (24, 12)), ("b", [(29, 19), (30, 40)]),
                                   ("b", [(30, 40), (27, 59)]), ("b", [(30, 40), (33, 59)]),
                                   ("b", [(30, 21), (33, 4), (42, 12)])],
                            anchors=[(43, 13)], cable=[(58, 58)]),
    "tricep_overhead_seated": dict(label="Seated overhead tricep extension", base="none", view="side",
                                   parts=[("e", [(24, 43), (42, 43)]), ("e", [(33, 43), (33, 60)]),
                                          ("h", (24, 12)), ("b", [(29, 19), (30, 41)]),
                                          ("b", [(30, 41), (16, 42), (16, 58)]),
                                          ("b", [(30, 21), (33, 4), (42, 12)])],
                                   anchors=[(43, 13)], cable=[(58, 58)]),
    "skull": dict(label="Lying tricep extension", base="bench_flat", view="side",
                  parts=[("b", [(21, 41), (22, 24), (11, 28)])], anchors=[(9, 27)], cable=[(4, 58)],
                  ball=(26, 52, 8)),
    "kickback": dict(label="Kickback", base="none", view="side",
                     parts=[FLOOR, ("e", [(4, 44), (20, 44)]), ("e", [(10, 44), (10, 60)]),
                            ("h", (11, 27)), ("b", [(18, 30), (36, 36), (34, 47), (36, 59)]),
                            ("b", [(16, 31), (14, 44)]), ("b", [(21, 31), (30, 34), (44, 31)])],
                     anchors=[(46, 31)], cable=[(4, 58)]),
    "pushdown": dict(label="Pushdown", base="side_stand", view="side",
                     parts=[("b", [(29, 21), (31, 33), (21, 42)])], anchors=[(20, 43)], cable=[(6, 6)]),
    "bench_dip": dict(label="Bench dip", base="none", view="side",
                      parts=[FLOOR, ("e", [(38, 40), (58, 40)]), ("e", [(50, 40), (50, 60)]),
                             ("h", (36, 17)), ("b", [(42, 40), (38, 26)]),
                             ("b", [(38, 25), (36, 44), (20, 46), (8, 58)])],
                      anchors=[(30, 44)]),
    "pulldown": dict(label="Pulldown", base="front_seat", view="front",
                     parts=[("b", [(26, 21), (17, 32), (14, 18)]), ("b", [(38, 21), (47, 32), (50, 18)])],
                     anchors=[(14, 18), (50, 18)], cable=[(32, 2), (32, 2)]),
    "pullover": dict(label="Pullover", base="bench_flat", view="side",
                     parts=[("b", [(19, 41), (5, 34)]), ("a", "M8 22 Q18 18 24 28")],
                     anchors=[(4, 33)], cable=[(4, 58)], ball=(26, 52, 8)),
    "squat": dict(label="Squat", base="none", view="side",
                  parts=[FLOOR, ("h", (27, 15)), ("b", [(30, 23), (36, 42), (20, 44), (24, 58)]),
                         ("b", [(31, 25), (37, 30), (38, 23)])],
                  anchors=[(36, 23)], cable=[(4, 58)]),
    "squat_goblet": dict(label="Goblet / front squat", base="none", view="side",
                         parts=[FLOOR, ("h", (27, 15)), ("b", [(30, 23), (36, 42), (20, 44), (24, 58)]),
                                ("b", [(31, 25), (24, 34), (22, 29)])],
                         anchors=[(21, 29)], cable=[(4, 58)]),
    "squat_overhead": dict(label="Overhead squat", base="none", view="side",
                           parts=[FLOOR, ("h", (25, 15)), ("b", [(30, 23), (36, 42), (20, 44), (24, 58)]),
                                  ("b", [(30, 23), (32, 5)])],
                           anchors=[(32, 4)]),
    "lunge": dict(label="Lunge", base="none", view="side",
                  parts=[FLOOR, ("h", (30, 10)), ("b", [(30, 18), (31, 37), (18, 41), (20, 58)]),
                         ("b", [(31, 37), (40, 52), (50, 58)]), ("b", [(30, 20), (31, 34)])],
                  anchors=[(31, 38)], bar=[(34, 19)], cable=[(4, 58)], db_vertical=True),
    "stepup": dict(label="Step-up", base="none", view="side",
                   parts=[FLOOR, ("e", [(8, 46), (28, 46), (28, 60)]), ("h", (30, 10)),
                          ("b", [(31, 18), (32, 36), (20, 37), (19, 46)]), ("b", [(32, 36), (37, 48), (40, 59)]),
                          ("b", [(31, 20), (33, 33)])],
                   anchors=[(33, 37)], bar=[(35, 18)], db_vertical=True),
    "sissy": dict(label="Sissy squat", base="none", view="side",
                  parts=[FLOOR, ("h", (40, 14)), ("b", [(38, 22), (30, 36), (20, 46), (26, 59)]),
                         ("b", [(37, 24), (28, 28)])],
                  anchors=[(26, 28)]),
    "wall_squat": dict(label="Wall squat", base="none", view="side",
                       parts=[FLOOR, ("e", [(50, 4), (50, 60)]), ("h", (44, 12)),
                              ("b", [(45, 20), (45, 40), (27, 40), (27, 59)]), ("b", [(45, 22), (31, 24)])],
                       anchors=[(29, 24)]),
    "deadlift": dict(label="Deadlift", base="none", view="side",
                     parts=[FLOOR, ("h", (10, 30)), ("b", [(17, 33), (33, 36), (32, 47), (33, 58)]),
                            ("b", [(18, 34), (18, 48)])],
                     anchors=[(18, 52)], cable=[(18, 60)]),
    "good_morning": dict(label="Good morning", base="none", view="side",
                         parts=[FLOOR, ("h", (10, 30)), ("b", [(17, 33), (33, 36), (32, 47), (33, 58)]),
                                ("b", [(18, 34), (23, 30)])],
                         anchors=[(23, 28)]),
    "calf": dict(label="Calf raise", base="none", view="side",
                 parts=[("e", [(24, 54), (40, 54), (40, 60), (24, 60), (24, 54)]), ("h", (32, 8)),
                        ("b", [(32, 15), (32, 32), (32, 41), (31, 48), (36, 53)]), ("b", [(32, 17), (31, 32)]),
                        ("a", "M48 46 L48 30 M44 34 L48 29 L52 34")],
                 anchors=[(31, 35)], bar=[(36, 14)], db_vertical=True, cable=[(31, 60)]),
    "calf_seated": dict(label="Seated calf raise", base="none", view="side",
                        parts=[("e", [(24, 43), (42, 43)]), ("e", [(33, 43), (33, 60)]), HEAD_S,
                               ("b", [(29, 19), (30, 41), (16, 40), (16, 52), (10, 56)]),
                               ("b", [(29, 21), (22, 34), (17, 37)]), ("a", "M6 50 L6 38 M3 41 L6 37 L9 41")],
                        anchors=[(18, 35)]),
    "leg_curl_stand": dict(label="Standing leg curl", base="none", view="side",
                           parts=[FLOOR, ("e", [(10, 18), (10, 60)]), HEAD_S, ("b", [(29, 19), (30, 40)]),
                                  ("b", [(30, 40), (30, 59)]), ("b", [(30, 40), (34, 50), (45, 43)]),
                                  ("b", [(29, 23), (12, 30)])],
                           anchors=[(46, 43)], cable=[(60, 58)]),
    "bridge": dict(label="Hip thrust / bridge", base="none", view="side",
                   parts=[FLOOR, ("e", [(6, 40), (20, 40)]), ("e", [(13, 40), (13, 60)]), ("h", (9, 34)),
                          ("b", [(16, 38), (36, 35), (46, 38), (48, 59)])],
                   anchors=[(36, 31)], ball=(14, 46, 9)),
    "glute_kick": dict(label="Glute kickback", base="none", view="side",
                       parts=[FLOOR, ("h", (9, 38)), ("b", [(16, 59), (16, 42), (36, 42), (36, 59)]),
                              ("b", [(36, 42), (48, 36), (56, 26)])],
                       anchors=[(55, 27)], cable=[(60, 58)]),
    "reverse_crunch": dict(label="Reverse crunch", base="none", view="side",
                           parts=[FLOOR, ("h", (8, 54)), ("b", [(15, 57), (32, 56), (28, 40), (40, 36)]),
                                  ("b", [(16, 58), (26, 59)])],
                           anchors=[(38, 38)], ball=(36, 52, 7)),
    "situp": dict(label="Sit-up", base="none", view="side",
                  parts=[FLOOR, ("h", (23, 29)), ("b", [(26, 37), (34, 56), (44, 42), (55, 57)]),
                         ("b", [(27, 38), (33, 44)])],
                  anchors=[(31, 41)], ball=(30, 52, 8)),
    "twist": dict(label="Twist", base="none", view="side",
                  parts=[FLOOR, ("h", (20, 31)), ("b", [(24, 38), (32, 56), (42, 44), (52, 50)]),
                         ("b", [(25, 40), (36, 40)]), ("a", "M30 30 Q40 26 44 34")],
                  anchors=[(38, 40)], cable=[(60, 40)]),
    "vup": dict(label="V-up", base="none", view="side",
                parts=[FLOOR, ("h", (16, 32)), ("b", [(20, 38), (32, 56), (46, 34)]), ("b", [(21, 40), (40, 33)])],
                anchors=[(41, 32)], ball=(32, 52, 7)),
    "side_plank": dict(label="Side plank", base="none", view="side",
                       parts=[FLOOR, ("h", (12, 40)), ("b", [(18, 44), (56, 58)]),
                              ("b", [(24, 58), (16, 58), (18, 44)]), ("b", [(20, 44), (22, 28)])],
                       anchors=[(22, 26)]),
    "woodchop": dict(label="Wood chop", base="front_stand", view="front",
                     parts=[("b", [(26, 21), (14, 9)]), ("b", [(38, 21), (16, 10)]),
                            ("a", "M22 16 Q36 30 48 46")],
                     anchors=[(13, 7)], cable=[(4, 4)]),
    "mountain": dict(label="Mountain climber", base="none", view="side",
                     parts=[FLOOR, ("h", (10, 41)), ("b", [(16, 58), (17, 44)]),
                            ("b", [(17, 44), (36, 47), (56, 57)]), ("b", [(36, 47), (24, 49), (30, 56)])],
                     anchors=[]),
    "side_bend": dict(label="Side bend", base="none", view="front",
                      parts=[FLOOR, ("h", (23, 13)), ("b", [(32, 40), (27, 22)]), ("b", [(19, 22), (33, 21)]),
                             ("b", [(32, 40), (27, 59)]), ("b", [(32, 40), (37, 59)]),
                             ("b", [(19, 22), (14, 40)]), ("b", [(33, 21), (40, 30), (34, 36)])],
                      anchors=[(14, 43)], cable=[(6, 58)], db_vertical=True),
    "back_ext": dict(label="Back extension", base="none", view="side",
                     parts=[("e", [(30, 44), (42, 38)]), ("e", [(36, 41), (36, 60)]), ("e", [(50, 56), (58, 60)]),
                            ("h", (9, 36)), ("b", [(16, 37), (34, 40), (54, 57)]), ("b", [(18, 38), (24, 43)])],
                     anchors=[(22, 41)], ball=(34, 48, 9)),
    "clean": dict(label="Clean / front rack", base="side_stand", view="side",
                  parts=[("b", [(29, 21), (19, 25), (24, 20)])], anchors=[(23, 18)]),
    "overhead_lift": dict(label="Snatch / jerk", base="none", view="side",
                          parts=[FLOOR, ("h", (24, 12)), ("b", [(29, 19), (30, 40)]),
                                 ("b", [(30, 40), (20, 48), (16, 59)]), ("b", [(30, 40), (40, 50), (48, 59)]),
                                 ("b", [(29, 21), (31, 5)])],
                          anchors=[(31, 4)]),
    "swing": dict(label="Swing", base="none", view="side",
                  parts=[FLOOR, ("h", (17, 22)), ("b", [(22, 28), (36, 38), (30, 47), (33, 59)]),
                         ("b", [(23, 29), (10, 35)]), ("a", "M8 48 Q2 38 6 26")],
                  anchors=[(8, 38)], cable=[(30, 60)]),
    "throw": dict(label="Throw / slam", base="front_stand", view="front",
                  parts=[("b", [(26, 21), (24, 10), (30, 4)]), ("b", [(38, 21), (40, 10), (34, 4)])],
                  anchors=[(32, 3)]),
    "jump": dict(label="Jump", base="none", view="side",
                 parts=[FLOOR, ("e", [(40, 42), (58, 42), (58, 60), (40, 60), (40, 42)]), ("h", (21, 8)),
                        ("b", [(23, 15), (27, 32), (19, 37), (26, 45)]), ("b", [(24, 17), (34, 23)]),
                        ("a", "M10 52 Q22 40 36 36")],
                 anchors=[(35, 23)]),
    "rotation": dict(label="Rotation", base="front_stand", view="front",
                     parts=[("b", [(26, 21), (30, 31)]), ("b", [(38, 21), (34, 31)]),
                            ("a", "M14 32 Q32 46 50 32")],
                     anchors=[(32, 33)], cable=[(4, 32)]),
    "circles": dict(label="Arm circles", base="front_stand", view="front",
                    parts=[("b", [(26, 21), (12, 24)]), ("b", [(38, 21), (52, 24)]),
                           ("a", "M8 18 A6 6 0 1 0 16 18 M48 18 A6 6 0 1 0 56 18")],
                    anchors=[(10, 24), (54, 24)], db_vertical=True),
    "neck": dict(label="Neck", base="none", view="side",
                 parts=[FLOOR, ("h", (23, 13)), ("b", [(29, 19), (30, 40)]),
                        ("b", [(30, 40), (27, 59)]), ("b", [(30, 40), (33, 59)]),
                        ("b", [(29, 21), (18, 22), (20, 12)]), ("a", "M14 4 Q8 10 12 18")],
                 anchors=[(22, 7)]),
    "handstand": dict(label="Handstand", base="none", view="front",
                      parts=[FLOOR, ("h", (32, 50)), ("b", [(26, 59), (26, 42), (38, 42), (38, 59)]),
                             ("b", [(32, 42), (32, 22)]), ("b", [(32, 22), (28, 4)]), ("b", [(32, 22), (36, 4)])],
                      anchors=[]),
    # stretches and yoga
    "stretch_side": dict(label="Stretch", base="none", view="front",
                         parts=[FLOOR, ("h", (39, 13)), ("b", [(32, 40), (37, 22)]), ("b", [(31, 21), (44, 22)]),
                                ("b", [(32, 40), (27, 59)]), ("b", [(32, 40), (37, 59)]),
                                ("b", [(31, 21), (28, 6), (40, 2)]), ("b", [(44, 22), (46, 32), (39, 37)])],
                         anchors=[]),
    "stretch_fold": dict(label="Forward fold", base="none", view="side",
                         parts=[FLOOR, ("h", (22, 55)), ("b", [(32, 38), (32, 59)]), ("b", [(32, 38), (35, 59)]),
                                ("b", [(32, 38), (26, 49)]), ("b", [(27, 50), (30, 58)])],
                         anchors=[]),
    "stretch_quad": dict(label="Quad stretch", base="none", view="side",
                         parts=[FLOOR, HEAD_S, ("b", [(29, 19), (30, 40)]), ("b", [(30, 40), (30, 59)]),
                                ("b", [(30, 40), (32, 52), (41, 40)]), ("b", [(29, 21), (36, 34), (40, 40)])],
                         anchors=[]),
    "stretch_arm": dict(label="Arm stretch", base="front_stand", view="front",
                        parts=[("b", [(26, 21), (44, 25)]), ("b", [(38, 21), (40, 31), (34, 26)])],
                        anchors=[]),
    "stretch_lying": dict(label="Lying stretch", base="none", view="side",
                          parts=[FLOOR, ("h", (8, 54)), ("b", [(15, 57), (36, 57), (54, 57)]),
                                 ("b", [(34, 57), (28, 40), (38, 36)]), ("b", [(16, 56), (28, 42)])],
                          anchors=[]),
    "stretch_seated": dict(label="Seated stretch", base="none", view="side",
                           parts=[FLOOR, ("h", (34, 36)), ("b", [(14, 57), (34, 57)]),
                                  ("b", [(14, 57), (28, 42)]), ("b", [(29, 44), (42, 54)])],
                           anchors=[]),
    "cobra": dict(label="Cobra", base="none", view="side",
                  parts=[FLOOR, ("h", (14, 32)), ("b", [(56, 58), (34, 56), (18, 40)]), ("b", [(18, 42), (20, 58)])],
                  anchors=[]),
    "child": dict(label="Child's pose", base="none", view="side",
                  parts=[FLOOR, ("h", (18, 53)), ("b", [(46, 59), (34, 58), (44, 51), (24, 54)]),
                         ("b", [(23, 55), (6, 58)])],
                  anchors=[]),
    "dog": dict(label="Downward dog", base="none", view="side",
                parts=[FLOOR, ("h", (20, 46)), ("b", [(12, 59), (34, 24), (54, 59)])],
                anchors=[]),
    "warrior": dict(label="Warrior / lunge pose", base="none", view="side",
                    parts=[FLOOR, ("h", (32, 12)), ("b", [(32, 20), (32, 40)]),
                           ("b", [(32, 40), (20, 46), (18, 59)]), ("b", [(32, 40), (46, 52), (54, 59)]),
                           ("b", [(32, 22), (30, 4)])],
                    anchors=[]),
    "stork": dict(label="Balance pose", base="none", view="front",
                  parts=[FLOOR, HEAD_F, SHOULDERS_F, ("b", [(32, 21), (32, 40)]), ("b", [(32, 40), (32, 59)]),
                         ("b", [(32, 40), (41, 47), (33, 51)]), ("b", [(26, 21), (30, 4)]), ("b", [(38, 21), (34, 4)])],
                  anchors=[]),
}

# Seated versions of the standing poses that have one.
SEATED = {"curl": "front_seat", "press_overhead": "front_seat", "lateral": "front_seat",
          "shrug": "front_seat", "tricep_overhead": None, "front_raise": "side_seat"}

EQUIPMENT_LABELS = {
    "barbell": "Barbell", "ez": "EZ bar", "smith": "Smith machine", "dumbbell": "Dumbbell",
    "kettlebell": "Kettlebell", "cable": "Cable", "band": "Band", "machine": "Machine",
    "medball": "Medicine ball", "ball": "Stability ball", "plate": "Plate", "none": "Bodyweight",
}


def equipment_of(name):
    n = name.lower()
    for key, pattern in [
        ("smith", r"smith"), ("ez", r"\bez\b"), ("barbell", r"barbell|\bbar\b(?! dip)"),
        ("dumbbell", r"dumbbell"), ("kettlebell", r"kettlebell"), ("cable", r"cable|pulley|rope"),
        ("band", r"\bband"), ("medball", r"medicine ball"), ("ball", r"stability ball|swiss ball"),
        ("plate", r"\bplate\b|weighted"), ("machine", r"machine|leverage|\bsled\b"),
    ]:
        if re.search(pattern, n):
            return key
    return "none"


def draw_load(pose, equipment, one_arm):
    """The strokes for the equipment at the pose's anchors."""
    anchors = list(pose["anchors"])
    if equipment in ("barbell", "smith", "plate") and pose.get("bar"):
        anchors = list(pose["bar"])
    if not anchors:
        return [], []
    if one_arm:
        anchors = anchors[:1]
    behind, front = [], []          # gray parts go under the body, weights over it
    front_view = pose["view"] == "front"
    cables = pose.get("cable") or [(4, 58)] * len(anchors)

    if equipment in ("barbell", "smith", "ez"):
        if front_view and len(anchors) > 1:
            xs = [x for x, _ in anchors]
            y = round(sum(y for _, y in anchors) / len(anchors))
            x0, x1 = min(xs) - 8, max(xs) + 8
            if equipment == "ez":
                mid = (x0 + x1) / 2
                front.append(("p", f"M{x0} {y} H{mid - 9:g} L{mid - 5:g} {y - 3} L{mid:g} {y + 2} "
                                   f"L{mid + 5:g} {y - 3} L{mid + 9:g} {y} H{x1}", "w"))
            else:
                front.append(("w", [(x0, y), (x1, y)]))
            front += [("w", [(x0 - 2, y - 6), (x0 - 2, y + 6)]), ("w", [(x1 + 2, y - 6), (x1 + 2, y + 6)])]
        else:
            front += [("c", (x, y, 6)) for x, y in anchors]
        if equipment == "smith":
            behind += [("e", [(5, 2), (5, 60)]), ("e", [(59, 2), (59, 60)])]
    elif equipment == "dumbbell":
        for x, y in anchors:
            front += dumbbell(x, y, horizontal=not pose.get("db_vertical"))
    elif equipment == "kettlebell":
        for x, y in anchors:
            front += [("c", (x, y + 3, 4)), ("w", [(x - 2.5, y - 2), (x + 2.5, y - 2)])]
    elif equipment == "plate":
        if front_view and len(anchors) > 1:
            xs = [x for x, _ in anchors]
            ys = [y for _, y in anchors]
            front.append(("c", (sum(xs) / len(xs), sum(ys) / len(ys), 6)))
        else:
            front.append(("c", (anchors[0][0], anchors[0][1], 6)))
    elif equipment == "medball":
        xs = [x for x, _ in anchors]
        ys = [y for _, y in anchors]
        front.append(("f", (sum(xs) / len(xs), sum(ys) / len(ys), 5)))
    elif equipment == "cable":
        for (x, y), (px, py) in zip(anchors, cables):
            post_x = 2 if px < 32 else 62
            behind += [("e", [(post_x, 2), (post_x, 60)]), ("e", [(px, py), (x, y)])]
            front.append(("w", [(x - 3, y), (x + 3, y)]))
    elif equipment == "band":
        for (x, y), (px, py) in zip(anchors, cables):
            bx, by = (px, py) if py < 50 else (x, 60)
            front.append(("d", f"M{x:g} {y:g} Q{(x + bx) / 2 + 6:g} {(y + by) / 2:g} {bx:g} {by:g}"))
    elif equipment == "machine":
        for x, y in anchors:
            behind.append(("e", [(x - 5, y), (x + 5, y)]))
        x, y = anchors[0]
        post_x = 60 if x < 32 else 4
        behind += [("e", [(post_x, 4), (post_x, 60)]), ("e", [(post_x, y), (x, y)])]
    elif equipment == "ball":
        if pose.get("ball"):
            behind.append(("g", pose["ball"]))
        else:
            behind.append(("g", (52, 50, 8)))
    return behind, front


# Name -> pose. First match wins; "=slug" means "use that hand-drawn icon".
RULES = [
    (r"handstand", "handstand"),
    (r"\bcobra\b", "cobra"), (r"child", "child"), (r"\bdog\b", "dog"),
    (r"warrior|crescent|lunge pose", "warrior"), (r"stork|tree pose|eagle|dancer", "stork"),
    (r"stretch|pose\b|yoga", None),                      # decided by stretch_pose()
    (r"muscle.?up", "=muscle-up"),
    (r"front lever|back lever|planche", "=front-lever-raise"),
    (r"pull.?up|chin.?up|pullup", "=pull-up"),
    (r"pull.?down", "pulldown"),
    (r"pullover", "pullover"),
    (r"bench dip|chair dip", "bench_dip"),
    (r"\bdips?\b", "=dip"),
    (r"push.?up|pushup", None),                          # decided by pushup_icon()
    (r"side plank|side bridge", "side_plank"),
    (r"plank", "=plank"),
    (r"reverse crunch", "reverse_crunch"),
    (r"cable crunch|kneeling crunch", "=cable-crunch"),
    (r"crunch", "=bench-crunch"),
    (r"sit.?up|situp", "situp"),
    (r"russian twist|twist", "twist"),
    (r"v.?up|jackknife|jack knife|toe touch", "vup"),
    (r"hanging (leg|knee)|hanging raise", "=hanging-leg-raise"),
    (r"parallel bar|captain", "=parallel-bar-leg-raise"),
    (r"(leg|knee) raise|flutter|scissor|hundreds", "=leg-raise"),
    (r"roll.?out|ab roll|ab wheel|wheel", "=ab-roll"),
    (r"chop", "woodchop"),
    (r"climber(?!.*pull)", "mountain"),
    (r"side bend|oblique", "side_bend"),
    (r"hyperextension|back extension|\bhyper\b|superman", "back_ext"),
    (r"good morning", "good_morning"),
    (r"deadlift|\brdl\b|pull.?through", "deadlift"),
    (r"clean|high pull", "clean"),
    (r"snatch|jerk|get.?up", "overhead_lift"),
    (r"swing", "swing"),
    (r"throw|slam|toss|\bpass\b|catch", "throw"),
    (r"jump|bound|\bhop\b|burpee|skipping", "jump"),
    (r"hip thrust|glute bridge|bridge|pelvic|hip lift|hip raise", "bridge"),
    (r"abduction", "=machine-hip-abduction"), (r"adduction", "=machine-hip-adduction"),
    (r"seated calf|calf.*seated", "calf_seated"),
    (r"calf|heel raise|toe raise|donkey calf", "calf"),
    (r"leg extension", "=machine-leg-extension"),
    (r"(leg|hamstring) curl", None),                     # decided by leg_curl_icon()
    (r"leg press", "=machine-leg-press"),
    (r"hack squat", "=hack-squat"),
    (r"bulgarian", "=barbell-bulgarian-split-squat"),
    (r"step.?up", "stepup"),
    (r"lunge|split squat|split", "lunge"),
    (r"sissy", "sissy"),
    (r"wall (squat|sit)", "wall_squat"),
    (r"overhead squat", "squat_overhead"),
    (r"squat", None),                                    # decided by squat_pose()
    (r"shrug", "shrug"),
    (r"upright row", "row_upright"),
    (r"inverted row|body row|australian", "row_inverted"),
    (r"face pull", "=cable-rope-face-pull"),
    (r"one.?arm.*\brow|single.?arm.*\brow|\brow.*one.?arm", None),   # row_icon()
    (r"\brow", None),                                    # row_icon()
    (r"push.?down|press.?down", "pushdown"),
    (r"skull|lying tricep|jm press|tricep extension.*(lying|supine|bench|decline)", "skull"),
    (r"kickback|kick back|kick", None),                  # kick_pose()
    (r"tricep|french press|overhead extension", None),   # tricep_pose()
    (r"wrist|forearm|finger|reverse grip curl", "wrist_curl"),
    (r"preacher|scott|spider curl", "preacher"),
    (r"concentration", "concentration"),
    (r"curl", "curl"),
    (r"reverse fly|rear delt|rear fly|reverse flye|prone deltoid|face away|y raise|t raise|rear lateral", "rear_raise"),
    (r"bent.?over.*raise|bent.?over lateral", "rear_raise"),
    (r"fly|flye|crossover|pec deck", None),              # fly_pose()
    (r"front raise", "front_raise"),
    (r"lateral|side raise|raise", "lateral"),
    (r"circle|halo|around the world", "circles"),
    (r"rotation|rotational|windmill|woodchopper|twist", "rotation"),
    (r"neck", "neck"),
    (r"shoulder press|military|overhead press|arnold|push press|z press|landmine press", "press_overhead"),
    (r"chest press|machine press|lever.*press|press.*machine", "chest_press"),
    (r"incline", "press_incline"),
    (r"decline", "press_decline"),
    (r"press|floor", "press_bench"),
    (r"carry|farmer|walk|hold|hang\b|hanging", "carry"),
    (r"extension", "back_ext"),
]

GROUP_FALLBACK = {"chest": "press_bench", "back": "row_bent", "shoulders": "press_overhead",
                  "triceps": "pushdown", "biceps": "curl", "upper_legs": "squat",
                  "lower_legs": "calf", "glutes": "bridge", "abs": "=bench-crunch", "forearm": "wrist_curl"}


def stretch_pose(n):
    if re.search(r"quad|thigh|hip flexor", n):
        return "stretch_quad"
    if re.search(r"hamstring|forward|toe|calf|bend", n):
        return "stretch_fold"
    if re.search(r"seated|butterfly|groin|sitting", n):
        return "stretch_seated"
    if re.search(r"lying|supine|knee to chest|piriformis|glute|lower back", n):
        return "stretch_lying"
    if re.search(r"chest|shoulder|arm|tricep|bicep|wrist|lat\b|upper back|neck", n):
        return "stretch_arm"
    return "stretch_side"


def resolve_pose(name, group):
    n = name.lower()
    for pattern, pose in RULES:
        if not re.search(pattern, n):
            continue
        if pose is not None:
            return pose
        if re.search(r"stretch|pose\b|yoga", n):
            return stretch_pose(n)
        if re.search(r"push.?up|pushup", n):
            if re.search(r"decline|feet elevated", n):
                return "=decline-push-up-handles"
            if re.search(r"incline|bench|elevated|wall", n):
                return "=bench-push-up"
            return "=push-up"
        if re.search(r"(leg|hamstring) curl", n):
            if "stand" in n:
                return "leg_curl_stand"
            if "seated" in n:
                return "=machine-seated-leg-curl"
            if "ball" in n:
                return "bridge"
            return "=machine-leg-curl-prone"
        if "squat" in n:
            return "squat" if equipment_of(name) in ("barbell", "smith", "band", "machine") else "squat_goblet"
        if re.search(r"\brow", n):
            if re.search(r"one.?arm|single.?arm", n) and equipment_of(name) == "dumbbell":
                return "=dumbbell-one-arm-row"
            if re.search(r"seated|cable|machine|lever|t.?bar|rear delt|high row|low row", n):
                return "row_seated"
            return "row_bent"
        if re.search(r"kick", n):
            return "kickback" if group == "triceps" or "tricep" in n else "glute_kick"
        if re.search(r"tricep|french press|overhead extension", n):
            return "tricep_overhead_seated" if "seated" in n else "tricep_overhead"
        if re.search(r"fly|flye|crossover|pec deck", n):
            return "fly_bench" if re.search(r"bench|lying|incline|decline|flat|ball", n) else "fly"
    return GROUP_FALLBACK.get(group, "press_bench")


def generated_icon(name, group):
    """(file name, label, strokes) for one exercise, or ("=slug", ...) for a
    hand-drawn one."""
    pose_key = resolve_pose(name, group)
    if pose_key.startswith("="):
        return pose_key[1:], None, None
    n = name.lower()
    equipment = equipment_of(name)
    one_arm = bool(re.search(r"one.?arm|single.?arm|alternat|one.?leg|single.?leg|unilateral", n))
    pose = dict(POSES[pose_key])
    base = pose["base"]
    if "seated" in n and pose_key in SEATED and SEATED[pose_key]:
        base = SEATED[pose_key]
        if pose_key == "front_raise":
            pose["parts"] = [("b", [(29, 21), (12, 20)])]
    behind, front = draw_load(pose, equipment, one_arm)
    strokes = behind + BASES[base] + pose["parts"] + front

    parts = [pose_key.replace("_", "-"), equipment]
    label = [pose["label"], EQUIPMENT_LABELS[equipment]]
    if base != pose["base"]:
        parts.append("seated")
        label.append("seated")
    if one_arm and pose["anchors"] and equipment != "none" and len(pose["anchors"]) > 1:
        parts.append("one-arm")
        label.append("one arm")
    return "x-" + "-".join(parts), " · ".join(label), strokes


def catalog_names():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "workout.db")
    if not os.path.exists(db_path):
        return []
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT exercise_name, muscle_group FROM exercises").fetchall()


def main():
    os.makedirs(OUT, exist_ok=True)
    # Start clean, so a pose that no exercise uses any more leaves no file.
    for old in os.listdir(OUT):
        if old.endswith(".svg"):
            os.remove(os.path.join(OUT, old))

    labels, total = {}, 0

    def write(file_name, label, strokes):
        nonlocal total
        svg = render(strokes)
        with open(os.path.join(OUT, file_name + ".svg"), "w", encoding="utf-8", newline="") as f:
            f.write(svg)
        labels[file_name] = label
        total += len(svg.encode())

    for name, strokes in ICONS.items():
        write(slug(name), name, strokes)
    drawn = len(labels)

    mapping, generated = {}, {}
    for name, group in catalog_names():
        if slug(name) in labels:
            continue                                  # has its own drawing
        file_name, label, strokes = generated_icon(name, group)
        if strokes is not None and file_name not in generated:
            generated[file_name] = (label, strokes)
        mapping[name] = file_name
    for file_name in sorted(generated, key=lambda f: generated[f][0]):
        write(file_name, *generated[file_name])

    # The icon library, in picker order: the hand-drawn ones first.
    with open(os.path.join(OUT, "icons.json"), "w", encoding="utf-8", newline="") as f:
        json.dump(labels, f, ensure_ascii=False, indent=0)
    map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "exercise_icons.json")
    with open(map_path, "w", encoding="utf-8", newline="") as f:
        json.dump(dict(sorted(mapping.items())), f, ensure_ascii=False, indent=1)

    print(f"{drawn} drawn + {len(generated)} generated icons, {total} bytes; "
          f"{len(mapping)} exercises mapped to a shared icon")


if __name__ == "__main__":
    main()
