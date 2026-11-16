"""Health ke roz ke numbers (paani, neend, training...). Sirf tumhare laptop par rehta hai."""
import math
import re
from datetime import datetime, timedelta

from db import connect

# Har kind ka matlab aur unit. Naya kind jodna ho to yahan ek line badhao.
KINDS = {
    "hydration": "glasses",
    "sleep": "hours",
    "training": "minutes",
    "mobility": "minutes",
    "energy": "score 1-10",
}
DATE_FORMAT = "%Y-%m-%d"
# Model kabhi "water" ya "neend" likhta hai: sahi kind mein badal do.
KIND_SYNONYMS = {
    "water": "hydration", "paani": "hydration", "pani": "hydration", "drink": "hydration",
    "neend": "sleep", "nind": "sleep", "sona": "sleep", "rest": "sleep",
    "workout": "training", "exercise": "training", "gym": "training", "running": "training", "run": "training",
    "stretching": "mobility", "stretch": "mobility", "yoga": "mobility", "flexibility": "mobility",
    "mood": "energy", "urja": "energy",
}
LABELS = {"hydration": "Paani", "sleep": "Neend", "training": "Training", "mobility": "Mobility", "energy": "Energy"}
# User ke shabdon se kind pehchaanna (model kabhi neend ko "energy" likh deta hai).
_KIND_WORDS = {
    "sleep": {"soya", "soyi", "soye", "sona", "neend", "nind", "sleep", "slept"},
    "hydration": {"paani", "pani", "water", "glass", "glasses", "gilas", "gilaas"},
    "training": {"training", "workout", "gym", "exercise", "running", "daud", "daudna", "cardio", "weights"},
    "mobility": {"mobility", "stretching", "stretch", "yoga"},
    "energy": {"energy", "urja", "mood"},
}


def kind_in(text):
    """Text mein sirf ek hi kind ke shabd hon to wo kind, warna None (shak ho to model ka hi maano)."""
    words = set(re.findall(r"[a-z]+", str(text).lower()))
    found = [kind for kind, keys in _KIND_WORDS.items() if words & keys]
    return found[0] if len(found) == 1 else None


def log_health(kind, value, day=None):
    """Aaj (ya di gayi tareekh) ka ek number likho. Usi din dobara likho to badal jata hai."""
    kind = str(kind).strip().lower()
    kind = KIND_SYNONYMS.get(kind, kind)
    if kind not in KINDS:
        raise ValueError(f"kind inme se ek ho: {', '.join(KINDS)}.")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("value number honi chahiye.")
    if not math.isfinite(value):  # "inf"/"nan" JSON tod deta hai (My data phir kabhi nahi khulta)
        raise ValueError("value number honi chahiye.")
    if value < 0:
        raise ValueError("value negative nahi ho sakti.")
    if value > 100000:
        raise ValueError("value itni badi nahi ho sakti.")
    if kind == "energy" and not 1 <= value <= 10:
        raise ValueError("energy 1 se 10 ke beech honi chahiye.")
    day = day.strip() if day and str(day).strip() else datetime.now().strftime(DATE_FORMAT)
    try:
        datetime.strptime(day, DATE_FORMAT)
    except ValueError:
        raise ValueError("day aise likho: 2026-11-10.")
    with connect() as conn:
        conn.execute(
            "INSERT INTO health_logs (day, kind, value) VALUES (?, ?, ?) "
            "ON CONFLICT(day, kind) DO UPDATE SET value = excluded.value",
            (day, kind, value),
        )
    return {"day": day, "kind": kind, "value": value, "unit": KINDS[kind]}


def value_on(kind, day=None):
    """Us din ka likha hua number (na ho to None). "2 glass aur piya" ko jodne ke kaam aata hai."""
    day = day or datetime.now().strftime(DATE_FORMAT)
    with connect() as conn:
        row = conn.execute("SELECT value FROM health_logs WHERE day = ? AND kind = ?", (day, kind)).fetchone()
    return row["value"] if row else None


def health_summary(days=7):
    """Pichhle `days` din ka hisaab: har kind ka average aur kitne din likha."""
    try:
        days = max(1, min(int(days), 365))
    except (TypeError, ValueError):
        raise ValueError("days number honi chahiye.")
    first_day = (datetime.now() - timedelta(days=days - 1)).strftime(DATE_FORMAT)
    with connect() as conn:
        rows = conn.execute(
            "SELECT kind, COUNT(*) AS days_logged, AVG(value) AS average, MAX(day) AS last_day "
            "FROM health_logs WHERE day >= ? GROUP BY kind ORDER BY kind",
            (first_day,),
        ).fetchall()
    return [
        {"kind": r["kind"], "unit": KINDS.get(r["kind"], ""), "days_logged": r["days_logged"],
         "average": round(r["average"], 1), "last_day": r["last_day"]}
        for r in rows
    ]
