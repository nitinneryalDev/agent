"""Tumhari cheezein jinhe track karna hai: kitabein, jootein, kapde... Har ek ke saath details."""
import json
import re
from datetime import datetime

from db import clean_query, connect, like_pattern

MAX_DETAILS_CHARS = 1000

# Ek hi cheez ke kai naam: model kabhi "shoes" likhta hai, kabhi "joote". Database mein ek hi naam rakhte hain.
CATEGORY_SYNONYMS = {
    "shoe": ["shoe", "shoes", "joota", "joote", "jootein", "jute", "juta", "jooti", "sneaker", "sneakers",
             "chappal", "chappals", "sandal", "sandals", "slipper", "slippers", "footwear"],
    "book": ["book", "books", "kitab", "kitaab", "kitabein", "kitaabein", "novel", "novels"],
    "shirt": ["shirt", "shirts", "tshirt", "tshirts", "t-shirt", "t-shirts", "kameez"],
    "dress": ["dress", "dresses", "frock", "gown"],
    "clothes": ["clothes", "kapde", "kapda", "kapdon", "jeans", "jacket", "jackets", "kurta", "kurte", "saree",
                "sari", "trouser", "trousers", "pant", "pants", "hoodie", "sweater"],
}
_CATEGORY_OF = {word: category for category, words in CATEGORY_SYNONYMS.items() for word in words}
_SEARCH_FILLER = {"mera", "meri", "mere", "my", "the", "kahan", "kaha", "kidhar", "hai", "hain", "h", "ka", "ki",
                  "ke", "wala", "wali", "wale", "kaunsi", "kaunse", "kaunsa", "sab", "saari", "saare", "all", "list",
                  "dikhao", "batao", "kya", "konsi", "apni", "apne", "apna", "paas", "pass", "kitni", "kitne", "hai?",
                  "hain?", "saved", "rakhi", "rakhe", "rakha"}


def meaningful_words(text):
    return [w for w in re.findall(r"[\w-]+", str(text).lower()) if w not in _SEARCH_FILLER]


def category_in(text):
    """User ke text mein koi category ka shabd ho to wo category ("kaunsi books hain" -> "book")."""
    for word in re.findall(r"[\w-]+", str(text).lower()):
        if word in _CATEGORY_OF:
            return _CATEGORY_OF[word]
    return None


def normalize_category(text):
    text = str(text or "").strip().lower()
    return _CATEGORY_OF.get(text, text)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _clean_details(details):
    """details = {"color": "black", "size": 9}. Sirf seedhe text/number allowed.
    Chhota model kabhi "black" ya "color: black, brand: Nike" jaisa text bhej deta hai: use bhi samajh lete hain."""
    if details is None or details == "" or details == "{}":
        return {}
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except ValueError:
            pairs = re.findall(r"([A-Za-z ]+?)\s*[:=]\s*([^,;]+)", details)
            details = {k.strip(): v.strip() for k, v in pairs} if pairs else {"note": details.strip()}
    if isinstance(details, list):
        details = {"note": ", ".join(str(item) for item in details)}
    if not isinstance(details, dict):
        details = {"note": str(details)}
    cleaned = {str(k).strip(): v for k, v in details.items() if str(k).strip() and v not in (None, "")}
    if not all(isinstance(v, (str, int, float, bool)) for v in cleaned.values()):
        raise ValueError("details ki har value seedha text ya number honi chahiye.")
    if len(json.dumps(cleaned, ensure_ascii=False)) > MAX_DETAILS_CHARS:
        raise ValueError("details bahut bade hain.")
    return cleaned


def _text_or_none(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def add_thing(category, name, place=None, status=None, details=None):
    """Nayi cheez jodo. category: book, shoe, dress, shirt... Cheez ki id wapas deta hai."""
    category, name = normalize_category(category), name.strip()
    if not category or not name:
        raise ValueError("category aur name dono chahiye.")
    now = _now()
    with connect() as conn:
        return conn.execute(
            "INSERT INTO things (category, name, status, place, details, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (category, name, _text_or_none(status), _text_or_none(place),
             json.dumps(_clean_details(details), ensure_ascii=False), now, now),
        ).lastrowid


def find_things(query=None, category=None, status=None, limit=20):
    """Text (naam, jagah ya details mein), category ya status se dhundho. Sabse naye pehle."""
    try:
        limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        raise ValueError("limit number honi chahiye.")
    conditions, params = [], []
    if _text_or_none(category):
        conditions.append("category = ?")
        params.append(normalize_category(category))
    if _text_or_none(status):
        conditions.append("status = ? COLLATE NOCASE")
        params.append(status.strip())
    if _text_or_none(query):
        # Har shabd kahin na kahin milna chahiye: "black jootein" = details mein black AUR category shoe.
        words = [w for w in re.findall(r"[\w-]+", query.lower()) if w not in _SEARCH_FILLER] or [query.strip().lower()]
        for word in words:
            if word in _CATEGORY_OF:
                conditions.append("category = ?")
                params.append(_CATEGORY_OF[word])
                continue
            conditions.append("(name LIKE ? ESCAPE '\\' OR place LIKE ? ESCAPE '\\' OR details LIKE ? ESCAPE '\\' "
                              "OR status LIKE ? ESCAPE '\\')")
            params += [like_pattern(word)] * 4
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"SELECT id, category, name, status, place, details, updated_at FROM things {where} ORDER BY updated_at DESC, id DESC LIMIT {limit}"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [{**dict(row), "details": json.loads(row["details"])} for row in rows]


def find_thing_id(text):
    """Cheez ko id ya naam se pehchano ("Atomic Habits" -> 2). Ek hi mile to id, warna ValueError."""
    text = str(text or "").strip()
    if not text:
        raise ValueError("Kaunsi cheez? Naam ya id batao.")
    if text.isdigit():
        return int(text)
    text = clean_query(text)
    with connect() as conn:
        rows = conn.execute("SELECT id, name FROM things WHERE name = ? COLLATE NOCASE", (text,)).fetchall()
        if not rows:
            rows = conn.execute("SELECT id, name FROM things WHERE name LIKE ? ESCAPE '\\'", (like_pattern(text),)).fetchall()
        if not rows:  # har shabd naam mein ho ("pegasus wale joote" -> "Nike Pegasus"; "joote" category hai, naam nahi)
            words = [w for w in meaningful_words(text) if w not in _CATEGORY_OF]
            if words:
                sql = " AND ".join(["name LIKE ? ESCAPE '\\'"] * len(words))
                rows = conn.execute(f"SELECT id, name FROM things WHERE {sql}", [like_pattern(w) for w in words]).fetchall()
    if not rows:
        raise ValueError(f"Cheez saved nahi hai: '{text}'. Nayi cheez ho to add_thing use karo.")
    if len(rows) > 1:
        raise ValueError("Kai cheezein milti hain: " + ", ".join(r["name"] for r in rows[:5]) + ". Poora naam batao.")
    return rows[0]["id"]


def get_thing(thing_id):
    with connect() as conn:
        row = conn.execute("SELECT id, category, name, status, place, details FROM things WHERE id = ?", (thing_id,)).fetchone()
    return {**dict(row), "details": json.loads(row["details"])} if row else None


def update_thing(thing_id, status=None, place=None, details=None):
    """Cheez ka status, jagah ya details badlo (details purane mein judte hain). Id na mile to False."""
    try:
        thing_id = int(thing_id)
    except (TypeError, ValueError):
        raise ValueError("thing_id number honi chahiye.")
    new_details = _clean_details(details)
    with connect() as conn:
        row = conn.execute("SELECT status, place, details FROM things WHERE id = ?", (thing_id,)).fetchone()
        if row is None:
            return False
        merged = {**json.loads(row["details"]), **new_details}
        conn.execute(
            "UPDATE things SET status = ?, place = ?, details = ?, updated_at = ? WHERE id = ?",
            (_text_or_none(status) or row["status"], _text_or_none(place) or row["place"],
             json.dumps(merged, ensure_ascii=False), _now(), thing_id),
        )
    return True


def delete_thing(thing_id, name):
    """Cheez hamesha ke liye hatao. Sirf user ke pakke 'haan' ke baad. id + naam dono milein."""
    with connect() as conn:
        return conn.execute("DELETE FROM things WHERE id = ? AND name = ?", (int(thing_id), name)).rowcount > 0
