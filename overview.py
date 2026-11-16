"""Dashboard ke 'My data' aur 'Aaj' hisse ke liye saara data ek hi jagah se (seedha database se, model nahi)."""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

import habits
import health
import planner
import replies
import things
from db import connect

GRID_DAYS = 14
HEALTH_LABELS = {"hydration": "Water", "sleep": "Sleep", "training": "Training", "mobility": "Mobility", "energy": "Energy"}


def _best_streak(days):
    best = run = 0
    previous = None
    for day in sorted(days):
        run = run + 1 if previous and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return best


def _habits():
    today = date.today()
    first = today - timedelta(days=GRID_DAYS - 1)
    with connect() as conn:
        rows = conn.execute("SELECT id, name FROM habits ORDER BY name").fetchall()
        checkins = conn.execute("SELECT habit_id, day FROM habit_checkins").fetchall()
    done = defaultdict(set)
    for row in checkins:
        done[row["habit_id"]].add(date.fromisoformat(row["day"]))
    result = []
    for habit in rows:
        days = done[habit["id"]]
        grid = [{"day": (first + timedelta(days=i)).isoformat(), "done": first + timedelta(days=i) in days}
                for i in range(GRID_DAYS)]
        result.append({
            "id": habit["id"],
            "name": habit["name"],
            "streak": habits.compute_streak(days, today),
            "best": _best_streak(days),
            "done_today": today in days,
            "done_7": sum(1 for d in days if today - timedelta(days=6) <= d <= today),
            "total": len(days),
            "grid": grid,
        })
    return result


def _tasks():
    now = datetime.now()
    pending = []
    for task in planner.list_tasks():
        status = "none"
        if task["due_at"]:
            due = datetime.strptime(task["due_at"], "%Y-%m-%d %H:%M")
            if due < now:
                status = "overdue"
            elif due.date() == now.date():
                status = "today"
            elif due.date() == now.date() + timedelta(days=1):
                status = "tomorrow"
            else:
                status = "later"
        pending.append({**task, "status": status, "when": replies.human_time(task["due_at"]) if task["due_at"] else ""})
    with connect() as conn:
        done = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
    return {
        "pending": pending,
        "done": done,
        "overdue": sum(t["status"] == "overdue" for t in pending),
        "today": sum(t["status"] == "today" for t in pending),
    }


def _goals():
    today = date.today()
    result = []
    for goal in planner.list_goals():
        created = datetime.fromisoformat(goal["created_at"]).date()
        target = date.fromisoformat(goal["target_date"])
        total = max((target - created).days, 1)
        elapsed = min(max((today - created).days, 0), total)
        result.append({**goal, "progress": round(100 * elapsed / total)})
    return result


def _health():
    today = date.today()
    first = today - timedelta(days=GRID_DAYS - 1)
    with connect() as conn:
        rows = conn.execute("SELECT day, kind, value FROM health_logs WHERE day >= ?", (first.isoformat(),)).fetchall()
    by_kind = defaultdict(dict)
    for row in rows:
        by_kind[row["kind"]][row["day"]] = row["value"]
    result = []
    for kind, unit in health.KINDS.items():
        values = by_kind.get(kind, {})
        series = [values.get((first + timedelta(days=i)).isoformat()) for i in range(GRID_DAYS)]
        week = [v for v in series[-7:] if v is not None]
        result.append({
            "kind": kind, "label": HEALTH_LABELS.get(kind, kind), "unit": unit,
            "today": values.get(today.isoformat()),
            "avg_7": round(sum(week) / len(week), 1) if week else None,
            "days_7": len(week), "series": series,
        })
    return result


def _things():
    rows = things.find_things(limit=100)
    counts = Counter(t["category"] for t in rows)
    return {"list": rows, "categories": [{"name": name, "count": count} for name, count in counts.most_common()]}


def _items():
    with connect() as conn:
        rows = conn.execute("SELECT name, place, updated_at FROM items ORDER BY updated_at DESC LIMIT 100").fetchall()
    return [dict(row) for row in rows]


def _contacts():
    with connect() as conn:
        rows = conn.execute(
            "SELECT c.id, c.name, c.phone, GROUP_CONCAT(a.alias, ', ') AS nicknames FROM contacts c "
            "LEFT JOIN aliases a ON a.contact_id = c.id GROUP BY c.id ORDER BY c.name"
        ).fetchall()
    return [dict(row) for row in rows]


def build_overview():
    today = date.today()
    data = {
        "today": today.isoformat(),
        "today_label": today.strftime("%A, %d %B"),
        "habits": _habits(),
        "tasks": _tasks(),
        "goals": _goals(),
        "health": _health(),
        "things": _things(),
        "items": _items(),
        "contacts": _contacts(),
    }
    data["counts"] = {
        "habits": len(data["habits"]),
        "habits_done_today": sum(h["done_today"] for h in data["habits"]),
        "best_streak": max((h["streak"] for h in data["habits"]), default=0),
        "tasks_pending": len(data["tasks"]["pending"]),
        "tasks_overdue": data["tasks"]["overdue"],
        "goals": len(data["goals"]),
        "things": len(data["things"]["list"]),
        "items": len(data["items"]),
        "contacts": len(data["contacts"]),
    }
    return data
