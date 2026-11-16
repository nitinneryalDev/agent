"""Wo tools jo model bula sakta hai. Har tool = naam + kaam ka description + inputs + asli function.
Jaan-boojhkar koi shell ya internet wala tool nahi diya: model sirf yaad rakh aur dekh sakta hai.

Hatana (delete) do kadam mein hota hai, aur model sirf pehla kadam utha sakta hai:
  1. remove_* tools kuch NAHI hatate. Wo sirf cheez dhundhkar user se poochhte hain: "Pakka hata doon?"
  2. confirm_delete() asli mein hatata hai. Ye model ki list mein hai hi nahi: sirf user ke "haan"
     (ya dashboard ke button) ke baad agent/dashboard ka code ise bulata hai.

Chhota model arguments mein galtiyan karta hai (number ko text, details ko "black", id ki jagah naam),
isliye yahan tools thode "maaf karne wale" hain: jo samajh aaye wo maan lete hain, aur galti par saaf wajah dete hain.
"""
import inspect
import json
import sqlite3

import contacts
import habits
import health
import items
import planner
import replies
import things
import when
from notes import INDEX


# ---------- Tools ke function (database ke functions ko model ke liye saaf jawab dene wale banate hain) ----------
def remember_item(item, place):
    item = items.clean_name(item)
    previous = items.remember_item(item, place)
    return {"saved": True, "item": item, "place": place.strip(), "previous_place": previous}


def find_item(query):
    matches = items.find_item(query)
    if matches:
        return {"matches": matches}
    # Chhota model kabhi jootein/books ke liye bhi find_item bula deta hai: tracked cheezein bhi dekho.
    found = things.find_things(query=query)
    if found:
        return {"things": found}
    return {"matches": [], "say": f"'{items.clean_name(query)}' abhi save nahi hai. Batao kahan rakha hai, main yaad rakh lunga."}


def add_contact(name, phone, nicknames=None):
    if isinstance(nicknames, str):  # "mumi, maa" jaisa text bhi chalega
        nicknames = [part.strip() for part in nicknames.replace(";", ",").split(",")]
    names = [n for n in (nicknames or []) if isinstance(n, str) and n.strip()]
    contacts.add_contact(name, str(phone), names)
    return {"saved": True, "name": name.strip(), "phone": str(phone).strip(), "nicknames": names}


def call_contact(name):
    contact = contacts.find_contact(name)
    if contact is None:
        return {"found": False, "say": f"'{name}' naam ka contact nahi mila. Naam aur number batao, main save kar dunga."}
    # Is laptop par asli call nahi lagti. Jawab mein saaf likhte hain taaki model jhooth na bole.
    return {"found": True, "contact": contact, "note": "Demo only: no real call is placed from this laptop."}


def add_task(title, due=None, recurrence=None):
    # recurrence model ke schema mein NAHI hai: agent._repair ise user ke shabdon ("roz", "har somvar") se bharta hai.
    recurrence = recurrence or when.parse_recurrence(str(title))
    task_id = planner.add_task(title, due, recurrence)
    due_at = planner.parse_due(due) if due and str(due).strip() else None
    return {"saved": True, "task_id": task_id, "title": title.strip(), "due": due_at, "recurrence": recurrence}


def reschedule_task(task=None, task_id=None, due=None):
    """Pending reminder ka samay badlo. Model ki list mein nahi: agent ka code ise seedha chalata hai."""
    found = planner.find_open_task(task if task not in (None, "") else task_id)
    result = planner.reschedule_task(found["id"], due)
    return {"saved": True, **result}


def list_tasks():
    return {"tasks": planner.list_tasks()}


def complete_task(task=None, task_id=None):
    found = planner.find_open_task(task if task not in (None, "") else task_id)
    planner.complete_task(found["id"])
    return {"completed": True, "task_id": found["id"], "title": found["title"]}


def add_goal(title, target_date):
    goal_id = planner.add_goal(title, target_date)
    return {"saved": True, "goal_id": goal_id, "title": title.strip(), "target_date": planner.parse_target_date(target_date)}


def list_goals():
    return {"goals": planner.list_goals()}


def log_health(kind, value, day=None):
    return {"saved": True, **health.log_health(kind, value, day)}


def health_summary(days=7):
    return {"summary": health.health_summary(days)}


def add_habit(name):
    return {"saved": True, "habit_id": habits.add_habit(name), "name": name.strip()}


def check_in_habit(habit, day=None):
    return {"saved": True, **habits.check_in(habit, day)}


def habit_status(days=7):
    return {"habits": habits.habit_status(days)}


def add_thing(category, name, place=None, status=None, details=None):
    thing_id = things.add_thing(category, name, place, status, details)
    return {"saved": True, "thing_id": thing_id, **things.get_thing(thing_id)}


def find_things(query=None, category=None, status=None):
    found = things.find_things(query, category, status)
    if not found:
        what = query or category or status or "ye"
        return {"things": [], "say": f"'{what}' jaisa kuch save nahi hai. Batao kya hai, main add kar dunga."}
    return {"things": found}


def update_thing(thing=None, thing_id=None, status=None, place=None, details=None):
    found_id = things.find_thing_id(thing if thing not in (None, "") else thing_id)
    things.update_thing(found_id, status, place, details)
    return {"updated": True, **things.get_thing(found_id)}


def search_notes(question, original=None):
    INDEX.ensure_built()
    passages = INDEX.search_best([question, original])
    return {"question": question, "passages": [{"file": c["source"], "score": round(s, 3), "text": c["text"]}
                                               for s, c in passages]}


# ---------- Hatana: pehla kadam (sirf poochhna) ----------
def _ask_to_delete(kind, target, name, label, noun):
    return {"confirm": {"kind": kind, "id": target, "name": name, "label": label},
            "say": f"Pakka? Ye {noun} hata doon: {label}? 'Haan' ya 'Nahi' bolo."}


def remove_task(task):
    found = planner.find_open_task(task)
    when = f" ({replies.human_time(found['due_at'])})" if found.get("due_at") else ""
    return _ask_to_delete("task", found["id"], found["title"], f"{found['title']}{when}", "reminder")


def remove_item(item):
    found = items.find_one(item)
    return _ask_to_delete("item", found["name"], found["name"], f"{found['name']} ({found['place']})", "entry")


def remove_thing(thing):
    found = things.get_thing(things.find_thing_id(thing))
    return _ask_to_delete("thing", found["id"], found["name"], f"{found['name']} ({found['category']})", "cheez")


def remove_habit(habit):
    found = habits.find_habit(habit)
    return _ask_to_delete("habit", found["id"], found["name"], f"{found['name']} (saare check-ins bhi)", "habit")


def remove_goal(goal):
    found = planner.find_goal(goal)
    return _ask_to_delete("goal", found["id"], found["title"], f"{found['title']} (target {found['target_date']})", "goal")


def remove_contact(name):
    found = contacts.find_contact_row(name)
    return _ask_to_delete("contact", found["id"], found["name"], f"{found['name']} ({found['phone']})", "contact")


# ---------- Hatana: doosra kadam (asli delete). Model ki list mein NAHI. ----------
_DELETERS = {
    "task": planner.delete_task, "item": items.delete_item, "thing": things.delete_thing,
    "habit": habits.delete_habit, "goal": planner.delete_goal, "contact": contacts.delete_contact,
}


def confirm_delete(kind, target, name, label=""):
    """User ke pakke 'haan' ke baad hi bulao (agent ka confirmation flow ya dashboard ka confirm button).
    target (id) aur name dono milne chahiye, warna kuch nahi hatta (purani screen se galat cheez na hate)."""
    deleter = _DELETERS.get(kind)
    if deleter is None:
        raise ValueError("Ye cheez hatayi nahi ja sakti.")
    if not name:
        raise ValueError("Kya hatana hai, ye pakka nahi hai. List dobara dekho.")
    if not deleter(target, name):
        raise ValueError("Ye entry badal gayi ya pehle hi hat chuki hai. List dobara dekho.")
    return {"deleted": True, "kind": kind, "label": label or name}


# ---------- Model ko dikhane wali list ----------
def _tool(function, description, properties, required=()):
    schema = {
        "type": "function",
        "function": {
            "name": function.__name__,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": list(required)},
        },
    }
    return function, schema


_TEXT = {"type": "string"}
_REGISTRY = [
    _tool(remember_item, "Save where a loose object is kept (passport, charger, umbrella). Use when the user STATES where it is.",
          {"item": _TEXT, "place": _TEXT}, ["item", "place"]),
    _tool(find_item, "Find where a loose object is kept. Use when the user ASKS where something is.",
          {"query": _TEXT}, ["query"]),
    _tool(add_contact, "Save a contact with phone number and optional nicknames (e.g. mumi, maa for Mom).",
          {"name": _TEXT, "phone": _TEXT, "nicknames": {"type": "array", "items": _TEXT}}, ["name", "phone"]),
    _tool(call_contact, "Call a person or look up their number, by name or nickname (e.g. mumi).",
          {"name": _TEXT}, ["name"]),
    _tool(add_task, "Add a to-do or reminder. 'due' must be the FULL date and time YYYY-MM-DD HH:MM when a time is said.",
          {"title": {"type": "string", "description": "short task in the user's own words"}, "due": _TEXT}, ["title"]),
    _tool(list_tasks, "List pending to-dos, soonest first.", {}),
    _tool(complete_task, "Mark a to-do as done. 'task' = a few words of its title (e.g. 'bijli ka bill') or its id.",
          {"task": _TEXT}, ["task"]),
    _tool(add_goal, "Save a goal with a target date (YYYY-MM-DD).",
          {"title": _TEXT, "target_date": _TEXT}, ["title", "target_date"]),
    _tool(list_goals, "List goals with days left.", {}),
    _tool(log_health, "Log one health number for a day: hydration (glasses of water), sleep (hours), training (minutes), mobility (minutes), energy (1-10).",
          {"kind": {"type": "string", "enum": list(health.KINDS)}, "value": {"type": "number"}, "day": _TEXT}, ["kind", "value"]),
    _tool(health_summary, "Summarise health logs for the last N days.",
          {"days": {"type": "integer"}}),
    _tool(add_habit, "Start tracking a NEW daily habit (e.g. walking, reading, no sugar).",
          {"name": _TEXT}, ["name"]),
    _tool(check_in_habit, "Mark an existing habit as done today (or on a given day YYYY-MM-DD). Returns the streak.",
          {"habit": _TEXT, "day": _TEXT}, ["habit"]),
    _tool(habit_status, "Show every habit with its streak and how many of the last N days it was done.",
          {"days": {"type": "integer"}}),
    _tool(add_thing, "Save something the user owns: a book, shoes, a dress, a shirt. category = book/shoe/dress/shirt/clothes; "
                     "details = object with extra info like color, brand, size, author; place = where it is kept.",
          {"category": _TEXT, "name": _TEXT, "place": _TEXT, "status": _TEXT, "details": {"type": "object"}}, ["category", "name"]),
    _tool(find_things, "Search the user's saved belongings (books, shoes, clothes) by words, category or status (reading, finished, lent).",
          {"query": _TEXT, "category": _TEXT, "status": _TEXT}),
    _tool(update_thing, "Change status, place or details of a saved thing (e.g. book finished, shoes in laundry). 'thing' = its name or id.",
          {"thing": _TEXT, "status": _TEXT, "place": _TEXT, "details": {"type": "object"}}, ["thing"]),
    _tool(search_notes, "Search the user's personal notes (about me, family, job, goals, health) to answer a question about their life.",
          {"question": _TEXT}, ["question"]),
    _tool(remove_task, "Delete/cancel a reminder or to-do. Does NOT delete yet: it asks the user to confirm. 'task' = a few words of its title.",
          {"task": _TEXT}, ["task"]),
    _tool(remove_item, "Delete a remembered object entry (where something is kept). Only asks the user to confirm first.",
          {"item": _TEXT}, ["item"]),
    _tool(remove_thing, "Delete a saved belonging (book, shoes, clothes). Only asks the user to confirm first.",
          {"thing": _TEXT}, ["thing"]),
    _tool(remove_habit, "Stop tracking a habit and delete it. Only asks the user to confirm first.",
          {"habit": _TEXT}, ["habit"]),
    _tool(remove_goal, "Delete a goal. Only asks the user to confirm first.",
          {"goal": _TEXT}, ["goal"]),
    _tool(remove_contact, "Delete a contact. Only asks the user to confirm first.",
          {"name": _TEXT}, ["name"]),
]

TOOL_SCHEMAS = [schema for _, schema in _REGISTRY]
TOOL_FUNCTIONS = {function.__name__: function for function, _ in _REGISTRY}
SCHEMA_BY_NAME = {schema["function"]["name"]: schema for schema in TOOL_SCHEMAS}


def schemas_for(names):
    """Sirf in tools ke schema (router jo chune)."""
    return [SCHEMA_BY_NAME[name] for name in names if name in SCHEMA_BY_NAME]


def _keep_known_arguments(function, arguments):
    """Model kabhi aise argument bhej deta hai jo function leta hi nahi: unhe chupchap hata do.
    Khali values (None, "") bhi hata do, taaki default lage."""
    accepted = inspect.signature(function).parameters
    return {k: v for k, v in arguments.items() if k in accepted and v not in (None, "")}


def run_tool(name, arguments):
    """Model ke maange hue tool ko chalao. Hamesha ek text wapas deta hai (galti ho to bhi),
    taaki model galti dekhke khud sudhaar sake."""
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    if isinstance(arguments, str):  # kabhi model arguments text mein bhejta hai
        try:
            arguments = json.loads(arguments)
        except ValueError:
            return json.dumps({"error": "Arguments must be a JSON object."})
    if not isinstance(arguments, dict):
        return json.dumps({"error": "Arguments must be a JSON object."})
    try:
        result = function(**_keep_known_arguments(function, arguments))
    except TypeError as error:
        return json.dumps({"error": f"Wrong arguments for {name}: {error}"})
    except (ValueError, OSError) as error:
        return json.dumps({"error": str(error)}, ensure_ascii=False)
    except sqlite3.Error as error:
        # Database ki dikkat (lock, disk full): saaf message, bina jawab ke connection band mat karo.
        return json.dumps({"error": f"Database mein dikkat aa gayi ({error}). Thodi der baad dobara bolo."}, ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False, default=str)
