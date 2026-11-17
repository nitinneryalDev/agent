"""Din ka plan code se, bina model ke: "aaj kya hai", "good morning", "is hafte kya pending hai".

Jawab seedha database se banta hai (planner + habits + health), isliye ~5 ms mein aata hai aur kabhi galat
kaam nahi banata (pehle "aaj ke reminders" par model ek naya 'aaj' naam ka reminder tak bana deta tha).
"""
from datetime import datetime, timedelta

import habits
import health
import planner
import replies

_DAY_OFFSETS = {"aaj": 0, "today": 0, "kal": 1, "tomorrow": 1, "parso": 2}
_DAY_NAMES = {0: "Aaj", 1: "Kal", 2: "Parso"}


def _task_line(task):
    tag = f" ({replies.recur_label(task['recurrence'])})" if task.get("recurrence") else ""
    when = f" ({replies.human_time(task['due_at'])})" if task.get("due_at") else ""
    return task["title"] + tag + when


def agenda_text(day_word="aaj", now=None):
    """Us din ke reminders (aaj ho to nikle hue bhi), chhota sa text."""
    now = now or datetime.now()
    offset = _DAY_OFFSETS.get(day_word, 0)
    day = (now.date() + timedelta(days=offset)).isoformat()
    tasks = planner.list_tasks()
    that_day = [t for t in tasks if (t.get("due_at") or "").startswith(day)]
    parts = []
    if offset == 0:
        overdue = [t for t in tasks if t.get("due_at") and t["due_at"] < now.strftime("%Y-%m-%d %H:%M")
                   and not t["due_at"].startswith(day)]
        if overdue:
            parts.append("Nikle hue: " + "; ".join(_task_line(t) for t in overdue[:5]) + ".")
    name = _DAY_NAMES.get(offset, day_word.capitalize())
    if that_day:
        parts.insert(0, f"{name} ke kaam: " + "; ".join(_task_line(t) for t in that_day[:8]) + ".")
    else:
        parts.insert(0, f"{name} koi reminder nahi hai.")
    if offset == 0:
        pending = [h["habit"] for h in habits.habit_status(1) if not h["done_today"]]
        if pending:
            parts.append("Habits baaki: " + ", ".join(pending[:6]) + ".")
        water = health.value_on("hydration")
        if water:
            parts.append(f"Paani: {int(water) if float(water).is_integer() else water} glass.")
    return " ".join(parts)


def week_text(now=None):
    """Agle 7 din ke reminders + nikle hue, ek nazar mein."""
    now = now or datetime.now()
    limit = (now.date() + timedelta(days=7)).isoformat()
    now_text = now.strftime("%Y-%m-%d %H:%M")
    tasks = [t for t in planner.list_tasks() if t.get("due_at")]
    overdue = [t for t in tasks if t["due_at"] < now_text]
    ahead = [t for t in tasks if now_text <= t["due_at"] <= f"{limit} 23:59"]
    no_date = [t for t in planner.list_tasks() if not t.get("due_at")]
    parts = []
    if overdue:
        parts.append("Nikle hue: " + "; ".join(_task_line(t) for t in overdue[:6]) + ".")
    if ahead:
        parts.append("Is hafte: " + "; ".join(_task_line(t) for t in ahead[:8]) + ".")
    if no_date:
        parts.append(f"Bina tareekh ke {len(no_date)} kaam (jaise {no_date[0]['title']}).")
    return " ".join(parts) or "Is hafte koi pending reminder nahi hai."


def morning_text(now=None):
    return "Good morning! " + agenda_text("aaj", now)
