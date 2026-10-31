"""Generate the stick-figure exercise icons (64x64 SVG, a few hundred bytes each)
into static/icons/exercises - the icon library /admin/exercises picks from -
plus icons.json (their labels) and data/exercise_icons.json (which icon each
catalog exercise without its own drawing gets; read from instance/workout.db).

Each icon is a list of strokes: ("b", points) body, ("e", points) equipment,
("w", points) weight, ("h", (x, y)) head, ("c", (x, y, r)) weight plate,
("p", d, kind) a raw path, ("a", d) a motion arrow.

Every icon with an end pose - ANIMATED for the drawn ones, POSE_ENDS for the
generated ones - also gets static/icons/exercises/anim/<file>.svg, moving
between its drawing and that pose (SMIL, ~1 KB more). Holds have none.

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


def element(s):
    """A stroke as (tag, {the attributes that place it}, the rest)."""
    k = s[0]
    if k == "b":
        return "polyline", {"points": pts(s[1])}, f'stroke="{BODY}" stroke-width="4.5"'
    if k == "e":
        return "polyline", {"points": pts(s[1])}, f'stroke="{EQUIP}" stroke-width="3"'
    if k == "w":
        return "polyline", {"points": pts(s[1])}, f'stroke="{WEIGHT}" stroke-width="4"'
    if k == "h":
        x, y = s[1]
        return "circle", {"cx": f"{x:g}", "cy": f"{y:g}"}, f'r="4.6" fill="{BODY}"'
    if k == "c":
        x, y, r = s[1]
        return "circle", {"cx": f"{x:g}", "cy": f"{y:g}"}, f'r="{r:g}" stroke="{WEIGHT}" stroke-width="3.5"'
    if k == "p":
        color, width = {"b": (BODY, 4.5), "e": (EQUIP, 3), "w": (WEIGHT, 4)}[s[2]]
        return "path", {"d": s[1]}, f'stroke="{color}" stroke-width="{width}"'
    if k == "a":
        return "path", {"d": s[1]}, f'stroke="{ARROW}" stroke-width="2.2" stroke-dasharray="3 3"'
    if k == "f":                                         # medicine ball
        x, y, r = s[1]
        return "circle", {"cx": f"{x:g}", "cy": f"{y:g}"}, f'r="{r:g}" fill="{WEIGHT}"'
    if k == "g":                                         # stability ball
        x, y, r = s[1]
        return "circle", {"cx": f"{x:g}", "cy": f"{y:g}"}, f'r="{r:g}" stroke="{EQUIP}" stroke-width="3"'
    if k == "d":                                         # band
        return "path", {"d": s[1]}, f'stroke="{WEIGHT}" stroke-width="2.4" stroke-dasharray="2 3"'
    raise ValueError(f"unknown stroke kind {k!r}")


# One rep, 2 s: the drawn pose -> the other end (40 %), hold, back (40 %),
# hold. Eased, so it reads as a movement rather than a slide.
EASE = ".45 0 .55 1"
ANIMATE = ('<animate attributeName="{0}" values="{1};{2};{2};{1};{1}" keyTimes="0;.4;.5;.9;1" '
           f'calcMode="spline" keySplines="{EASE};{EASE};{EASE};{EASE}" dur="2s" repeatCount="indefinite"/>')


def render(strokes, end=None):
    """The icon as SVG. With end - the same strokes in the other pose of the
    rep, point for point - every stroke that moves is animated between them,
    and the motion arrows go: the movement itself says it better."""
    if end is not None:
        strokes = [s for s in strokes if s[0] != "a"]
        end = [s for s in end if s[0] != "a"]
    if end is not None and len(end) != len(strokes):
        raise ValueError(f"end pose has {len(end)} strokes, the icon {len(strokes)}")
    parts = []
    for i, s in enumerate(strokes):
        tag, place, rest = element(s)
        anims = ""
        if end is not None:
            end_tag, end_place, _ = element(end[i])
            if end_tag != tag or (tag == "polyline" and len(end[i][1]) != len(s[1])):
                raise ValueError(f"stroke {i} does not match its end pose")
            anims = "".join(ANIMATE.format(attr, place[attr], end_place[attr])
                            for attr in place if end_place[attr] != place[attr])
        attrs = " ".join(f'{attr}="{value}"' for attr, value in place.items())
        parts.append(f"<{tag} {attrs} {rest}>{anims}</{tag}>" if anims else f"<{tag} {attrs} {rest}/>")
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" '
            'stroke-linecap="round" stroke-linejoin="round">' + "".join(parts) + "</svg>")


def moved(strokes, changes):
    """strokes with some replaced - {index: stroke}, or {index: [strokes]}
    for a run of them (a dumbbell is three). How an end pose is written."""
    out = list(strokes)
    for i, new in changes.items():
        new = new if isinstance(new, list) else [new]
        out[i:i + len(new)] = new
    return out


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
        ("b", [(20, 58), (20.5, 50.5), (21, 43)]),       # elbow mid-arm: it bends in ANIMATED
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
        ("b", [(20, 41), (20, 31.5), (20, 22)]),
        *dumbbell(20, 18),
    ],
    "Dumbbell Incline Bench Press": [
        ("e", [(17, 24), (36, 48), (50, 48)]), ("e", [(38, 48), (38, 60)]),
        ("h", (17, 19)),
        ("b", [(22, 27), (36, 44), (48, 42), (50, 59)]),
        ("b", [(23, 28), (24, 19.5), (25, 11)]),
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
        ("b", [(21, 55), (21, 50), (21, 45)]),
        ("b", [(20, 45), (36, 40), (50, 35)]),
    ],
    "Bench Push-Up": [
        FLOOR, ("e", [(4, 38), (24, 38)]), ("e", [(14, 38), (14, 60)]),
        ("h", (16, 22)),
        ("b", [(18, 38), (20, 33), (22, 28)]),
        ("b", [(22, 28), (39, 43), (56, 57)]),
    ],
    "Barbell Bench Press": [
        ("e", [(8, 46), (50, 46)]), ("e", [(14, 46), (14, 60)]), ("e", [(44, 46), (44, 60)]),
        ("h", (11, 40)),
        ("b", [(18, 41), (36, 41), (46, 36), (50, 59)]),
        ("b", [(20, 41), (20, 32.5), (20, 24)]),
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
        ("b", [(22, 32), (24, 25), (26, 18), (38, 18), (40, 25), (42, 32)]),
        ("b", [(32, 18), (32, 38), (29, 52), (31, 60)]), ("b", [(32, 38), (35, 52), (33, 60)]),
    ],
}


# ---- third batch: the logged exercises that shared a drawing with a sibling
# get their own - the same movement, drawn with what tells them apart (grip,
# handle, seat, machine, stance, what is held). Built from the drawing they
# shared, so the family still looks like one.
_PULLDOWN, _CURL, _DIP = ICONS["Machine Lat Pulldown"], ICONS["Dumbbell Bicep Curl"], ICONS["Dip"]
_INCLINE, _SLD, _CRUNCH = ICONS["Dumbbell Incline Bench Press"], ICONS["Barbell Stiff-Leg Deadlift"], ICONS["Bench Crunch"]
_SKULL, _BENCH, _PRESS = ICONS["EZ Bar Tricep Extension"], ICONS["Barbell Bench Press"], ICONS["Dumbbell Shoulder Press"]
_LEG_PRESS, _MILITARY, _EZ_CURL = ICONS["Machine Leg Press"], ICONS["Barbell Military Press"], ICONS["EZ Bar Curl"]
SEAT_F = [("e", [(20, 44), (44, 44)]), ("e", [(32, 44), (32, 60)])]
SEATED_LEGS_F = [("b", [(32, 21), (32, 41), (24, 45), (24, 58)]), ("b", [(32, 41), (40, 45), (40, 58)])]
STANDING_LEGS_F = [("b", [(32, 21), (32, 41), (27, 58)]), ("b", [(32, 41), (37, 58)])]
SMITH_RAILS = [("e", [(5, 2), (5, 60)]), ("e", [(59, 2), (59, 60)])]

ICONS.update({
    "Cable Lat Pulldown (Wide Grip)": moved(_PULLDOWN, {
        3: ("w", [(4, 20), (60, 20)]),
        5: ("b", [(8, 20), (12, 33), (27, 25), (37, 25), (52, 33), (56, 20)]),
    }),
    "Cable Grip Lat Pulldown (Narrow Grip)": moved(_PULLDOWN, {
        0: ("e", [(32, 2), (32, 22)]),
        3: ("w", [(21, 22), (43, 22)]),
        5: ("b", [(24, 22), (20, 33), (27, 25), (37, 25), (44, 33), (40, 22)]),
    }),
    "Cable Front Lat Pulldown (Close Grip)": moved(_PULLDOWN, {     # V-handle to the chest
        0: ("e", [(32, 2), (32, 19)]),
        3: ("w", [(28, 25), (32, 19), (36, 25)]),
        5: ("b", [(29, 25), (21, 34), (27, 25), (37, 25), (43, 34), (35, 25)]),
    }),
    "Machine One-Arm Pulldown": [
        ("e", [(46, 2), (46, 18)]), ("e", [(22, 50), (42, 50)]), ("e", [(32, 50), (32, 60)]),
        ("w", [(43, 18), (49, 18)]),
        ("h", (32, 13)),
        ("b", [(23, 45), (21, 35), (27, 25), (37, 25), (45, 31), (46, 18)]),
        ("b", [(32, 25), (32, 47), (25, 51), (25, 60)]), ("b", [(32, 47), (39, 51), (39, 60)]),
    ],
    "Cable Bicep Curl": [                                # bar on a cable from the floor
        FLOOR, ("e", [(26, 58), (38, 58)]), ("e", [(32, 57), (32, 25)]),
        ("h", (32, 12)),
        ("b", [(27, 21), (37, 21)]),
        ("b", [(27, 21), (24, 34), (22, 25)]), ("b", [(37, 21), (40, 34), (42, 25)]),
        ("w", [(17, 25), (47, 25)]),
        *STANDING_LEGS_F,
    ],
    "Dumbbell Hammer Curl": [                            # dumbbells upright: palms in
        FLOOR,
        ("h", (32, 12)),
        ("b", [(23, 44), (24, 34), (27, 21), (37, 21), (40, 34), (44, 24)]),
        *dumbbell(23, 48, horizontal=False), *dumbbell(44, 22, horizontal=False),
        *STANDING_LEGS_F,
    ],
    "Dumbbell Seated Bicep Curl": [
        *SEAT_F,
        ("h", (32, 12)),
        ("b", [(18, 40), (22, 32), (27, 21), (37, 21), (40, 34), (44, 24)]),
        *dumbbell(18, 43), *dumbbell(44, 21),
        *SEATED_LEGS_F,
    ],
    "Weighted Tricep Dip": _DIP + [("e", [(32, 40), (32, 47)]), ("c", (32, 51, 4))],
    "Machine Dip": [("e", [(24, 52), (40, 52)]), ("e", [(32, 52), (32, 60)])] + _DIP,   # knee pad
    "Machine Seated Tricep Dip": [
        ("e", [(14, 44), (36, 44)]), ("e", [(26, 44), (26, 60)]), ("e", [(40, 12), (40, 44)]),
        ("h", (32, 11)),
        ("b", [(33, 19), (34, 42), (16, 44), (18, 58)]),
        ("w", [(30, 40), (42, 40)]),
        ("b", [(33, 21), (35, 30), (36, 40)]),
    ],
    "Barbell Incline Bench Press": _INCLINE[:5] + [("c", (25, 7, 6))],
    "Machine Incline Chest Press": [
        ("e", [(4, 2), (4, 60)]), ("e", [(17, 24), (36, 48), (50, 48)]), ("e", [(38, 48), (38, 60)]),
        ("e", [(4, 6), (25, 10)]),
        ("h", (17, 19)),
        ("b", [(22, 27), (36, 44), (48, 42), (50, 59)]),
        ("b", [(23, 28), (24, 19.5), (25, 11)]),
        ("w", [(22, 10), (28, 10)]),
    ],
    "Cable Side Lateral Raise": [                        # one arm, cable from the far low pulley
        FLOOR, ("e", [(60, 4), (60, 60)]), ("e", [(58, 56), (12, 23)]),
        ("h", (32, 12)),
        ("b", [(13, 23), (26, 21), (38, 21), (41, 34)]),
        ("w", [(10, 21), (14, 25)]),
        ("b", [(32, 21), (32, 40), (27, 58)]), ("b", [(32, 40), (37, 58)]),
    ],
    "Dumbbell Seated Side Lateral Raise": [
        *SEAT_F,
        ("h", (32, 12)),
        ("b", [(13, 23), (26, 21), (38, 21), (51, 23)]),
        *SEATED_LEGS_F,
        *dumbbell(10, 23, horizontal=False), *dumbbell(54, 23, horizontal=False),
    ],
    "Chin-Up": [                                         # hands close together
        ("e", [(8, 9), (56, 9)]),
        ("b", [(26, 9), (21, 21), (27, 26), (37, 26), (43, 21), (38, 9)]),
        ("h", (32, 17)),
        ("b", [(32, 25), (32, 42)]),
        ("b", [(32, 42), (28, 51), (31, 59)]), ("b", [(32, 42), (36, 51), (33, 59)]),
    ],
    "Assisted One-Arm Pull-Up": [                        # the other hand on a band
        ("e", [(8, 9), (56, 9)]),
        ("d", "M44 9 Q48 17 44 26"),
        ("b", [(28, 9), (22, 21), (27, 26), (37, 26), (44, 25)]),
        ("h", (32, 17)),
        ("b", [(32, 25), (32, 42)]),
        ("b", [(32, 42), (28, 51), (31, 59)]), ("b", [(32, 42), (36, 51), (33, 59)]),
    ],
    "Cable Tricep Pushdown (Rope)": [                    # the rope splits at the bottom
        FLOOR, ("e", [(32, 2), (32, 26)]),
        ("h", (32, 12)),
        ("b", [(24, 44), (25, 32), (27, 21), (37, 21), (39, 32), (40, 44)]),
        ("w", [(24, 44), (32, 26), (40, 44)]),
        *STANDING_LEGS_F,
    ],
    "Cable Tricep Pushdown (V-Bar)": [
        FLOOR, ("e", [(32, 2), (32, 38)]),
        ("h", (32, 12)),
        ("b", [(30, 44), (25, 33), (27, 21), (37, 21), (39, 33), (34, 44)]),
        ("w", [(28, 46), (32, 38), (36, 46)]),
        *STANDING_LEGS_F,
    ],
    "Barbell Romanian Deadlift": [                       # soft knees, bar only to the shins
        FLOOR,
        ("h", (10, 27)),
        ("b", [(17, 31), (35, 34), (29, 46), (33, 58)]),
        ("b", [(19, 32), (22, 44)]),
        ("c", (22, 48, 6.5)),
    ],
    "Dumbbell Stiff-Leg Deadlift": _SLD[:4] + dumbbell(18, 51),
    "Machine Ab Crunch": [
        ("e", [(20, 46), (40, 46)]), ("e", [(30, 46), (30, 60)]), ("e", [(48, 8), (48, 60)]),
        ("e", [(48, 14), (28, 30)]),
        ("p", "M38 44 Q30 40 26 31", "b"),
        ("h", (23, 26)),
        ("b", [(38, 44), (20, 46), (22, 58)]),
    ],
    "Oblique Crunch": [                                  # knees dropped, elbow across
        FLOOR,
        ("p", "M34 56 Q24 54 21 45", "b"),
        ("h", (19, 38)),
        ("b", [(34, 56), (46, 48), (56, 57)]),
        ("b", [(22, 46), (31, 44)]),
        ("a", "M14 30 Q22 24 30 30"),
    ],
    "EZ Bar Tricep Extension (Close Grip)": _SKULL[:5] + [("b", [(21, 41), (22, 24), (14, 33)]), ("c", (12, 33, 4))],
    "Barbell JM Press": _BENCH[:5] + [("b", [(20, 41), (29, 33), (23, 27)]), ("c", (23, 23, 6))],
    "Hack Squat (Narrow Stance)": [                      # front view, feet together
        ("e", [(14, 4), (14, 60)]), ("e", [(50, 4), (50, 60)]), ("e", [(18, 60), (46, 60)]),
        ("h", (32, 18)),
        ("e", [(22, 26), (42, 26)]),
        ("b", [(22, 32), (25, 26), (39, 26), (42, 32)]),
        ("b", [(32, 26), (32, 42)]),
        ("b", [(32, 42), (25, 49), (29, 59)]), ("b", [(32, 42), (39, 49), (35, 59)]),
    ],
    "Machine Squat": [                                   # shoulder pads on a lever, no bar
        FLOOR, ("e", [(56, 4), (56, 60)]), ("e", [(56, 10), (32, 23)]),
        ("h", (27, 15)),
        ("b", [(30, 23), (36, 42), (20, 44), (24, 58)]),
        ("b", [(31, 25), (37, 30), (38, 23)]),
    ],
    "Machine Leg Press (Narrow Stance)": _LEG_PRESS[:5] + [   # both legs side by side, feet low
        ("b", [(13, 30), (24, 49), (36, 34), (50, 40)]),
        _LEG_PRESS[6],
        ("b", [(24, 49), (38, 36), (51, 42)]),
    ],
    "Machine Single-Leg Press": _LEG_PRESS + [("b", [(24, 49), (35, 52), (36, 60)])],   # other foot down
    "Machine Shoulder Press": [
        ("e", [(8, 4), (8, 46)]), ("e", [(56, 4), (56, 46)]),
        ("e", [(8, 34), (19, 9)]), ("e", [(56, 34), (45, 9)]),
    ] + _PRESS[:6] + [("w", [(15, 9), (23, 9)]), ("w", [(41, 9), (49, 9)])],
    "Barbell Squat with Narrow Stance": [                # front view, knees together
        FLOOR,
        ("w", [(12, 27), (52, 27)]), ("w", [(10, 21), (10, 33)]), ("w", [(54, 21), (54, 33)]),
        ("h", (32, 20)),
        ("b", [(19, 27), (21, 35), (27, 30), (37, 30), (43, 35), (45, 27)]),
        ("b", [(32, 29), (32, 44)]),
        ("b", [(32, 44), (25, 51), (29, 59)]), ("b", [(32, 44), (39, 51), (35, 59)]),
    ],
    "Smith Machine Shoulder Press": SMITH_RAILS + [("e", [(22, 48), (42, 48)]), ("e", [(32, 48), (32, 60)])]
        + _MILITARY[1:6]
        + [("b", [(32, 26), (32, 45), (24, 49), (24, 58)]), ("b", [(32, 45), (40, 49), (40, 58)])],
    "EZ Bar Close Grip Curl": moved(_EZ_CURL, {
        3: ("b", [(27, 21), (26, 34), (28, 25)]), 4: ("b", [(37, 21), (38, 34), (36, 25)]),
        5: ("p", "M17 25 H22 L25 22 L29 27 L32 25 L35 22 L39 27 L42 25 H47", "w"),
        6: ("w", [(15, 19), (15, 31)]), 7: ("w", [(49, 19), (49, 31)]),
    }),
    "Dumbbell Bench Press (Palms in)": ICONS["Dumbbell Bench Press"][:6] + dumbbell(20, 18, horizontal=False),
    "Cable One-Arm Seated Row": ICONS["Cable Seated Row"] + [
        ("b", [(19, 26), (13, 33), (21, 40)]),           # the free hand on the hip
        ("w", [(26, 34), (26, 40)]),
    ],
    "Machine Bench Press": [("e", [(58, 4), (58, 46)]), ("e", [(58, 12), (23, 24)])]
        + _BENCH[:6] + [("w", [(17, 24), (23, 24)])],
    "Dumbbell Prone Deltoid Raise": [                    # face down on an incline bench
        FLOOR, ("e", [(20, 28), (42, 50)]), ("e", [(36, 44), (36, 60)]),
        ("h", (15, 22)),
        ("b", [(20, 27), (38, 44), (47, 50), (54, 59)]),
        ("b", [(21, 28), (10, 17)]),
        *dumbbell(8, 15, horizontal=False),
    ],
    "Smith Machine Bulgarian Split Squat": SMITH_RAILS + ICONS["Barbell Bulgarian Split Squat"],
    "Elevated Push-Up": [                                # hands on a low box
        FLOOR, ("e", [(12, 60), (12, 50), (28, 50), (28, 60)]),
        ("h", (13, 35)),
        ("b", [(20, 50), (20.5, 44.5), (21, 39)]),
        ("b", [(21, 39), (38, 47), (56, 57)]),
    ],
})

# The other end of the rep for some ICONS: the same strokes, in the same order
# and with as many points, moved. Each gets a second, animated file in
# static/icons/exercises/anim, which the exercise dropdown plays on hover.
ANIMATED = {
    "Barbell Squat": [                                   # bottom -> standing
        FLOOR,
        ("c", (34, 15, 6)),
        ("h", (25, 7)),
        ("b", [(28, 15), (29, 32), (27, 45), (24, 58)]),
        ("b", [(29, 17), (35, 22), (36, 15)]),
    ],
    "Pull-Up": [                                         # top -> dead hang
        ("e", [(8, 9), (56, 9)]),
        ("b", [(20, 9), (21, 20), (24, 31), (40, 31), (43, 20), (44, 9)]),
        ("h", (32, 23)),
        ("b", [(32, 30), (32, 46)]),
        ("b", [(32, 46), (29, 54), (31, 61)]), ("b", [(32, 46), (35, 54), (33, 61)]),
    ],
    "Push-Up": [                                         # arms straight -> chest down
        FLOOR,
        ("b", [(20, 58), (29, 53), (22, 51)]),
        ("b", [(22, 51), (38, 54), (56, 57)]),
        ("h", (14, 48)),
    ],
    "Cable Rope Face Pull": [                            # pulled in -> arms out
        FLOOR, ("e", [(56, 4), (56, 60)]), ("e", [(56, 20), (48, 20)]),
        ("h", (29, 13)),
        ("b", [(28, 21), (28, 39), (26, 49), (27, 58)]), ("b", [(28, 39), (32, 49), (33, 58)]),
        ("b", [(28, 22), (38, 21), (48, 20)]),
    ],
    "Dumbbell Lateral Raise": [                          # raised -> arms down
        FLOOR,
        ("h", (32, 12)),
        ("b", [(22, 34), (26, 21), (38, 21), (42, 34)]),
        ("b", [(32, 21), (32, 40), (27, 58)]), ("b", [(32, 40), (37, 58)]),
        *dumbbell(21, 37), *dumbbell(43, 37),
    ],
    # The rest name only what moves - see moved(). A hold shows the way into
    # it, or its harder version (Tuck Front Lever opens out to a full lever).
    "Plank": moved(ICONS["Plank"], {3: ("b", [(19, 47), (37, 44), (56, 57)])}),     # hip lift
    "Tuck Front Lever": moved(ICONS["Tuck Front Lever"], {3: ("b", [(22, 28), (37, 29), (47, 29), (57, 29)])}),
    "Dip": moved(ICONS["Dip"], {                         # top -> bottom
        4: ("h", (32, 22)),
        5: ("b", [(14, 34), (16, 24), (26, 31), (38, 31), (48, 24), (50, 34)]),
        6: ("b", [(32, 31), (32, 46), (28, 53), (35, 58)]),
        7: ("b", [(32, 46), (36, 53), (29, 58)]),
    }),
    "Front Lever Raise": moved(ICONS["Front Lever Raise"], {   # lever -> hang
        1: ("b", [(24, 8), (23, 26)]),
        2: ("h", (18, 21)),
        3: ("b", [(23, 26), (24, 43), (25, 60)]),
    }),
    "Dumbbell Bench Press": moved(ICONS["Dumbbell Bench Press"], {
        5: ("b", [(20, 41), (28, 45), (22, 34)]), 6: dumbbell(22, 31),
    }),
    "Dumbbell Incline Bench Press": moved(ICONS["Dumbbell Incline Bench Press"], {
        4: ("b", [(23, 28), (31, 31), (27, 21)]), 5: dumbbell(27, 18),
    }),
    "Barbell Stiff-Leg Deadlift": moved(ICONS["Barbell Stiff-Leg Deadlift"], {   # -> standing
        1: ("h", (30, 12)),
        2: ("b", [(31, 20), (33, 36), (32, 47), (33, 58)]),
        3: ("b", [(31, 21), (32, 35)]),
        4: ("c", (32, 39, 6.5)),
    }),
    "Machine Calf Raise": moved(ICONS["Machine Calf Raise"], {    # -> on the toes
        0: ("e", [(22, 12), (42, 12)]),
        2: ("h", (32, 5)),
        3: ("b", [(32, 12), (32, 29), (32, 38), (33, 46), (36, 53)]),
        4: ("b", [(26, 12), (25, 19)]),
    }),
    "Parallel Bar Leg Raise": moved(ICONS["Parallel Bar Leg Raise"], {
        4: ("b", [(25, 15), (25, 34), (25, 47), (25, 60)]),
    }),
    "Machine Lateral Shoulder Raise": moved(ICONS["Machine Lateral Shoulder Raise"], {
        3: ("b", [(22, 34), (26, 21), (38, 21), (42, 34)]),
        4: ("e", [(20, 22), (18, 31)]), 5: ("e", [(44, 22), (46, 31)]),
    }),
    "Machine Seated Leg Curl": moved(ICONS["Machine Seated Leg Curl"], {   # -> leg out
        3: ("b", [(18, 21), (22, 40), (38, 40), (51, 47)]),
        5: ("c", (52, 51, 3.5)),
    }),
    "Hack Squat": moved(ICONS["Hack Squat"], {           # bottom -> up
        2: ("h", (44, 8)),
        3: ("b", [(43, 16), (37, 38), (20, 44), (23, 58)]),
        4: ("b", [(43, 17), (37, 23), (42, 16)]),
    }),
    "EZ Bar Curl": moved(ICONS["EZ Bar Curl"], {         # curled -> arms down
        3: ("b", [(27, 21), (25, 32), (24, 43)]), 4: ("b", [(37, 21), (39, 32), (40, 43)]),
        5: ("p", "M14 43 H19 L23 40 L28 45 L32 43 L36 40 L41 45 L45 43 H50", "w"),
        6: ("w", [(12, 37), (12, 49)]), 7: ("w", [(52, 37), (52, 49)]),
    }),
    "Cable Seated Row": moved(ICONS["Cable Seated Row"], {    # pulled -> reaching
        2: ("e", [(57, 46), (44, 38)]),
        4: ("h", (24, 16)),
        5: ("b", [(22, 24), (20, 45), (35, 37), (48, 46)]),
        6: ("b", [(22, 26), (33, 32), (44, 38)]),
    }),
    "Machine Seated Row": moved(ICONS["Machine Seated Row"], {
        7: ("b", [(20, 23), (30, 26), (40, 30)]),
    }),
    "Barbell Bulgarian Split Squat": moved(ICONS["Barbell Bulgarian Split Squat"], {
        3: ("c", (36, 14, 6)),
        4: ("h", (25, 6)),
        5: ("b", [(27, 14), (29, 33), (22, 45), (20, 58)]),
        6: ("b", [(28, 16), (33, 20), (35, 14)]),
        7: ("b", [(29, 33), (34, 49), (44, 44)]),
    }),
    "Cable Tricep Extension": moved(ICONS["Cable Tricep Extension"], {     # -> hands up
        2: ("e", [(52, 8), (42, 24)]),
        4: ("b", [(30, 20), (31, 32), (42, 24)]),
    }),
    "Machine Fly": moved(ICONS["Machine Fly"], {         # open -> closed
        2: ("e", [(20, 8), (18, 28)]), 3: ("e", [(44, 8), (46, 28)]),
        5: ("b", [(24, 9), (21, 22), (26, 21), (38, 21), (43, 22), (40, 9)]),
    }),
    "Cable Crunch": moved(ICONS["Cable Crunch"], {       # crunched -> upright
        2: ("e", [(56, 8), (39, 22)]),
        3: ("p", "M31 42 Q31 33 34 25", "b"),
        4: ("h", (37, 19)),
    }),
    "Explosive Pull-Up": moved(ICONS["Explosive Pull-Up"], {
        1: ("h", (32, 26)),
        2: ("b", [(20, 22), (22, 27), (26, 32), (38, 32), (42, 27), (44, 22)]),
        3: ("b", [(32, 32), (32, 47), (30, 59)]),
        4: ("b", [(32, 47), (34, 59)]),
    }),
    "Decline Push-Up (Handles)": moved(ICONS["Decline Push-Up (Handles)"], {
        4: ("h", (14, 49)),
        5: ("b", [(21, 55), (28, 53), (22, 50)]),
        6: ("b", [(21, 50), (36, 42), (50, 35)]),
    }),
    "Bench Push-Up": moved(ICONS["Bench Push-Up"], {
        3: ("h", (14, 29)),
        4: ("b", [(18, 38), (26, 38), (21, 33)]),
        5: ("b", [(21, 33), (38, 45), (56, 57)]),
    }),
    "Barbell Bench Press": moved(ICONS["Barbell Bench Press"], {
        5: ("b", [(20, 41), (28, 45), (22, 34)]), 6: ("c", (22, 28, 7)),
    }),
    "Barbell Bent-Over Row": moved(ICONS["Barbell Bent-Over Row"], {
        3: ("b", [(19, 33), (20, 41), (20, 48)]), 4: ("c", (20, 52, 6)),
    }),
    "Barbell Military Press": moved(ICONS["Barbell Military Press"], {    # -> bar at the chin
        1: ("w", [(10, 21), (54, 21)]), 2: ("w", [(10, 15), (10, 27)]), 3: ("w", [(54, 15), (54, 27)]),
        5: ("b", [(21, 21), (20, 32), (27, 26), (37, 26), (44, 32), (43, 21)]),
    }),
    "Dumbbell Shoulder Press": moved(ICONS["Dumbbell Shoulder Press"], {
        3: ("b", [(17, 20), (16, 31), (27, 26), (37, 26), (48, 31), (47, 20)]),
        6: dumbbell(17, 17), 9: dumbbell(47, 17),
    }),
    "Barbell Upright Row": moved(ICONS["Barbell Upright Row"], {     # -> bar at the hips
        2: ("b", [(29, 43), (27, 32), (27, 20), (37, 20), (37, 32), (35, 43)]),
        3: ("w", [(14, 43), (50, 43)]), 4: ("w", [(12, 37), (12, 49)]), 5: ("w", [(52, 37), (52, 49)]),
    }),
    "Dumbbell Bicep Curl": moved(ICONS["Dumbbell Bicep Curl"], {     # the arms swap
        2: ("b", [(20, 24), (24, 34), (27, 21), (37, 21), (40, 34), (41, 44)]),
        3: dumbbell(20, 21), 6: dumbbell(41, 47),
    }),
    "Dumbbell Preacher Curl": moved(ICONS["Dumbbell Preacher Curl"], {
        5: ("b", [(21, 24), (35, 39), (45, 49)]), 6: dumbbell(46, 52, horizontal=False),
    }),
    "EZ Bar Tricep Extension": moved(ICONS["EZ Bar Tricep Extension"], {   # -> arms up
        5: ("b", [(21, 41), (22, 24), (23, 13)]), 6: ("c", (23, 9, 5)),
    }),
    "Machine Leg Extension": moved(ICONS["Machine Leg Extension"], {     # -> knee bent
        3: ("b", [(18, 21), (22, 40), (38, 40), (33, 55)]),
        5: ("c", (37, 53, 3.5)),
    }),
    "Machine Leg Curl (Prone)": moved(ICONS["Machine Leg Curl (Prone)"], {   # -> leg straight
        4: ("b", [(15, 42), (34, 42), (47, 42), (59, 42)]),
        6: ("c", (58, 38, 3.5)),
    }),
    "Machine Leg Press": moved(ICONS["Machine Leg Press"], {     # -> legs out
        2: ("e", [(47, 24), (61, 42)]),
        5: ("b", [(13, 30), (24, 49), (38, 37), (52, 32)]),
    }),
    "Machine Lat Pulldown": moved(ICONS["Machine Lat Pulldown"], {   # pulled -> arms up
        0: ("e", [(32, 2), (32, 5)]),
        3: ("w", [(8, 5), (56, 5)]),
        5: ("b", [(14, 5), (20, 15), (27, 25), (37, 25), (44, 15), (50, 5)]),
    }),
    "Dumbbell One-Arm Row": moved(ICONS["Dumbbell One-Arm Row"], {   # -> arm hanging
        8: ("b", [(22, 31), (24, 40), (25, 50)]), 9: dumbbell(25, 53),
    }),
    "Bench Crunch": moved(ICONS["Bench Crunch"], {       # up -> lying
        1: ("p", "M34 56 Q24 57 15 56", "b"),
        2: ("h", (8, 54)),
        4: ("b", [(16, 55), (22, 51)]),
    }),
    "Leg Raise": moved(ICONS["Leg Raise"], {
        2: ("b", [(16, 57), (34, 57), (60, 53)]),
    }),
    "Hanging Leg Raise": moved(ICONS["Hanging Leg Raise"], {
        3: ("b", [(30, 20), (30, 38), (31, 50), (32, 61)]),
    }),
    "Ab Roll": moved(ICONS["Ab Roll"], {                 # out -> rolled in
        1: ("c", (28, 55, 4.5)),
        2: ("h", (28, 31)),
        3: ("b", [(28, 52), (32, 38)]),
        4: ("b", [(32, 38), (40, 46), (42, 57), (56, 57)]),
    }),
    "Dumbbell Lunge": moved(ICONS["Dumbbell Lunge"], {   # bottom -> up
        1: ("h", (30, 5)),
        2: ("b", [(30, 12), (32, 31), (24, 45), (20, 58)]),
        3: ("b", [(32, 31), (42, 45), (50, 58)]),
        4: ("b", [(30, 14), (31, 28)]),
        5: dumbbell(31, 32, horizontal=False),
    }),
    "Machine Hip Adduction": moved(ICONS["Machine Hip Adduction"], {     # open -> closed
        6: ("b", [(32, 32), (26, 42), (26, 56)]), 7: ("b", [(32, 32), (38, 42), (38, 56)]),
        8: ("e", [(20, 43), (20, 56)]), 9: ("e", [(44, 43), (44, 56)]),
    }),
    "Machine Hip Abduction": moved(ICONS["Machine Hip Abduction"], {     # open -> closed
        6: ("b", [(32, 32), (24, 42), (23, 56)]), 7: ("b", [(32, 32), (40, 42), (41, 56)]),
        8: ("e", [(28, 43), (27, 56)]), 9: ("e", [(36, 43), (37, 56)]),
    }),
    "Machine Reverse Fly": moved(ICONS["Machine Reverse Fly"], {     # open -> in front
        2: ("e", [(27, 19), (27, 31)]), 3: ("e", [(37, 19), (37, 31)]),
        5: ("b", [(27, 25), (26, 21), (38, 21), (37, 25)]),
    }),
    "Muscle-Up": moved(ICONS["Muscle-Up"], {             # support -> coming over the bar
        1: ("h", (32, 23)),
        2: ("b", [(22, 32), (19, 25), (26, 30), (38, 30), (45, 25), (42, 32)]),
        3: ("b", [(32, 30), (32, 47), (30, 55), (31, 61)]),
        4: ("b", [(32, 47), (34, 55), (33, 61)]),
    }),
}


# The third batch's other ends - see the third batch in ICONS.
ANIMATED.update({
    "Cable Lat Pulldown (Wide Grip)": moved(ICONS["Cable Lat Pulldown (Wide Grip)"], {
        0: ("e", [(32, 2), (32, 5)]), 3: ("w", [(4, 5), (60, 5)]),
        5: ("b", [(8, 5), (16, 15), (27, 25), (37, 25), (48, 15), (56, 5)]),
    }),
    "Cable Grip Lat Pulldown (Narrow Grip)": moved(ICONS["Cable Grip Lat Pulldown (Narrow Grip)"], {
        0: ("e", [(32, 2), (32, 5)]), 3: ("w", [(21, 5), (43, 5)]),
        5: ("b", [(24, 5), (23, 15), (27, 25), (37, 25), (41, 15), (40, 5)]),
    }),
    "Cable Front Lat Pulldown (Close Grip)": moved(ICONS["Cable Front Lat Pulldown (Close Grip)"], {
        0: ("e", [(32, 2), (32, 3)]), 3: ("w", [(28, 9), (32, 3), (36, 9)]),
        5: ("b", [(29, 9), (25, 17), (27, 25), (37, 25), (39, 17), (35, 9)]),
    }),
    "Machine One-Arm Pulldown": moved(ICONS["Machine One-Arm Pulldown"], {
        0: ("e", [(46, 2), (46, 4)]), 3: ("w", [(43, 4), (49, 4)]),
        5: ("b", [(23, 45), (21, 35), (27, 25), (37, 25), (43, 14), (46, 4)]),
    }),
    "Cable Bicep Curl": moved(ICONS["Cable Bicep Curl"], {          # -> arms down
        2: ("e", [(32, 57), (32, 43)]),
        5: ("b", [(27, 21), (25, 32), (24, 43)]), 6: ("b", [(37, 21), (39, 32), (40, 43)]),
        7: ("w", [(17, 43), (47, 43)]),
    }),
    "Dumbbell Hammer Curl": moved(ICONS["Dumbbell Hammer Curl"], {  # the arms swap
        2: ("b", [(20, 24), (24, 34), (27, 21), (37, 21), (40, 34), (41, 44)]),
        3: dumbbell(20, 22, horizontal=False), 6: dumbbell(41, 48, horizontal=False),
    }),
    "Dumbbell Seated Bicep Curl": moved(ICONS["Dumbbell Seated Bicep Curl"], {
        3: ("b", [(20, 24), (23, 33), (27, 21), (37, 21), (42, 32), (46, 40)]),
        4: dumbbell(20, 21), 7: dumbbell(46, 43),
    }),
    "Weighted Tricep Dip": ANIMATED["Dip"] + [("e", [(32, 46), (32, 53)]), ("c", (32, 57, 4))],
    "Machine Dip": [("e", [(24, 56), (40, 56)]), ("e", [(32, 56), (32, 60)])] + ANIMATED["Dip"],
    "Machine Seated Tricep Dip": moved(ICONS["Machine Seated Tricep Dip"], {   # -> handles up
        5: ("w", [(30, 30), (42, 30)]), 6: ("b", [(33, 21), (42, 26), (36, 30)]),
    }),
    "Barbell Incline Bench Press": _INCLINE[:4] + [("b", [(23, 28), (31, 31), (27, 21)]), ("c", (27, 17, 6))],
    "Machine Incline Chest Press": moved(ICONS["Machine Incline Chest Press"], {
        3: ("e", [(4, 6), (27, 20)]), 6: ("b", [(23, 28), (31, 31), (27, 21)]), 7: ("w", [(24, 20), (30, 20)]),
    }),
    "Cable Side Lateral Raise": moved(ICONS["Cable Side Lateral Raise"], {     # -> arm down
        2: ("e", [(58, 56), (23, 35)]),
        4: ("b", [(22, 34), (26, 21), (38, 21), (41, 34)]),
        5: ("w", [(21, 33), (25, 37)]),
    }),
    "Dumbbell Seated Side Lateral Raise": moved(ICONS["Dumbbell Seated Side Lateral Raise"], {
        3: ("b", [(22, 34), (26, 21), (38, 21), (42, 34)]),
        6: dumbbell(21, 37), 9: dumbbell(43, 37),
    }),
    "Chin-Up": moved(ICONS["Chin-Up"], {                 # top -> dead hang
        1: ("b", [(26, 9), (25, 20), (26, 31), (38, 31), (39, 20), (38, 9)]),
        2: ("h", (32, 23)),
        3: ("b", [(32, 30), (32, 46)]),
        4: ("b", [(32, 46), (29, 54), (31, 61)]), 5: ("b", [(32, 46), (35, 54), (33, 61)]),
    }),
    "Assisted One-Arm Pull-Up": moved(ICONS["Assisted One-Arm Pull-Up"], {
        2: ("b", [(28, 9), (27, 20), (27, 31), (37, 31), (44, 27)]),
        3: ("h", (32, 23)),
        4: ("b", [(32, 30), (32, 46)]),
        5: ("b", [(32, 46), (29, 54), (31, 61)]), 6: ("b", [(32, 46), (35, 54), (33, 61)]),
    }),
    "Cable Tricep Pushdown (Rope)": moved(ICONS["Cable Tricep Pushdown (Rope)"], {     # -> hands up
        1: ("e", [(32, 2), (32, 20)]),
        3: ("b", [(29, 27), (24, 34), (27, 21), (37, 21), (40, 34), (35, 27)]),
        4: ("w", [(29, 27), (32, 20), (35, 27)]),
    }),
    "Cable Tricep Pushdown (V-Bar)": moved(ICONS["Cable Tricep Pushdown (V-Bar)"], {
        1: ("e", [(32, 2), (32, 22)]),
        3: ("b", [(30, 28), (24, 34), (27, 21), (37, 21), (40, 34), (34, 28)]),
        4: ("w", [(28, 30), (32, 22), (36, 30)]),
    }),
    "Barbell Romanian Deadlift": moved(ICONS["Barbell Romanian Deadlift"], {   # -> standing
        1: ("h", (30, 12)),
        2: ("b", [(31, 20), (33, 36), (32, 47), (33, 58)]),
        3: ("b", [(31, 21), (32, 35)]),
        4: ("c", (32, 39, 6.5)),
    }),
    "Dumbbell Stiff-Leg Deadlift": ANIMATED["Barbell Stiff-Leg Deadlift"][:4] + dumbbell(32, 38),
    "Machine Ab Crunch": moved(ICONS["Machine Ab Crunch"], {   # crunched -> upright
        3: ("e", [(48, 14), (36, 24)]),
        4: ("p", "M38 44 Q37 34 36 25", "b"),
        5: ("h", (35, 19)),
    }),
    "Oblique Crunch": moved(ICONS["Oblique Crunch"], {   # up -> lying
        1: ("p", "M34 56 Q24 57 15 56", "b"),
        2: ("h", (8, 54)),
        4: ("b", [(16, 55), (22, 51)]),
    }),
    "EZ Bar Tricep Extension (Close Grip)": _SKULL[:5] + [("b", [(21, 41), (22, 24), (23, 13)]), ("c", (23, 9, 4))],
    "Barbell JM Press": _BENCH[:5] + [("b", [(20, 41), (20, 32.5), (20, 24)]), ("c", (20, 18, 6))],
    "Hack Squat (Narrow Stance)": moved(ICONS["Hack Squat (Narrow Stance)"], {   # bottom -> up
        3: ("h", (32, 9)),
        4: ("e", [(22, 17), (42, 17)]),
        5: ("b", [(22, 23), (25, 17), (39, 17), (42, 23)]),
        6: ("b", [(32, 17), (32, 36)]),
        7: ("b", [(32, 36), (30, 47), (29, 59)]), 8: ("b", [(32, 36), (34, 47), (35, 59)]),
    }),
    "Machine Squat": moved(ICONS["Machine Squat"], {     # bottom -> up
        2: ("e", [(56, 10), (30, 15)]),
        3: ("h", (25, 7)),
        4: ("b", [(28, 15), (29, 32), (27, 45), (24, 58)]),
        5: ("b", [(29, 17), (35, 22), (36, 15)]),
    }),
    "Machine Leg Press (Narrow Stance)": moved(ICONS["Machine Leg Press (Narrow Stance)"], {   # -> legs out
        2: ("e", [(47, 24), (61, 42)]),
        5: ("b", [(13, 30), (24, 49), (40, 40), (55, 34)]),
        7: ("b", [(24, 49), (41, 42), (56, 36)]),
    }),
    "Machine Single-Leg Press": moved(ICONS["Machine Single-Leg Press"], {
        2: ("e", [(47, 24), (61, 42)]),
        5: ("b", [(13, 30), (24, 49), (38, 37), (52, 32)]),
    }),
    "Machine Shoulder Press": moved(ICONS["Machine Shoulder Press"], {     # -> handles down
        2: ("e", [(8, 34), (17, 20)]), 3: ("e", [(56, 34), (47, 20)]),
        7: ("b", [(17, 20), (16, 31), (27, 26), (37, 26), (48, 31), (47, 20)]),
        10: ("w", [(13, 20), (21, 20)]), 11: ("w", [(43, 20), (51, 20)]),
    }),
    "Barbell Squat with Narrow Stance": moved(ICONS["Barbell Squat with Narrow Stance"], {   # -> standing
        1: ("w", [(12, 19), (52, 19)]), 2: ("w", [(10, 13), (10, 25)]), 3: ("w", [(54, 13), (54, 25)]),
        4: ("h", (32, 12)),
        5: ("b", [(19, 19), (21, 27), (27, 22), (37, 22), (43, 27), (45, 19)]),
        6: ("b", [(32, 21), (32, 40)]),
        7: ("b", [(32, 40), (30, 50), (29, 59)]), 8: ("b", [(32, 40), (34, 50), (35, 59)]),
    }),
    "Smith Machine Shoulder Press": moved(ICONS["Smith Machine Shoulder Press"], {   # -> bar at the chin
        4: ("w", [(10, 21), (54, 21)]), 5: ("w", [(10, 15), (10, 27)]), 6: ("w", [(54, 15), (54, 27)]),
        8: ("b", [(21, 21), (20, 32), (27, 26), (37, 26), (44, 32), (43, 21)]),
    }),
    "EZ Bar Close Grip Curl": moved(ICONS["EZ Bar Close Grip Curl"], {     # -> arms down
        3: ("b", [(27, 21), (27, 32), (28, 43)]), 4: ("b", [(37, 21), (37, 32), (36, 43)]),
        5: ("p", "M17 43 H22 L25 40 L29 45 L32 43 L35 40 L39 45 L42 43 H47", "w"),
        6: ("w", [(15, 37), (15, 49)]), 7: ("w", [(49, 37), (49, 49)]),
    }),
    "Dumbbell Bench Press (Palms in)": ICONS["Dumbbell Bench Press"][:5]
        + [("b", [(20, 41), (28, 45), (22, 34)])] + dumbbell(22, 31, horizontal=False),
    "Cable One-Arm Seated Row": ANIMATED["Cable Seated Row"] + [
        ("b", [(23, 27), (17, 34), (22, 42)]),
        ("w", [(44, 35), (44, 41)]),
    ],
    "Machine Bench Press": moved(ICONS["Machine Bench Press"], {   # -> handles at the chest
        1: ("e", [(58, 12), (25, 34)]),
        7: ("b", [(20, 41), (28, 45), (22, 34)]),
        8: ("w", [(19, 34), (25, 34)]),
    }),
    "Dumbbell Prone Deltoid Raise": moved(ICONS["Dumbbell Prone Deltoid Raise"], {   # -> arm hanging
        5: ("b", [(21, 28), (21, 42)]), 6: dumbbell(21, 45),
    }),
    "Smith Machine Bulgarian Split Squat": SMITH_RAILS + ANIMATED["Barbell Bulgarian Split Squat"],
    "Elevated Push-Up": moved(ICONS["Elevated Push-Up"], {     # arms straight -> chest down
        2: ("h", (14, 40)),
        3: ("b", [(20, 50), (28, 47), (22, 44)]),
        4: ("b", [(22, 44), (38, 50), (56, 57)]),
    }),
})


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
                        parts=[("b", [(20, 41), (20, 32.5), (20, 24)])], anchors=[(20, 19)], cable=[(4, 58)],
                        ball=(26, 52, 8)),
    "press_incline": dict(label="Incline press", base="bench_incline", view="side",
                          parts=[("b", [(23, 28), (24, 20), (25, 12)])], anchors=[(25, 8)], cable=[(4, 58)]),
    "press_decline": dict(label="Decline press", base="bench_decline", view="side",
                          parts=[("b", [(19, 46), (19, 38), (19, 30)])], anchors=[(19, 26)], cable=[(4, 58)]),
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
                                ("h", (11, 37)), ("b", [(18, 22), (18, 29.5), (18, 37)]),
                                ("b", [(18, 37), (36, 47), (56, 57)])],
                         anchors=[(18, 22)]),
    "shrug": dict(label="Shrug", base="front_stand", view="front",
                  parts=[("b", [(26, 21), (23, 39)]), ("b", [(38, 21), (41, 39)]), ARROW_UP_L, ARROW_UP_R],
                  anchors=[(23, 42), (41, 42)], cable=[(6, 58), (58, 58)]),
    "hang": dict(label="Hang", base="none", view="front",
                 parts=[("e", [(8, 6), (56, 6)]), ("h", (32, 15)), ("b", [(26, 24), (38, 24)]),
                        ("b", [(32, 24), (32, 42)]), ("b", [(32, 42), (29, 59)]), ("b", [(32, 42), (35, 59)]),
                        ("b", [(26, 24), (25, 15), (24, 6)]), ("b", [(38, 24), (41, 39)])],
                 anchors=[]),
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
                             ("h", (36, 17)), ("b", [(42, 40), (40, 33), (38, 26)]),
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
                       parts=[FLOOR, ("h", (12, 40)), ("b", [(18, 44), (37, 51), (56, 58)]),
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
                      parts=[FLOOR, ("h", (32, 50)),
                             ("b", [(26, 59), (26, 50.5), (26, 42), (38, 42), (38, 50.5), (38, 59)]),
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

# The other end of the rep for the POSES: their parts moved (see moved()) and
# where the hands are then - the load is drawn there again by draw_load(), so
# one end pose animates every equipment variant of it. "bases" swaps a base
# body for the end pose (shrug: the shoulders go up). Every pose has one - a
# hold shows the way into it (wall squat: sliding down the wall).
def end_of(key, changes, anchors, **extra):
    return dict(parts=moved(POSES[key]["parts"], changes), anchors=anchors, **extra)


POSE_ENDS = {
    "curl": end_of("curl", {0: ("b", [(26, 21), (25, 32), (24, 43)]), 1: ("b", [(38, 21), (39, 32), (40, 43)])},
                   [(24, 44), (40, 44)]),
    "preacher": end_of("preacher", {5: ("b", [(21, 24), (35, 39), (45, 49)])}, [(46, 51)]),
    "concentration": end_of("concentration", {4: ("b", [(30, 27), (24, 41), (21, 52)])}, [(21, 54)]),
    "wrist_curl": end_of("wrist_curl", {0: ("b", [(29, 21), (27, 37), (12, 35)])}, [(9, 31)]),
    "press_bench": end_of("press_bench", {0: ("b", [(20, 41), (28, 45), (22, 34)])}, [(22, 30)]),
    "press_incline": end_of("press_incline", {0: ("b", [(23, 28), (31, 31), (27, 21)])}, [(27, 17)]),
    "press_decline": end_of("press_decline", {0: ("b", [(19, 46), (27, 48), (21, 37)])}, [(21, 33)]),
    "press_overhead": end_of("press_overhead", {0: ("b", [(26, 21), (17, 30), (18, 20)]),
                                                1: ("b", [(38, 21), (47, 30), (46, 20)])}, [(18, 18), (46, 18)]),
    "chest_press": end_of("chest_press", {0: ("b", [(29, 21), (35, 27), (22, 24)])}, [(20, 24)]),
    "fly": end_of("fly", {0: ("b", [(26, 21), (24, 28), (29, 30)]), 1: ("b", [(38, 21), (40, 28), (35, 30)])},
                  [(29, 30), (35, 30)]),
    "fly_bench": end_of("fly_bench", {0: ("b", [(20, 41), (20, 24)])}, [(20, 21)]),
    "lateral": end_of("lateral", {0: ("b", [(26, 21), (22, 35)]), 1: ("b", [(38, 21), (42, 35)])},
                      [(21, 37), (43, 37)]),
    "front_raise": end_of("front_raise", {0: ("b", [(29, 21), (27, 38)])}, [(27, 41)]),
    "rear_raise": end_of("rear_raise", {3: ("b", [(19, 33), (25, 24)])}, [(26, 22)]),
    "row_bent": end_of("row_bent", {3: ("b", [(19, 33), (20, 41), (20, 49)])}, [(20, 52)]),
    "row_seated": end_of("row_seated", {0: ("b", [(29, 21), (18, 26), (8, 30)])}, [(6, 30)]),
    "row_upright": end_of("row_upright", {0: ("b", [(29, 43), (27, 32), (26, 21)]),
                                          1: ("b", [(35, 43), (37, 32), (38, 21)])}, [(29, 43), (35, 43)]),
    "row_inverted": end_of("row_inverted", {3: ("h", (13, 26)), 4: ("b", [(18, 22), (26, 24), (20, 27)]),
                                            5: ("b", [(20, 27), (37, 41), (56, 57)])}, [(18, 22)]),
    "shrug": end_of("shrug", {0: ("b", [(26, 18), (23, 36)]), 1: ("b", [(38, 18), (41, 36)])},
                    [(23, 39), (41, 39)],
                    bases={"front_stand": moved(BASES["front_stand"], {2: ("b", [(26, 18), (38, 18)]),
                                                                        3: ("b", [(32, 18), (32, 40)])}),
                           "front_seat": moved(BASES["front_seat"], {3: ("b", [(26, 18), (38, 18)]),
                                                                     4: ("b", [(32, 18), (32, 41)])})}),
    "tricep_overhead": end_of("tricep_overhead", {5: ("b", [(30, 21), (32, 13), (34, 6)])}, [(34, 5)]),
    "tricep_overhead_seated": end_of("tricep_overhead_seated", {5: ("b", [(30, 21), (32, 13), (34, 6)])},
                                     [(34, 5)]),
    "skull": end_of("skull", {0: ("b", [(21, 41), (22, 24), (23, 12)])}, [(23, 9)]),
    "kickback": end_of("kickback", {6: ("b", [(21, 31), (30, 34), (31, 45)])}, [(31, 47)]),
    "pushdown": end_of("pushdown", {0: ("b", [(29, 21), (31, 33), (21, 26)])}, [(20, 26)]),
    "bench_dip": end_of("bench_dip", {3: ("h", (35, 26)), 4: ("b", [(42, 40), (46, 31), (37, 33)]),
                                      5: ("b", [(37, 33), (35, 51), (20, 50), (8, 58)])}, [(29, 47)]),
    "pulldown": end_of("pulldown", {0: ("b", [(26, 21), (19, 13), (15, 5)]),
                                    1: ("b", [(38, 21), (45, 13), (49, 5)])}, [(15, 5), (49, 5)]),
    "pullover": end_of("pullover", {0: ("b", [(19, 41), (20, 24)])}, [(20, 21)]),
    "squat": end_of("squat", {1: ("h", (25, 7)), 2: ("b", [(28, 15), (29, 32), (27, 45), (24, 58)]),
                              3: ("b", [(29, 17), (35, 22), (36, 15)])}, [(34, 15)]),
    "squat_goblet": end_of("squat_goblet", {1: ("h", (25, 7)), 2: ("b", [(28, 15), (29, 32), (27, 45), (24, 58)]),
                                            3: ("b", [(29, 17), (22, 26), (20, 21)])}, [(19, 21)]),
    "squat_overhead": end_of("squat_overhead", {1: ("h", (24, 11)),
                                                2: ("b", [(29, 19), (32, 37), (22, 45), (24, 58)]),
                                                3: ("b", [(29, 19), (31, 5)])}, [(31, 4)]),
    "lunge": end_of("lunge", {1: ("h", (30, 5)), 2: ("b", [(30, 12), (32, 31), (24, 45), (20, 58)]),
                              3: ("b", [(32, 31), (42, 45), (50, 58)]), 4: ("b", [(30, 14), (31, 28)])},
                    [(31, 32)], bar=[(34, 13)]),
    "stepup": end_of("stepup", {2: ("h", (22, 6)), 3: ("b", [(23, 13), (24, 31), (18, 38), (19, 46)]),
                                4: ("b", [(24, 31), (30, 42), (32, 52)]), 5: ("b", [(23, 15), (25, 28)])},
                     [(25, 32)], bar=[(27, 13)]),
    "sissy": end_of("sissy", {1: ("h", (29, 10)), 2: ("b", [(28, 18), (26, 36), (22, 47), (26, 59)]),
                              3: ("b", [(28, 20), (20, 24)])}, [(18, 24)]),
    "deadlift": end_of("deadlift", {1: ("h", (30, 12)), 2: ("b", [(31, 20), (33, 36), (32, 47), (33, 58)]),
                                    3: ("b", [(31, 21), (32, 35)])}, [(32, 39)]),
    "good_morning": end_of("good_morning", {1: ("h", (30, 12)),
                                            2: ("b", [(31, 20), (33, 36), (32, 47), (33, 58)]),
                                            3: ("b", [(31, 21), (35, 17)])}, [(35, 16)]),
    "calf": end_of("calf", {1: ("h", (32, 5)), 2: ("b", [(32, 12), (32, 29), (32, 38), (33, 46), (36, 53)]),
                            3: ("b", [(32, 14), (31, 29)])}, [(31, 32)], bar=[(36, 11)]),
    "calf_seated": end_of("calf_seated", {3: ("b", [(29, 19), (30, 41), (16, 37), (15, 49), (10, 56)]),
                                          4: ("b", [(29, 21), (22, 32), (17, 34)])}, [(18, 32)]),
    "leg_curl_stand": end_of("leg_curl_stand", {5: ("b", [(30, 40), (32, 50), (35, 58)])}, [(36, 57)]),
    "bridge": end_of("bridge", {4: ("b", [(16, 38), (34, 47), (46, 39), (48, 59)])}, [(34, 43)]),
    "glute_kick": end_of("glute_kick", {3: ("b", [(36, 42), (38, 52), (48, 54)])}, [(49, 54)]),
    "reverse_crunch": end_of("reverse_crunch", {2: ("b", [(15, 57), (32, 56), (42, 44), (54, 50)])}, [(52, 48)]),
    "situp": end_of("situp", {1: ("h", (9, 54)), 2: ("b", [(16, 57), (34, 56), (44, 42), (55, 57)]),
                              3: ("b", [(17, 56), (24, 52)])}, [(23, 51)]),
    "twist": end_of("twist", {3: ("b", [(25, 40), (18, 46)])}, [(17, 48)]),
    "vup": end_of("vup", {1: ("h", (6, 53)), 2: ("b", [(13, 56), (32, 57), (56, 56)]),
                          3: ("b", [(14, 55), (7, 46)])}, [(6, 45)]),
    "woodchop": end_of("woodchop", {0: ("b", [(26, 21), (41, 36)]), 1: ("b", [(38, 21), (43, 37)])}, [(43, 39)]),
    "mountain": end_of("mountain", {4: ("b", [(36, 47), (46, 53), (54, 58)])}, []),
    "side_bend": end_of("side_bend", {1: ("h", (36, 12)), 2: ("b", [(32, 40), (34, 21)]),
                                      3: ("b", [(28, 21), (40, 21)]), 6: ("b", [(28, 21), (26, 39)]),
                                      7: ("b", [(40, 21), (45, 30), (39, 36)])}, [(26, 42)]),
    "back_ext": end_of("back_ext", {3: ("h", (19, 58)), 4: ("b", [(24, 54), (34, 40), (54, 57)]),
                                    5: ("b", [(25, 53), (31, 51)])}, [(29, 51)]),
    "clean": end_of("clean", {0: ("b", [(29, 21), (29, 31), (28, 40)])}, [(28, 42)]),
    "overhead_lift": end_of("overhead_lift", {5: ("b", [(29, 21), (24, 17)])}, [(23, 16)]),
    "swing": end_of("swing", {1: ("h", (27, 10)), 2: ("b", [(29, 18), (34, 38), (32, 48), (33, 59)]),
                              3: ("b", [(29, 19), (12, 18)])}, [(10, 20)]),
    "throw": end_of("throw", {0: ("b", [(26, 21), (25, 32), (30, 40)]), 1: ("b", [(38, 21), (39, 32), (34, 40)])},
                    [(32, 42)]),
    "jump": end_of("jump", {2: ("h", (19, 26)), 3: ("b", [(22, 33), (30, 46), (18, 50), (22, 59)]),
                            4: ("b", [(23, 35), (33, 44)])}, [(34, 44)]),
    "rotation": end_of("rotation", {0: ("b", [(26, 21), (42, 30)]), 1: ("b", [(38, 21), (46, 28)])}, [(46, 31)]),
    "circles": end_of("circles", {0: ("b", [(26, 21), (13, 15)]), 1: ("b", [(38, 21), (51, 15)])},
                      [(11, 14), (53, 14)]),
    "side_plank": end_of("side_plank", {2: ("b", [(18, 44), (37, 55), (56, 58)])}, [(22, 26)]),   # hip dip
    "wall_squat": end_of("wall_squat", {2: ("h", (44, 6)), 3: ("b", [(45, 14), (45, 34), (32, 44), (27, 59)]),
                                        4: ("b", [(45, 16), (31, 18)])}, [(29, 18)]),
    "handstand": end_of("handstand", {1: ("h", (32, 56)),                  # -> lowered: the push-up
                                      2: ("b", [(26, 59), (19, 52), (27, 50), (37, 50), (45, 52), (38, 59)]),
                                      3: ("b", [(32, 50), (32, 30)]), 4: ("b", [(32, 30), (28, 12)]),
                                      5: ("b", [(32, 30), (36, 12)])}, []),
    "hang": end_of("hang", {1: ("h", (32, 12)), 2: ("b", [(26, 20), (38, 20)]),   # -> active hang
                            3: ("b", [(32, 20), (32, 38)]), 4: ("b", [(32, 38), (29, 55)]),
                            5: ("b", [(32, 38), (35, 55)]), 6: ("b", [(26, 20), (23, 13), (24, 6)]),
                            7: ("b", [(38, 20), (41, 35)])}, []),
    "carry": end_of("carry", {4: ("b", [(32, 40), (39, 59)]), 5: ("b", [(32, 40), (24, 58)])},   # walking
                    [(22, 42), (42, 42)]),
    "neck": end_of("neck", {1: ("h", (21, 16)), 5: ("b", [(29, 21), (17, 24), (18, 15)])}, [(20, 10)]),
    # stretches and yoga: easing into the position
    "stretch_side": end_of("stretch_side", {1: ("h", (42, 15)), 2: ("b", [(32, 40), (39, 23)]),
                                            3: ("b", [(33, 22), (46, 24)]),
                                            6: ("b", [(33, 22), (32, 7), (45, 4)]),
                                            7: ("b", [(46, 24), (48, 34), (41, 38)])}, []),
    "stretch_fold": end_of("stretch_fold", {1: ("h", (14, 40)), 4: ("b", [(32, 38), (20, 40)]),
                                            5: ("b", [(21, 41), (25, 52)])}, []),
    "stretch_quad": end_of("stretch_quad", {4: ("b", [(30, 40), (33, 53), (38, 36)]),
                                            5: ("b", [(29, 21), (35, 31), (38, 36)])}, []),
    "stretch_arm": end_of("stretch_arm", {0: ("b", [(26, 21), (45, 22)]), 1: ("b", [(38, 21), (41, 29), (36, 23)])},
                          []),
    "stretch_lying": end_of("stretch_lying", {3: ("b", [(34, 57), (24, 44), (32, 38)]),
                                              4: ("b", [(16, 56), (25, 45)])}, []),
    "stretch_seated": end_of("stretch_seated", {1: ("h", (37, 44)), 3: ("b", [(14, 57), (31, 48)]),
                                                4: ("b", [(31, 49), (46, 56)])}, []),
    "cobra": end_of("cobra", {1: ("h", (7, 53)), 2: ("b", [(56, 58), (34, 57), (14, 56)]),
                              3: ("b", [(14, 55), (20, 58)])}, []),
    "child": end_of("child", {1: ("h", (14, 52)), 2: ("b", [(46, 59), (34, 58), (42, 50), (21, 52)]),
                              3: ("b", [(20, 54), (4, 58)])}, []),
    "dog": end_of("dog", {1: ("h", (18, 50)), 2: ("b", [(12, 59), (34, 32), (54, 59)])}, []),
    "warrior": end_of("warrior", {1: ("h", (32, 16)), 2: ("b", [(32, 24), (32, 44)]),
                                  3: ("b", [(32, 44), (20, 48), (18, 59)]), 4: ("b", [(32, 44), (46, 54), (54, 59)]),
                                  5: ("b", [(32, 26), (30, 8)])}, []),
    "stork": end_of("stork", {5: ("b", [(32, 40), (42, 44), (35, 49)]),
                              6: ("b", [(26, 21), (12, 18)]), 7: ("b", [(38, 21), (52, 18)])}, []),
}

# ---- round 3: the core, leg raise, yoga / stretch, Olympic lift and rear
# delt groups, which shared one or two drawings each - one pose per movement.
# The holds move too: a slow ease deeper into the position and back.
def shifted(strokes, dx=0, dy=0):
    """strokes moved by (dx, dy) - a pose put up on a bench."""
    out = []
    for s in strokes:
        if s[0] in ("b", "e", "w"):
            out.append((s[0], [(x + dx, y + dy) for x, y in s[1]]))
        elif s[0] == "h":
            out.append(("h", (s[1][0] + dx, s[1][1] + dy)))
        else:
            out.append(s)
    return out


LIE_ARMS = ("b", [(16, 58), (28, 59)])                   # lying, arms along the floor
_PULL_IN = [("h", (47, 32)), ("b", [(44, 39), (34, 54), (24, 42), (14, 50)]), ("b", [(44, 40), (46, 50), (42, 56)])]
_PULL_IN_END = {0: ("h", (51, 36)), 1: ("b", [(47, 42), (34, 54), (22, 50), (8, 48)]),
                2: ("b", [(47, 43), (47, 51), (42, 56)])}
BENCH_LOW = [("e", [(26, 47), (56, 47)]), ("e", [(30, 47), (30, 60)]), ("e", [(52, 47), (52, 60)])]

POSES.update({
    # core
    "crunch_floor": dict(label="Crunch", base="none", view="side",
                         parts=[FLOOR, ("h", (14, 46)), ("b", [(19, 51), (34, 57), (44, 44), (54, 58)]),
                                ("b", [(20, 51), (28, 47)])],
                         anchors=[(28, 46)], cable=[(4, 50)]),
    "crunch_cross": dict(label="Bicycle / cross-body crunch", base="none", view="side",
                         parts=[FLOOR, ("h", (14, 45)), ("b", [(19, 50), (34, 56)]),
                                ("b", [(34, 56), (30, 42), (40, 38)]), ("b", [(34, 56), (46, 50), (58, 48)]),
                                ("b", [(20, 50), (27, 44)])],
                         anchors=[(28, 43)], cable=[(4, 50)]),
    "decline_crunch": dict(label="Decline crunch", base="none", view="side",
                           parts=[("e", [(10, 50), (46, 38)]), ("e", [(40, 40), (40, 60)]), ("e", [(50, 31), (56, 36)]),
                                  ("h", (22, 24)), ("b", [(26, 31), (36, 40), (44, 31), (52, 35)]),
                                  ("b", [(27, 32), (33, 29)])],
                           anchors=[(33, 28)]),
    "ball_crunch": dict(label="Stability ball crunch", base="none", view="side",
                        parts=[FLOOR, ("h", (17, 31)), ("b", [(22, 37), (36, 42), (48, 42), (48, 59)]),
                               ("b", [(23, 38), (29, 34)])],
                        anchors=[(29, 33)], ball=(30, 50, 9)),
    "ball_tuck": dict(label="Stability ball knee tuck", base="none", view="side",
                      parts=[FLOOR, ("h", (9, 37)), ("b", [(15, 41), (34, 36), (40, 44), (50, 43)]),
                             ("b", [(15, 41), (14, 59)])],
                      anchors=[(46, 44)], ball=(47, 51, 8)),
    "leg_pull_in": dict(label="Seated leg pull-in", base="none", view="side",
                        parts=[FLOOR] + _PULL_IN, anchors=[]),
    "leg_pull_in_bench": dict(label="Bench leg pull-in", base="none", view="side",
                              parts=[FLOOR] + BENCH_LOW + shifted(_PULL_IN, dy=-9), anchors=[]),
    "leg_slide": dict(label="Leg slide", base="none", view="side",
                      parts=[FLOOR, ("h", (8, 54)), ("b", [(15, 57), (34, 57), (42, 44), (50, 58)]),
                             ("b", [(34, 57), (46, 57), (58, 57)]), LIE_ARMS],
                      anchors=[]),
    "heel_touch": dict(label="Heel touch", base="none", view="side",
                       parts=[FLOOR, ("h", (13, 48)), ("b", [(18, 52), (34, 57), (44, 44), (50, 58)]),
                              ("b", [(19, 53), (30, 56), (42, 58)])],
                       anchors=[]),
    "dragon_flag": dict(label="Dragon flag", base="none", view="side",
                        parts=[FLOOR, ("e", [(6, 46), (36, 46)]), ("e", [(10, 46), (10, 60)]), ("e", [(32, 46), (32, 60)]),
                               ("h", (12, 39)), ("b", [(17, 43), (34, 26), (52, 9)]), ("b", [(16, 43), (7, 40), (6, 45)])],
                        anchors=[]),
    "hip_roll": dict(label="Lying hip roll (from above)", base="none", view="front",
                     parts=[("h", (32, 8)), ("b", [(32, 15), (32, 38)]), ("b", [(6, 20), (20, 17), (44, 17), (58, 20)]),
                            ("b", [(32, 38), (29, 48), (31, 57)]), ("b", [(32, 38), (35, 48), (33, 57)])],
                     anchors=[]),
    "lying_twist": dict(label="Lying twist (from above)", base="none", view="front",
                        parts=[("h", (32, 8)), ("b", [(32, 15), (32, 38)]), ("b", [(6, 20), (20, 17), (44, 17), (58, 20)]),
                               ("b", [(32, 38), (28, 58)]), ("b", [(32, 38), (35, 48), (36, 58)])],
                        anchors=[]),
    "side_crunch": dict(label="Side jackknife", base="none", view="side",
                        parts=[FLOOR, ("h", (12, 44)), ("b", [(16, 49), (32, 56), (56, 46)]),
                               ("b", [(17, 48), (12, 38)]), ("b", [(17, 50), (22, 58)])],
                        anchors=[]),
    "roll_down": dict(label="Roll down", base="none", view="side",
                      parts=[FLOOR, ("h", (48, 33)), ("b", [(46, 40), (40, 57), (26, 44), (16, 58)]),
                             ("b", [(46, 41), (30, 42)])],
                      anchors=[(30, 42)], ball=(50, 52, 8)),
    "salute": dict(label="Overhead reach / salute", base="front_stand", view="front",
                   parts=[("b", [(26, 21), (29, 3)]), ("b", [(38, 21), (35, 3)])], anchors=[]),
    # leg raises
    "hundreds": dict(label="Hundreds", base="none", view="side",
                     parts=[FLOOR, ("h", (12, 47)), ("b", [(17, 51), (34, 57), (56, 40)]),
                            ("b", [(18, 52), (32, 50)])],
                     anchors=[(46, 47)], ball=(49, 45, 6)),
    "flutter": dict(label="Flutter / scissor kick", base="none", view="side",
                    parts=[FLOOR, ("h", (8, 54)), ("b", [(15, 57), (34, 57)]),
                           ("b", [(34, 57), (58, 45)]), ("b", [(34, 57), (58, 54)]), LIE_ARMS],
                    anchors=[]),
    "knee_raise_lying": dict(label="Lying knee raise", base="none", view="side",
                             parts=[FLOOR, ("h", (8, 54)), ("b", [(15, 57), (34, 57), (32, 42), (44, 40)]), LIE_ARMS],
                             anchors=[(44, 39)], cable=[(60, 40)], ball=(47, 36, 6)),
    "decline_leg_raise": dict(label="Decline bench leg raise", base="none", view="side",
                              parts=[("e", [(8, 32), (50, 52)]), ("e", [(14, 35), (14, 60)]), ("e", [(44, 49), (44, 60)]),
                                     ("h", (12, 23)), ("b", [(17, 30), (34, 39), (40, 17)]),
                                     ("b", [(17, 29), (10, 26), (7, 32)])],
                              anchors=[(40, 16)], cable=[(60, 4)]),
    "leg_raise_thrust": dict(label="Leg raise with hip thrust", base="none", view="side",
                             parts=[FLOOR, ("h", (8, 54)), ("b", [(15, 57), (34, 56), (34, 30)]), LIE_ARMS],
                             anchors=[]),
    # yoga and stretches
    "boat": dict(label="Boat pose", base="none", view="side",
                 parts=[FLOOR, ("h", (19, 34)), ("b", [(22, 41), (32, 57), (50, 38)]), ("b", [(23, 42), (38, 43)])],
                 anchors=[]),
    "bow": dict(label="Bow pose", base="none", view="side",
                parts=[FLOOR, ("h", (12, 42)), ("b", [(17, 47), (34, 56), (48, 52), (42, 38)]),
                       ("b", [(18, 47), (41, 39)])],
                anchors=[]),
    "locust": dict(label="Locust pose", base="none", view="side",
                   parts=[FLOOR, ("h", (10, 48)), ("b", [(16, 52), (34, 58), (56, 52)]), ("b", [(17, 52), (30, 53)])],
                   anchors=[]),
    "camel": dict(label="Camel pose", base="none", view="side",
                  parts=[FLOOR, ("h", (45, 25)), ("b", [(46, 59), (30, 59), (32, 40), (42, 31)]),
                         ("b", [(42, 32), (46, 56)])],
                  anchors=[]),
    "hero": dict(label="Hero pose", base="none", view="side",
                 parts=[FLOOR, ("h", (38, 28)), ("b", [(40, 59), (20, 58), (38, 54), (38, 36)]),
                        ("b", [(38, 38), (28, 48), (24, 53)])],
                 anchors=[]),
    "wheel": dict(label="Wheel pose", base="none", view="side",
                  parts=[FLOOR, ("h", (17, 47)), ("b", [(14, 59), (20, 40), (36, 30), (46, 42), (50, 59)])],
                  anchors=[]),
    "fish": dict(label="Fish pose", base="none", view="side",
                 parts=[FLOOR, ("h", (10, 54)), ("b", [(15, 50), (24, 46), (34, 57), (58, 57)]),
                        ("b", [(22, 48), (24, 58)])],
                 anchors=[]),
    "all_fours": dict(label="Cat-cow / table", base="none", view="side",
                      parts=[FLOOR, ("h", (9, 40)), ("b", [(16, 42), (28, 42), (40, 42), (40, 59), (54, 59)]),
                             ("b", [(16, 42), (15, 59)])],
                      anchors=[]),
    "crow": dict(label="Crow pose", base="none", view="side",
                 parts=[FLOOR, ("h", (11, 46)), ("b", [(18, 44), (34, 34), (24, 44), (36, 50)]),
                        ("b", [(19, 45), (22, 52), (22, 59)])],
                 anchors=[]),
    "staff": dict(label="Staff pose", base="none", view="side",
                  parts=[FLOOR, ("h", (34, 30)), ("b", [(10, 58), (34, 58), (34, 38)]), ("b", [(34, 40), (38, 50), (38, 58)])],
                  anchors=[]),
    "seated_fold": dict(label="Seated forward fold", base="none", view="side",
                        parts=[FLOOR, ("h", (16, 40)), ("b", [(10, 58), (34, 58), (20, 44)]), ("b", [(21, 45), (10, 54)])],
                        anchors=[]),
    "straddle": dict(label="Straddle stretch", base="none", view="front",
                     parts=[FLOOR, ("h", (32, 22)), ("b", [(26, 31), (38, 31)]), ("b", [(32, 31), (32, 50)]),
                            ("b", [(32, 50), (6, 58)]), ("b", [(32, 50), (58, 58)]),
                            ("b", [(26, 31), (14, 50)]), ("b", [(38, 31), (50, 50)])],
                     anchors=[]),
    "triangle": dict(label="Triangle / side angle pose", base="none", view="front",
                     parts=[FLOOR, ("h", (16, 23)), ("b", [(32, 40), (20, 28)]), ("b", [(32, 40), (14, 59)]),
                            ("b", [(32, 40), (50, 59)]), ("b", [(14, 46), (22, 30), (30, 14)])],
                     anchors=[]),
    "chair_pose": dict(label="Chair pose", base="none", view="side",
                       parts=[FLOOR, ("h", (24, 17)), ("b", [(28, 24), (36, 40), (24, 46), (26, 59)]),
                              ("b", [(28, 25), (20, 6)])],
                       anchors=[]),
    "low_lunge": dict(label="Low lunge stretch", base="none", view="side",
                      parts=[FLOOR, ("h", (12, 33)), ("b", [(14, 59), (14, 45), (30, 49), (46, 58), (60, 58)]),
                             ("b", [(30, 49), (18, 37)]), ("b", [(18, 38), (18, 58)])],
                      anchors=[]),
    "calf_wall": dict(label="Wall calf stretch", base="none", view="side",
                      parts=[FLOOR, ("e", [(6, 4), (6, 60)]), ("h", (14, 19)), ("b", [(18, 24), (30, 40)]),
                             ("b", [(30, 40), (20, 48), (18, 59)]), ("b", [(30, 40), (46, 59)]),
                             ("b", [(18, 25), (6, 24)])],
                      anchors=[]),
    "hinge_hold": dict(label="Supported hinge stretch", base="none", view="side",
                       parts=[FLOOR, ("e", [(8, 34), (8, 60)]), ("h", (12, 40)), ("b", [(18, 36), (36, 38)]),
                              ("b", [(36, 38), (35, 59)]), ("b", [(36, 38), (39, 59)]), ("b", [(19, 36), (8, 34)])],
                       anchors=[]),
    "chair_fold": dict(label="Seated chair fold", base="none", view="side",
                       parts=[FLOOR, ("e", [(30, 44), (48, 44)]), ("e", [(46, 44), (46, 60)]), ("e", [(48, 44), (48, 22)]),
                              ("h", (24, 57)), ("b", [(28, 52), (40, 43), (24, 43), (24, 59)]),
                              ("b", [(29, 52), (27, 60)])],
                       anchors=[]),
    "supine_leg_up": dict(label="Lying hamstring stretch", base="none", view="side",
                          parts=[FLOOR, ("h", (8, 54)), ("b", [(15, 57), (34, 57), (58, 57)]),
                                 ("b", [(34, 57), (38, 33)]), ("b", [(16, 56), (34, 40)])],
                          anchors=[]),
    # Olympic lifts: the catch, with the way up as an arrow (the moving one
    # plays the pull from the floor instead)
    "snatch": dict(label="Snatch (squat catch)", base="none", view="side",
                   parts=[FLOOR, ("h", (25, 15)), ("b", [(30, 23), (36, 42), (20, 44), (24, 58)]),
                          ("b", [(30, 23), (32, 5)]), ("a", "M48 56 Q56 30 42 6")],
                   anchors=[(32, 4)]),
    "power_snatch": dict(label="Power snatch", base="none", view="side",
                         parts=[FLOOR, ("h", (28, 13)), ("b", [(30, 21), (34, 40), (24, 46), (26, 58)]),
                                ("b", [(30, 21), (32, 4)]), ("a", "M48 56 Q56 30 42 6")],
                         anchors=[(32, 3)]),
    "hang_snatch": dict(label="Hang snatch", base="none", view="side",
                        parts=[FLOOR, ("h", (15, 17)), ("b", [(21, 23), (33, 40), (27, 48), (29, 58)]),
                               ("b", [(21, 24), (23, 40)]), ("a", "M12 40 Q4 20 20 4")],
                        anchors=[(23, 42)]),
    "snatch_pull": dict(label="Snatch pull / high pull", base="none", view="side",
                        parts=[FLOOR, ("h", (27, 9)), ("b", [(29, 16), (31, 38), (30, 50), (34, 57)]),
                               ("b", [(29, 18), (20, 22), (26, 28)])],
                        anchors=[(26, 30)]),
    "power_jerk": dict(label="Power jerk", base="none", view="side",
                       parts=[FLOOR, ("h", (26, 13)), ("b", [(29, 21), (32, 40), (24, 47), (26, 58)]),
                              ("b", [(29, 22), (31, 4)]), ("a", "M14 26 L14 8 M11 11 L14 7 L17 11")],
                       anchors=[(31, 3)]),
    # rear delts, supported
    "rear_raise_prone": dict(label="Rear delt raise, prone on a bench", base="none", view="side",
                             parts=[FLOOR, ("e", [(16, 26), (44, 46)]), ("e", [(36, 40), (36, 60)]),
                                    ("h", (13, 21)), ("b", [(19, 27), (42, 44), (46, 59)]), ("b", [(20, 28), (19, 44)])],
                             anchors=[(19, 47)]),
    "rear_raise_seated": dict(label="Rear delt raise, seated", base="none", view="side",
                              parts=[("e", [(30, 44), (46, 44)]), ("e", [(38, 44), (38, 60)]), FLOOR,
                                     ("h", (15, 36)), ("b", [(22, 36), (40, 42), (24, 42), (24, 58)]),
                                     ("b", [(23, 37), (22, 52)])],
                              anchors=[(22, 55)]),
})

_PULL_IN_BENCH_END = {i + 4: s for i, s in
                      enumerate(shifted([_PULL_IN_END[0], _PULL_IN_END[1], _PULL_IN_END[2]], dy=-9))}
_FROM_FLOOR = {1: ("h", (12, 31)), 2: ("b", [(18, 34), (34, 40), (26, 48), (26, 58)]),
               3: ("b", [(18, 35), (20, 52)])}         # the bar at the shins, where a snatch starts

POSE_ENDS.update({
    "crunch_floor": end_of("crunch_floor", {1: ("h", (9, 53)), 2: ("b", [(15, 57), (34, 57), (44, 44), (54, 58)]),
                                            3: ("b", [(16, 56), (24, 53)])}, [(24, 52)]),
    "crunch_cross": end_of("crunch_cross", {1: ("h", (13, 47)), 3: ("b", [(34, 56), (46, 50), (58, 48)]),
                                            4: ("b", [(34, 56), (30, 42), (40, 38)]),
                                            5: ("b", [(20, 51), (27, 47)])}, [(28, 46)]),
    "decline_crunch": end_of("decline_crunch", {3: ("h", (10, 44)), 4: ("b", [(17, 46), (36, 40), (44, 31), (52, 35)]),
                                                5: ("b", [(18, 46), (25, 44)])}, [(25, 43)]),
    "ball_crunch": end_of("ball_crunch", {1: ("h", (13, 46)), 2: ("b", [(20, 45), (36, 42), (48, 42), (48, 59)]),
                                          3: ("b", [(21, 45), (28, 42)])}, [(28, 41)]),
    "ball_tuck": end_of("ball_tuck", {2: ("b", [(15, 41), (32, 42), (44, 43), (54, 45)])}, [(46, 44)]),
    "leg_pull_in": end_of("leg_pull_in", {i + 1: s for i, s in _PULL_IN_END.items()}, []),
    "leg_pull_in_bench": end_of("leg_pull_in_bench", _PULL_IN_BENCH_END, []),
    "leg_slide": end_of("leg_slide", {3: ("b", [(34, 57), (44, 50), (54, 57)])}, []),
    "heel_touch": end_of("heel_touch", {1: ("h", (11, 49)), 3: ("b", [(19, 53), (27, 54), (35, 55)])}, []),
    "dragon_flag": end_of("dragon_flag", {5: ("b", [(17, 43), (36, 38), (56, 32)])}, []),
    "hip_roll": end_of("hip_roll", {3: ("b", [(32, 38), (42, 44), (40, 55)]),
                                    4: ("b", [(32, 38), (45, 42), (46, 53)])}, []),
    "lying_twist": end_of("lying_twist", {4: ("b", [(32, 38), (20, 36), (10, 28)])}, []),
    "side_crunch": end_of("side_crunch", {1: ("h", (8, 54)), 2: ("b", [(14, 57), (32, 57), (58, 57)]),
                                          3: ("b", [(15, 56), (14, 48)]), 4: ("b", [(15, 57), (22, 59)])}, []),
    "roll_down": end_of("roll_down", {1: ("h", (55, 41)), 2: ("b", [(51, 47), (40, 57), (26, 44), (16, 58)]),
                                      3: ("b", [(51, 48), (36, 44)])}, [(36, 44)]),
    "salute": end_of("salute", {0: ("b", [(26, 21), (16, 5)]), 1: ("b", [(38, 21), (48, 5)])}, []),
    "hundreds": end_of("hundreds", {3: ("b", [(18, 52), (32, 55)])}, [(46, 47)]),
    "flutter": end_of("flutter", {3: ("b", [(34, 57), (58, 54)]), 4: ("b", [(34, 57), (58, 45)])}, []),
    "knee_raise_lying": end_of("knee_raise_lying", {2: ("b", [(15, 57), (34, 57), (46, 53), (58, 52)])}, [(58, 51)]),
    "decline_leg_raise": end_of("decline_leg_raise", {4: ("b", [(17, 30), (34, 39), (54, 48)])}, [(54, 47)]),
    "leg_raise_thrust": end_of("leg_raise_thrust", {2: ("b", [(15, 57), (36, 49), (38, 22)])}, []),
    "boat": end_of("boat", {1: ("h", (16, 37)), 2: ("b", [(20, 43), (32, 57), (51, 41)]),
                            3: ("b", [(21, 44), (36, 45)])}, []),
    "bow": end_of("bow", {1: ("h", (11, 39)), 2: ("b", [(16, 44), (34, 56), (48, 50), (44, 34)]),
                          3: ("b", [(17, 44), (43, 35)])}, []),
    "locust": end_of("locust", {1: ("h", (9, 44)), 2: ("b", [(15, 48), (34, 58), (57, 48)]),
                                3: ("b", [(16, 48), (30, 49)])}, []),
    "camel": end_of("camel", {1: ("h", (48, 30)), 2: ("b", [(46, 59), (30, 59), (30, 40), (44, 33)]),
                              3: ("b", [(44, 34), (47, 57)])}, []),
    "hero": end_of("hero", {1: ("h", (38, 26)), 2: ("b", [(40, 59), (20, 58), (38, 54), (38, 34)]),
                            3: ("b", [(38, 36), (28, 47), (24, 53)])}, []),
    "wheel": end_of("wheel", {1: ("h", (18, 45)), 2: ("b", [(14, 59), (21, 38), (36, 26), (46, 41), (50, 59)])}, []),
    "fish": end_of("fish", {2: ("b", [(15, 50), (24, 43), (34, 57), (58, 57)]), 3: ("b", [(22, 46), (24, 58)])}, []),
    "all_fours": end_of("all_fours", {1: ("h", (11, 46)),
                                      2: ("b", [(16, 42), (28, 34), (40, 42), (40, 59), (54, 59)])}, []),
    "crow": end_of("crow", {1: ("h", (9, 48)), 2: ("b", [(16, 46), (33, 32), (24, 44), (36, 46)]),
                            3: ("b", [(17, 47), (22, 53), (22, 59)])}, []),
    "staff": end_of("staff", {1: ("h", (34, 28)), 2: ("b", [(10, 58), (34, 58), (34, 36)])}, []),
    "seated_fold": end_of("seated_fold", {1: ("h", (11, 48)), 2: ("b", [(10, 58), (34, 58), (16, 50)]),
                                          3: ("b", [(17, 51), (8, 56)])}, []),
    "straddle": end_of("straddle", {1: ("h", (32, 32)), 2: ("b", [(26, 39), (38, 39)]), 3: ("b", [(32, 39), (32, 50)]),
                                    6: ("b", [(26, 39), (10, 54)]), 7: ("b", [(38, 39), (54, 54)])}, []),
    "triangle": end_of("triangle", {1: ("h", (13, 27)), 2: ("b", [(32, 40), (18, 31)]),
                                    5: ("b", [(11, 48), (19, 32), (27, 16)])}, []),
    "chair_pose": end_of("chair_pose", {1: ("h", (25, 20)), 2: ("b", [(29, 27), (38, 43), (24, 48), (26, 59)]),
                                        3: ("b", [(29, 28), (20, 9)])}, []),
    "low_lunge": end_of("low_lunge", {1: ("h", (13, 36)), 2: ("b", [(14, 59), (13, 46), (31, 52), (47, 58), (60, 58)]),
                                      3: ("b", [(31, 52), (19, 40)]), 4: ("b", [(19, 41), (18, 58)])}, []),
    "calf_wall": end_of("calf_wall", {2: ("h", (12, 21)), 3: ("b", [(16, 26), (28, 42)]),
                                      4: ("b", [(28, 42), (18, 49), (18, 59)]), 5: ("b", [(28, 42), (46, 59)]),
                                      6: ("b", [(16, 27), (6, 26)])}, []),
    "hinge_hold": end_of("hinge_hold", {2: ("h", (12, 44)), 3: ("b", [(18, 40), (36, 38)]),
                                        6: ("b", [(19, 40), (8, 35)])}, []),
    "chair_fold": end_of("chair_fold", {4: ("h", (26, 49)), 5: ("b", [(30, 46), (40, 43), (24, 43), (24, 59)]),
                                        6: ("b", [(31, 46), (27, 56)])}, []),
    "supine_leg_up": end_of("supine_leg_up", {3: ("b", [(34, 57), (32, 33)]), 4: ("b", [(16, 56), (30, 40)])}, []),
    "snatch": end_of("snatch", _FROM_FLOOR, [(20, 54)]),
    "power_snatch": end_of("power_snatch", _FROM_FLOOR, [(20, 54)]),
    "hang_snatch": end_of("hang_snatch", {1: ("h", (28, 13)), 2: ("b", [(30, 21), (34, 40), (24, 46), (26, 58)]),
                                          3: ("b", [(30, 21), (32, 4)])}, [(32, 3)]),
    "snatch_pull": end_of("snatch_pull", {1: ("h", (14, 30)), 2: ("b", [(19, 33), (35, 40), (28, 48), (28, 58)]),
                                          3: ("b", [(19, 34), (20, 42), (21, 50)])}, [(21, 52)]),
    "power_jerk": end_of("power_jerk", {1: ("h", (26, 11)), 2: ("b", [(29, 19), (31, 40), (28, 50), (30, 58)]),
                                        3: ("b", [(29, 21), (23, 20)])}, [(22, 19)]),
    "rear_raise_prone": end_of("rear_raise_prone", {5: ("b", [(20, 28), (28, 21)])}, [(29, 19)]),
    "rear_raise_seated": end_of("rear_raise_seated", {5: ("b", [(23, 37), (28, 28)])}, [(29, 26)]),
})


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
    (r"crunch", "crunch_floor"),
    (r"sit.?up|situp", "situp"),
    (r"russian twist|twist", "twist"),
    (r"v.?up|jackknife|jack knife|toe touch", "vup"),
    (r"hanging (leg|knee|pike)|hanging raise", "=hanging-leg-raise"),
    (r"\bhang$|dead hang", "hang"),                      # not "Hang Clean" / "Hang Snatch"
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
    (r"reverse fly|rear delt|rear fly|reverse flye|prone deltoid|face away|\by raise|\bt raise|rear lateral", "rear_raise"),
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

# Round 3: the movements of the groups that shared one drawing, ahead of the
# general rules below (which would give them the shared one).
RULES[:0] = [
    # yoga and stretches
    (r"hare pose|shell stretch", "child"),
    (r"boat pose", "boat"), (r"upward facing bow|wheel pose", "wheel"), (r"\bbow pose", "bow"),
    (r"locust", "locust"), (r"camel", "camel"), (r"fish pose", "fish"), (r"hero pose", "hero"),
    (r"crow pose", "crow"), (r"staff pose", "staff"), (r"mighty pose|chair pose", "chair_pose"),
    (r"triangle|side angle", "triangle"), (r"straddle|wide leg stretch|turtle pose", "straddle"),
    (r"cat stretch|table pose|kneeling back stretch|dynamic back stretch|cat.?cow", "all_fours"),
    (r"runner'?s stretch|world'?s greatest|^hip stretch$|bench leg and hip", "low_lunge"),
    (r"seated (floor )?hamstring", "seated_fold"),
    (r"hamstring stretch \(supine\)|supine hamstring|big toe pose|90/90 hamstring", "supine_leg_up"),
    (r"^(?!.*hamstring).*(calf|soleus|achilles|peroneal|tibialis|lower leg) stretch", "calf_wall"),
    (r"low back chair", "chair_fold"), (r"upper body chair|^back stretch$", "hinge_hold"),
    (r"iron cross stretch", "lying_twist"), (r"revolved abdomen|hip roll|pendulum", "hip_roll"),
    (r"posterior capsule", "stretch_arm"),
    (r"overhead stretch|upward stretch|sun salutation", "salute"),
    (r"half moon", "stretch_side"), (r"cross.?leg(ged)? (forward fold|erector)", "stretch_seated"),
    (r"single.?leg stance|opposition reach", "stork"),
    # leg raises
    (r"double leg stretch|hundreds", "hundreds"),
    (r"flutter|scissor|alternating floor leg raise", "flutter"),
    (r"roman chair", "=parallel-bar-leg-raise"),
    (r"decline.*(leg|knee) raise|bench leg raise", "decline_leg_raise"),
    (r"leg raise with hip thrust", "leg_raise_thrust"),
    (r"(supine|lying).*knee raise|knee raise.*supine|single.?leg knee raise|knee to chest to leg|knee draw|ball leg lift",
     "knee_raise_lying"),
    # the rest of the core
    (r"ball (knee tuck|pull.?in|rollover)", "ball_tuck"),
    (r"bench leg pull", "leg_pull_in_bench"), (r"leg pull.?in|leg tuck|^rolling$", "leg_pull_in"),
    (r"^(?!.*reverse).*ball.*crunch|ball incline ab", "ball_crunch"),
    (r"ball roll down|^roll down$", "roll_down"), (r"ball head tilt", "neck"),
    (r"hand and foot exchange", "vup"),
    (r"leg slide|one.?knee to chest", "leg_slide"), (r"heel touch", "heel_touch"),
    (r"dragon flag", "dragon_flag"), (r"side jack?knife", "side_crunch"),
    (r"judo flip", "woodchop"), (r"figure eight", "swing"), (r"side touch", "side_bend"),
    (r"^(?!.*reverse).*decline.*crunch", "decline_crunch"),
    (r"^(?!.*reverse).*bench.*crunch", "=bench-crunch"),
    (r"cable.*crunch.*kneeling|cable (rope|oblique) crunch", "=cable-crunch"),
    (r"machine crunch|cable seated crunch", "=machine-ab-crunch"),
    (r"^(?!.*reverse).*(cross.?body|rotational crunch|air bike|bicycle)", "crunch_cross"),
    # Olympic lifts
    (r"barbell.*(snatch (pull|shrug)|high snatch)", "snatch_pull"),
    (r"barbell.*hang snatch", "hang_snatch"),
    (r"barbell.*(power snatch|one.?arm snatch)", "power_snatch"),
    (r"barbell.*(snatch|squat jerk)", "snatch"),
    (r"barbell power jerk", "power_jerk"),
    # rear delts on a bench or seated
    (r"(reverse fly|rear delt|rear fly).*prone|prone.*(reverse fly|rear delt|rear fly)", "rear_raise_prone"),
    (r"seated.*(reverse fly|rear delt|rear fly)", "rear_raise_seated"),
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
    """(file name, label, strokes, end strokes or None) for one exercise, or
    ("=slug", ...) for a hand-drawn one."""
    pose_key = resolve_pose(name, group)
    if pose_key.startswith("="):
        return pose_key[1:], None, None, None
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

    end_strokes = None
    if pose_key in POSE_ENDS:
        end = POSE_ENDS[pose_key]
        # The seated front raise swaps its arm above for the same one, so the
        # standing end pose fits it too.
        end_pose = dict(pose, parts=end["parts"], anchors=end["anchors"], bar=end.get("bar", pose.get("bar")))
        end_behind, end_front = draw_load(end_pose, equipment, one_arm)
        end_strokes = end_behind + end.get("bases", {}).get(base, BASES[base]) + end_pose["parts"] + end_front

    parts = [pose_key.replace("_", "-"), equipment]
    label = [pose["label"], EQUIPMENT_LABELS[equipment]]
    if base != pose["base"]:
        parts.append("seated")
        label.append("seated")
    if one_arm and pose["anchors"] and equipment != "none" and len(pose["anchors"]) > 1:
        parts.append("one-arm")
        label.append("one arm")
    return "x-" + "-".join(parts), " · ".join(label), strokes, end_strokes


def catalog_names():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "workout.db")
    if not os.path.exists(db_path):
        return []
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT exercise_name, muscle_group FROM exercises").fetchall()


def main():
    anim_dir = os.path.join(OUT, "anim")
    os.makedirs(anim_dir, exist_ok=True)
    # Start clean, so a pose that no exercise uses any more leaves no file.
    for folder in (OUT, anim_dir):
        for old in os.listdir(folder):
            if old.endswith(".svg"):
                os.remove(os.path.join(folder, old))

    labels, total = {}, 0
    animated, anim_total = 0, 0

    def write(file_name, label, strokes, end=None):
        nonlocal total, animated, anim_total
        svg = render(strokes)
        with open(os.path.join(OUT, file_name + ".svg"), "w", encoding="utf-8", newline="") as f:
            f.write(svg)
        labels[file_name] = label
        total += len(svg.encode())
        if end is not None:
            svg = render(strokes, end)
            with open(os.path.join(anim_dir, file_name + ".svg"), "w", encoding="utf-8", newline="") as f:
                f.write(svg)
            animated += 1
            anim_total += len(svg.encode())

    for name, strokes in ICONS.items():
        write(slug(name), name, strokes, ANIMATED.get(name))
    drawn = len(labels)

    mapping, generated = {}, {}
    for name, group in catalog_names():
        if slug(name) in labels:
            continue                                  # has its own drawing
        file_name, label, strokes, end = generated_icon(name, group)
        if strokes is not None and file_name not in generated:
            generated[file_name] = (label, strokes, end)
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
          f"{len(mapping)} exercises mapped to a shared icon; "
          f"{animated} of them animated, {anim_total} bytes")


if __name__ == "__main__":
    main()
