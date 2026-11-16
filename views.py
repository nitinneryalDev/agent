"""Kuch bhi add/update hone ke baad uska table (status ke saath) dikhane ke liye.
Ye model ke bharose nahi: seedha database se padhke table banate hain.
table_data() dashboard ke liye (title, columns, rows), table_for() terminal ke liye (box wala text)."""
import json
import unicodedata

import habits
import health
import planner
import replies
import things
from db import connect


def _width(text):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def render_table(title, columns, rows):
    """Box wala sundar table. rows = list of tuples."""
    if not rows:
        return ""
    cells = [[("" if v is None else str(v)) for v in row] for row in rows]
    widths = [max(_width(c), *(_width(r[i]) for r in cells)) for i, c in enumerate(columns)]

    def line(left, mid, right):
        return left + mid.join("─" * (w + 2) for w in widths) + right

    def row_text(values):
        return "│" + "│".join(f" {v}{' ' * (w - _width(v))} " for v, w in zip(values, widths)) + "│"

    out = [f"\n{title}", line("╭", "┬", "╮"), row_text(columns), line("├", "┼", "┤")]
    out += [row_text(r) for r in cells]
    out.append(line("╰", "┴", "╯"))
    return "\n".join(out)


def _yes(flag):
    return "yes" if flag else "no"


def _habits():
    rows = [(h["habit"], f"{h['streak']} {'day' if h['streak'] == 1 else 'days'}", _yes(h["done_today"]),
             f"{h['done_days']}/{h['out_of_days']}") for h in habits.habit_status(7)]
    return "Habits · last 7 days", ["Habit", "Streak", "Today", "This week"], rows


def _tasks():
    rows = [(t["id"], t["title"] + (f" ({replies.recur_label(t['recurrence'])})" if t.get("recurrence") else ""),
             replies.human_time(t["due_at"]) if t["due_at"] else "-") for t in planner.list_tasks()]
    return "Pending reminders", ["ID", "Reminder", "When"], rows


def _goals():
    rows = [(g["title"], g["target_date"], f"{g['days_left']} days") for g in planner.list_goals()]
    return "Goals", ["Goal", "Target", "Left"], rows


def _health():
    rows = [(health.LABELS.get(s["kind"], s["kind"]), s["average"], s["unit"], s["days_logged"], s["last_day"])
            for s in health.health_summary(7)]
    return "Health · last 7 days", ["Metric", "Average", "Unit", "Days", "Last logged"], rows


def _items():
    with connect() as conn:
        rows = conn.execute("SELECT name, place, updated_at FROM items ORDER BY updated_at DESC LIMIT 15").fetchall()
    return "Where things are", ["Item", "Place", "Updated"], [(r["name"], r["place"], r["updated_at"][:16].replace("T", " ")) for r in rows]


def _contacts():
    with connect() as conn:
        rows = conn.execute(
            "SELECT c.name, c.phone, GROUP_CONCAT(a.alias, ', ') AS nicknames FROM contacts c "
            "LEFT JOIN aliases a ON a.contact_id = c.id GROUP BY c.id ORDER BY c.name"
        ).fetchall()
    return "Contacts", ["Name", "Phone", "Nicknames"], [(r["name"], r["phone"], r["nicknames"]) for r in rows]


def _things():
    rows = []
    for t in things.find_things(limit=15):
        details = ", ".join(f"{k}: {v}" for k, v in t["details"].items())
        rows.append((t["category"], t["name"], t["status"] or "-", t["place"] or "-", details or "-"))
    return "Belongings", ["Type", "Name", "Status", "Place", "Details"], rows


# Kaunsa tool chalne ke baad kaunsa table dikhana hai.
VIEWS = {
    "add_habit": _habits, "check_in_habit": _habits, "habit_status": _habits,
    "add_task": _tasks, "complete_task": _tasks, "list_tasks": _tasks, "reschedule_task": _tasks,
    "add_goal": _goals, "list_goals": _goals,
    "log_health": _health, "health_summary": _health,
    "remember_item": _items,
    "add_contact": _contacts,
    "add_thing": _things, "update_thing": _things,
}


def table_data(tool_name, result_text):
    """Tool kamyab hua ho to {'title', 'columns', 'rows'}, warna None."""
    view = VIEWS.get(tool_name)
    if view is None:
        return None
    try:
        result = json.loads(result_text)
    except ValueError:
        return None
    if not isinstance(result, dict) or "error" in result:
        return None
    title, columns, rows = view()
    if not rows:
        return None
    return {"title": title, "columns": columns, "rows": [["" if v is None else str(v) for v in row] for row in rows]}


def table_for(tool_name, result_text):
    """Terminal ke liye: tool kamyab hua ho to uska table (text), warna khali."""
    data = table_data(tool_name, result_text)
    return render_table(data["title"], data["columns"], data["rows"]) if data else ""
