"""Cheezein kahan rakhi hain (stone, passport, charger...)."""
from datetime import datetime

from db import clean_query, connect, like_pattern


def _now():
    return datetime.now().isoformat(timespec="seconds")


def remember_item(item, place):
    """Cheez aur uski jagah yaad rakho. Pehle ki jagah (agar thi) wapas deta hai."""
    item, place = clean_name(item), place.strip()
    if not item or not place:
        raise ValueError("Cheez aur jagah dono chahiye.")
    with connect() as conn:
        old = conn.execute("SELECT place FROM items WHERE name = ?", (item,)).fetchone()
        conn.execute(
            "INSERT INTO items (name, place, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET place = excluded.place, updated_at = excluded.updated_at",
            (item, place, _now()),
        )
    return old["place"] if old else None


_FILLER = {"mera", "meri", "mere", "my", "the", "kahan", "kaha", "kahaan", "kidhar", "hai", "hain", "h", "rakha",
           "rakhi", "rakhe", "apna", "apni", "apne", "where", "is", "are", "wala", "wali", "wale"}


def clean_name(text):
    """'mera passport' -> 'passport' (aage ke mera/meri hata do)."""
    words = str(text or "").strip().split()
    while len(words) > 1 and words[0].lower() in {"mera", "meri", "mere", "my", "apna", "apni", "apne", "the"}:
        words.pop(0)
    return " ".join(words)


def find_item(query):
    """Naam mein query wali saari cheezein dhundho. Na mile to khali list.
    Kai shabd hon to har shabd naam mein hona chahiye ("office ki chabi" -> 'chabi')."""
    query = query.strip()
    if not query:
        return []
    with connect() as conn:
        rows = conn.execute(
            "SELECT name, place, updated_at FROM items WHERE name LIKE ? ESCAPE '\\' ORDER BY updated_at DESC",
            (like_pattern(query),),
        ).fetchall()
        words = [w for w in query.lower().split() if w not in _FILLER]
        if not rows and words:
            sql = " AND ".join(["name LIKE ? ESCAPE '\\'"] * len(words))
            rows = conn.execute(f"SELECT name, place, updated_at FROM items WHERE {sql} ORDER BY updated_at DESC",
                                [like_pattern(w) for w in words]).fetchall()
    return [dict(row) for row in rows]


def find_one(text):
    """Ek hi cheez dhundho (naam se). Na mile ya kai milein to ValueError."""
    name = clean_name(clean_query(text))
    with connect() as conn:
        row = conn.execute("SELECT name, place FROM items WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
    if row:
        return dict(row)
    matches = find_item(name)
    if not matches:
        raise ValueError(f"'{name}' naam ki koi cheez yaad nahi rakhi hai.")
    if len(matches) > 1:
        raise ValueError("Kai cheezein milti hain: " + ", ".join(m["name"] for m in matches[:5]) + ". Poora naam batao.")
    return {"name": matches[0]["name"], "place": matches[0]["place"]}


def delete_item(name, _name=None):
    """Cheez ki entry hamesha ke liye hatao. Sirf user ke pakke 'haan' ke baad. (Naam hi iski pehchaan hai.)"""
    with connect() as conn:
        return conn.execute("DELETE FROM items WHERE name = ? COLLATE NOCASE", (name,)).rowcount > 0
