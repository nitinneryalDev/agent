"""Roz ki aadatein (habits): check-in aur streak (lagatar kitne din)."""
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta

from db import clean_query, connect, like_pattern

DATE_FORMAT = "%Y-%m-%d"


def compute_streak(done_days, today):
    """Lagatar kitne din. Aaj kiya ho to aaj tak, nahi kiya to kal tak ginte hain
    (kal tak ki streak aaj raat tak toot-ti nahi)."""
    day = today if today in done_days else today - timedelta(days=1)
    streak = 0
    while day in done_days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def _parse_day(text):
    today = date.today()
    if not text or not str(text).strip():
        return today
    try:
        day = datetime.strptime(str(text).strip(), DATE_FORMAT).date()
    except ValueError:
        raise ValueError("day aise likho: 2026-11-10.")
    if day > today:
        raise ValueError("Aane wale din ka check-in nahi ho sakta.")
    return day


def _find_habit(conn, text):
    text = text.strip()
    if not text:
        raise ValueError("Habit ka naam chahiye.")
    row = conn.execute("SELECT id, name FROM habits WHERE name = ?", (text,)).fetchone()
    if row:
        return row
    rows = conn.execute("SELECT id, name FROM habits WHERE name LIKE ? ESCAPE '\\'", (like_pattern(text),)).fetchall()
    if len(rows) == 1:  # "walk" likha aur ek hi habit "walking" mili
        return rows[0]
    if not rows:
        raise ValueError(f"'{text}' naam ki habit nahi mili. Pehle add_habit se jodo.")
    raise ValueError("Kai habits milti hain: " + ", ".join(r["name"] for r in rows) + ". Poora naam batao.")


def add_habit(name):
    """Nayi habit track karna shuru karo."""
    name = name.strip()
    if not name:
        raise ValueError("Habit ka naam chahiye.")
    try:
        with connect() as conn:
            return conn.execute(
                "INSERT INTO habits (name, created_at) VALUES (?, ?)",
                (name, datetime.now().isoformat(timespec="seconds")),
            ).lastrowid
    except sqlite3.IntegrityError as error:
        raise ValueError("Ye habit pehle se hai.") from error


def check_in(habit, day=None):
    """Habit aaj (ya di gayi tareekh par) ho gayi likho. Dobara likhne se kuch nahi bigadta."""
    day = _parse_day(day)
    with connect() as conn:
        row = _find_habit(conn, habit)
        conn.execute("INSERT OR IGNORE INTO habit_checkins (habit_id, day) VALUES (?, ?)", (row["id"], day.isoformat()))
        done = {date.fromisoformat(r["day"]) for r in
                conn.execute("SELECT day FROM habit_checkins WHERE habit_id = ?", (row["id"],))}
    return {"habit": row["name"], "day": day.isoformat(), "streak": compute_streak(done, date.today())}


def habit_status(days=7):
    """Har habit: streak, aur pichhle `days` din mein kitne din ki."""
    try:
        days = max(1, min(int(days), 365))
    except (TypeError, ValueError):
        raise ValueError("days number honi chahiye.")
    today = date.today()
    first = today - timedelta(days=days - 1)
    with connect() as conn:
        habits = conn.execute("SELECT id, name FROM habits ORDER BY name").fetchall()
        checkins = conn.execute("SELECT habit_id, day FROM habit_checkins").fetchall()
    done_by_habit = defaultdict(set)
    for row in checkins:
        done_by_habit[row["habit_id"]].add(date.fromisoformat(row["day"]))
    return [
        {
            "habit": h["name"],
            "streak": compute_streak(done_by_habit[h["id"]], today),
            "done_today": today in done_by_habit[h["id"]],
            "done_days": sum(1 for d in done_by_habit[h["id"]] if first <= d <= today),
            "out_of_days": days,
        }
        for h in habits
    ]


def find_habit(text):
    """Habit ko naam (ya adhoore naam) se dhundho: {'id', 'name'}. Na mile to ValueError."""
    with connect() as conn:
        return dict(_find_habit(conn, clean_query(text)))


def delete_habit(habit_id, name):
    """Habit aur uske saare check-ins hatao (foreign key se check-ins apne aap hat jaate hain). id + naam dono milein."""
    with connect() as conn:
        return conn.execute("DELETE FROM habits WHERE id = ? AND name = ?", (int(habit_id), name)).rowcount > 0
