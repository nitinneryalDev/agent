"""Roz ki bilkul seedhi baatein bina model ke, milliseconds mein:

    "walking ho gayi"        -> check_in_habit   (sirf tab jab 'walking' naam ki habit sach mein saved ho)
    "meri habits dikhao"     -> habit_status
    "passport kahan hai"     -> find_item        (sirf tab jab 'passport' bilkul isi naam se saved ho)
    "hi" / "thanks"          -> seedha jawab

Niyam: shak ho to shortcut NAHI lete, model ke paas bhej dete hain. Galat shortcut se behtar hai thoda dheema sahi jawab.
"""
import re
from datetime import datetime

import briefing
import notes
from config import NOTES_FOLDER
from db import connect
from router import normalize
from tools import run_tool

GREETINGS = {"hi", "hii", "hiii", "hello", "helo", "hey", "namaste", "namaskar", "hola", "yo",
             "good evening", "hi assistant", "hello assistant", "namaste ji"}
THANKS = {"thanks", "thank you", "thankyou", "thx", "shukriya", "dhanyavad", "dhanyawad", "ok thanks",
          "thanks bhai", "thank you so much", "theek hai thanks"}
GREETING_REPLY = ("Namaste! Main aapki habits, kaam aur reminders, cheezein kahan rakhi hain, kitabein-joote, "
                  "contacts, health aur notes sambhalta hoon. Jaise bolo: 'walking ho gayi aaj' ya "
                  "'kal shaam 6 baje doodh lena yaad dilao'.")

_DONE = (r"(?:ho\s*gay[ai]|ho\s*gai|ho\s*gy[ai]|hogay[ai]|kar\s*l[ie]+(?:ya|a)?|kr\s*l[ie]+|done|completed?|"
         r"ho\s*chuk[aei]|kar\s*chuk[aei])")
_CHECKIN = re.compile(rf"^(?P<name>.+?)\s+{_DONE}(?:\s+(?:aaj|today|hai|h|bhi|ji|bhai))*$")
_CHECKIN_FILLER = {"aaj", "aj", "ki", "ka", "ke", "meri", "mera", "maine", "wali", "wala", "bhi", "habit", "today",
                   "main", "mein", "ne", "apni", "apna", "aaj ki"}
_WHERE = re.compile(r"^(?:mera|meri|mere|my|apna|apni|apne)?\s*(?P<name>.+?)\s+(?:kahan|kaha|kahaan|kidhar|where)"
                    r"(?:\s+(?:hai|hain|h|rakha|rakhi|rakhe|pada|padi|hai\s+rakha|is|are))*$")
_SHOW = {"dikhao", "dikha", "dikhaao", "batao", "bata", "btao", "show", "list", "status", "summary", "kya", "kitni",
         "kaisi", "check", "sab", "saari", "saare"}
_CHANGE = {"save", "add", "jodo", "likho", "shuru", "nayi", "naya", "new", "karo", "yaad", "set", "bana", "banao",
           "complete", "done", "gaya", "gayi", "delete", "hatao"}
_LISTS = [
    ({"habit", "habits", "habbits", "aadat", "aadatein", "streak", "streaks"}, "habit_status"),
    ({"task", "tasks", "kaam", "todo", "todos", "reminder", "reminders"}, "list_tasks"),
    ({"goal", "goals"}, "list_goals"),
    ({"health"}, "health_summary"),
]


def _exact(table, column, name):
    with connect() as conn:
        row = conn.execute(f"SELECT {column} FROM {table} WHERE {column} = ? COLLATE NOCASE", (name,)).fetchone()
    return row[column] if row else None


def _call(name, arguments):
    return {"name": name, "arguments": arguments, "result": run_tool(name, arguments)}


# "note karo: ...", "likh lo ki ...": seedha my_data/inbox.md mein, jahan se notes-search ise padh leta hai.
_NOTE = re.compile(r"^\s*(?:ek\s+)?note\s*(?:karo|kar\s*lo|likho|likh\s*lo|banao)?\s*[:\-]\s*(.{3,})$|"
                   r"^\s*(?:ye\s+)?(?:note|likh)\s+(?:karo|lo|kar\s*lo|likh\s*lo)\s+(?:ki\s+)?(.{3,})$", re.IGNORECASE)
# "aaj ka plan", "kal kya kya hai", "aaj ke reminders": din ka agenda, code se.
_TELL = r"(?:\s+(?:batao|bata|btao|dikhao|dikha|sunao|do|hain?))?$"
_AGENDA = re.compile(r"^(aaj|kal|parso|today|tomorrow)\s+(?:ka|ke|ki)?\s*(?:plan|schedule|reminders?|kaam|agenda)" + _TELL + "|"
                     r"^(aaj|kal|parso|today|tomorrow)\s+kya(?:\s+kya)?\s+(?:hai|karna\s+hai|karne\s+hain)$")
_WEEK = re.compile(r"^is\s+hafte\s+kya\s+(?:pending|baaki)\s+hai$|"
                   r"^(?:is\s+)?(?:hafte|week(?:ly)?)\s+(?:ka|ke)?\s*(?:plan|kaam|reminders?|pending)" + _TELL)


def _save_note(content):
    inbox = NOTES_FOLDER / "inbox.md"
    NOTES_FOLDER.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with inbox.open("a", encoding="utf-8") as file:
        file.write(f"\n[{stamp}] {content.strip()}\n")
    try:
        notes.INDEX.build()  # embed cache ki wajah se sirf naya hissa embed hota hai
        return "Note kar liya. Baad mein 'Notes' tab ya sawal se poochh sakte ho."
    except OSError:
        return "Note kar liya (file mein). Ollama band hai, isliye search mein thodi der baad aayega (Reload notes dabao)."


def try_shortcut(text):
    """Shortcut mila to {'kind', 'reply' (ya None), 'calls': [...]} deta hai, warna None."""
    match = _NOTE.match(text or "")
    if match:
        content = next(g for g in match.groups() if g)
        return {"kind": "note", "reply": _save_note(content), "calls": []}
    clean = normalize(text)
    if not clean:
        return None
    words = clean.split()
    if clean in ("good morning", "gm", "gud morning"):
        return {"kind": "brief", "reply": briefing.morning_text(), "calls": []}
    match = _AGENDA.match(clean)
    if match:
        day_word = match.group(1) or match.group(2)
        return {"kind": "brief", "reply": briefing.agenda_text(day_word), "calls": []}
    if _WEEK.match(clean):
        return {"kind": "brief", "reply": briefing.week_text(), "calls": []}
    if clean in GREETINGS:
        return {"kind": "greeting", "reply": GREETING_REPLY, "calls": []}
    if clean in THANKS:
        return {"kind": "thanks", "reply": "Koi baat nahi! Kabhi bhi bolo.", "calls": []}

    match = _CHECKIN.match(clean)
    if match:
        name_words = [w for w in match.group("name").split() if w not in _CHECKIN_FILLER]
        habit = _exact("habits", "name", " ".join(name_words)) if name_words else None
        if habit:
            return {"kind": "checkin", "reply": None, "calls": [_call("check_in_habit", {"habit": habit})]}

    match = _WHERE.match(clean)
    if match:
        name = match.group("name").strip()
        item = _exact("items", "name", name)
        if item:
            return {"kind": "where", "reply": None, "calls": [_call("find_item", {"query": item})]}
        thing = _exact("things", "name", name)
        if thing:
            return {"kind": "where", "reply": None, "calls": [_call("find_things", {"query": thing})]}

    if len(words) <= 6 and not set(words) & _CHANGE:
        for topic_words, tool in _LISTS:
            if set(words) & topic_words and (set(words) & _SHOW or len(words) <= 2):
                return {"kind": "list", "reply": None, "calls": [_call(tool, {})]}
    return None
