"""Tool chalne ke baad user ko kya bolna hai: ye code khud likhta hai, model nahi.

Kyun:
  - Tez: save/dhundhne ke baad model ko dobara bulane ki zaroorat nahi (ek call kam = aadha intezaar).
  - Sach: jawab sirf database ke natije se banta hai, model kuch "bana" nahi sakta.
Sirf search_notes ka jawab model likhta hai (notes padhkar samjhana padta hai).
"""
from datetime import date, datetime, timedelta

import health
from config import REMINDER_DAY_TIME

_DAY_PARTS = ((5, "subah"), (12, "dopahar"), (16, "shaam"), (20, "raat"))
_RECUR_LABEL = {"daily": "roz", "weekly": "har hafte", "monthly": "har mahine", "yearly": "har saal"}
_WEEKDAY_HINDI = ["somvar", "mangalvar", "budhvar", "guruvar", "shukravar", "shanivar", "ravivar"]


def recur_label(recurrence):
    """'daily' -> 'roz', 'weekly:0' -> 'har somvar'. Anjaan ho to wahi text."""
    if not recurrence:
        return ""
    if recurrence.startswith("weekly:"):
        try:
            return f"har {_WEEKDAY_HINDI[int(recurrence.split(':')[1])]}"
        except (ValueError, IndexError):
            return "har hafte"
    return _RECUR_LABEL.get(recurrence, recurrence)


def human_time(value):
    """'2026-11-08 18:00' -> 'kal shaam 6:00 baje'. Galat ho to wahi text wapas."""
    try:
        moment = datetime.strptime(value, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return value or ""
    today = date.today()
    day = moment.date()
    names = {today: "aaj", today + timedelta(days=1): "kal", today + timedelta(days=2): "parso",
             today - timedelta(days=1): "kal (beeta)"}
    day_text = names.get(day, moment.strftime("%d %b"))
    if moment.hour == 23 and moment.minute == 59:
        return day_text  # sirf tareekh di thi
    part = "raat"
    for start, name in _DAY_PARTS:
        if moment.hour >= start:
            part = name
    hour12 = moment.hour % 12 or 12
    return f"{day_text} {part} {hour12}:{moment.minute:02d} baje"


def _items_line(rows):
    return "; ".join(f"{r['name']} {r['place']} mein hai" for r in rows[:5]) + "."


def _things_line(rows):
    parts = []
    for t in rows[:5]:
        about = [str(v) for v in (t.get("details") or {}).values()] + ([t["status"]] if t.get("status") else [])
        name = f"{t['name']} ({', '.join(about)})" if about else t["name"]
        parts.append(f"{name} {t['place']} mein hai" if t.get("place") else f"{name}, jagah save nahi hai")
    more = f" Aur {len(rows) - 5} aur hain." if len(rows) > 5 else ""
    return "; ".join(parts) + "." + more


def reply_for(name, arguments, data):
    """Tool ke natije se ek chhota Hinglish jawab. None = model ko likhne do (jaise search_notes)."""
    if "say" in data:
        return data["say"]
    if name == "add_habit":
        return f"Nayi habit shuru: {data['name']}. Roz '{data['name']} ho gayi' bolke check-in karna."
    if name == "check_in_habit":
        when = "" if data["day"] == date.today().isoformat() else f" ({data['day']} ke liye)"
        return f"{data['habit'].capitalize()} ho gayi{when}! Streak: {data['streak']} din."
    if name == "habit_status":
        rows = data["habits"]
        if not rows:
            return "Abhi koi habit nahi hai. 'walking naam ki habit shuru karo' bolkar shuru karo."
        parts = [f"{h['habit']}: {h['streak']} din streak, is hafte {h['done_days']}/{h['out_of_days']}, "
                 f"aaj {'ho gayi' if h['done_today'] else 'baaki'}" for h in rows]
        return "; ".join(parts) + "."
    if name == "add_task":
        when = f", {human_time(data['due'])}" if data.get("due") else ""
        extra = f" ({recur_label(data['recurrence'])})" if data.get("recurrence") else ""
        note = ""
        if data.get("due", "") and str(data["due"]).endswith("23:59"):
            hour = int(REMINDER_DAY_TIME[:2])
            note = f" Us din subah {hour} baje yaad dila dunga."
        return f"Yaad rakhunga: {data['title']}{extra}{when}.{note}"
    if name == "reschedule_task":
        return f"Badal diya: {data['title']}, ab {human_time(data['due'])}."
    if name == "list_tasks":
        rows = data["tasks"]
        if not rows:
            return "Koi pending kaam nahi hai."
        parts = []
        for t in rows[:6]:
            tag = f" ({recur_label(t['recurrence'])})" if t.get("recurrence") else ""
            when = f" ({human_time(t['due_at'])})" if t.get("due_at") else ""
            parts.append(t["title"] + tag + when)
        return f"{len(rows)} pending kaam: " + "; ".join(parts) + "."
    if name == "complete_task":
        return f"Done! '{data['title']}' ho gaya."
    if name == "add_goal":
        return f"Goal save ho gaya: {data['title']} (target {data['target_date']})."
    if name == "list_goals":
        rows = data["goals"]
        if not rows:
            return "Abhi koi goal saved nahi hai."
        return "; ".join(f"{g['title']}: {g['days_left']} din baaki" for g in rows) + "."
    if name == "log_health":
        label = health.LABELS.get(data["kind"], data["kind"])
        value = int(data["value"]) if float(data["value"]).is_integer() else data["value"]
        when = "" if data["day"] == date.today().isoformat() else f" ({data['day']})"
        return f"{label} log ho gaya: {value} {data['unit']}{when}."
    if name == "health_summary":
        rows = data["summary"]
        if not rows:
            return "Is hafte ka koi health log nahi hai."
        return "; ".join(f"{health.LABELS.get(r['kind'], r['kind'])}: average {r['average']} {r['unit']} "
                         f"({r['days_logged']} din)" for r in rows) + "."
    if name == "add_thing":
        details = ", ".join(str(v) for v in data.get("details", {}).values())
        where = f", {data['place']} mein" if data.get("place") else ""
        status = f", status: {data['status']}" if data.get("status") else ""
        return f"Save ho gaya: {data['name']} ({data['category']}{f', {details}' if details else ''}){where}{status}."
    if name == "update_thing":
        changes = [f"status {data['status']}" if arguments.get("status") else "",
                   f"jagah {data['place']}" if arguments.get("place") else ""]
        changed = ", ".join(c for c in changes if c)
        return f"Update ho gaya: {data['name']}{f' ({changed})' if changed else ''}."
    if name == "find_things":
        return _things_line(data["things"])
    if name == "remember_item":
        before = data.get("previous_place")
        moved = f" (pehle {before} mein thi)" if before and before.lower() != data["place"].lower() else ""
        return f"Yaad rakh liya: {data['item']} {data['place']} mein hai{moved}."
    if name == "find_item":
        if data.get("matches"):
            return _items_line(data["matches"])
        return _things_line(data.get("things", []))
    if name == "add_contact":
        nick = f" (nicknames: {', '.join(data['nicknames'])})" if data.get("nicknames") else ""
        return f"Contact save ho gaya: {data['name']}, {data['phone']}{nick}."
    if name == "call_contact":
        contact = data["contact"]
        return f"{contact['name']} ka number: {contact['phone']}. Is laptop se asli call nahi lagti, phone se laga lo."
    return None
