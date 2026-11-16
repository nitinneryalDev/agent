#!/usr/bin/env python3
"""Assistant ka eval: agent_eval_cases.json ki har line par dekhte hain ki sahi tool chala ya nahi,
arguments sahi the ya nahi, aur kitna time laga.

Chalane ka tareeka:   python3 run_agent_eval.py
Ye ek ALAG temporary database par chalta hai, tumhara assistant.db bilkul nahi chhuta.
Natija agent_eval_results.json mein jata hai, aur dashboard ke System tab mein dikhta hai.
"""
import json
import os
import re
import sys
import tempfile
import time
from datetime import date, datetime, timedelta
from pathlib import Path

# Database ka raasta config import hone se PEHLE badalna zaroori hai.
_TEMP_DIR = tempfile.mkdtemp(prefix="assistant-eval-")
os.environ["ASSISTANT_DB"] = str(Path(_TEMP_DIR) / "eval.db")

import agent  # noqa: E402
import contacts  # noqa: E402
import habits  # noqa: E402
import health  # noqa: E402
import items  # noqa: E402
import planner  # noqa: E402
import things  # noqa: E402
from config import AGENT_EVAL_CASES_FILE, AGENT_EVAL_RESULTS_FILE  # noqa: E402


def seed(stress=False):
    """Kuch pehle se saved data, taaki 'kahan hai' ya 'ho gayi' wale sawalon ka jawab ho.
    stress=True (agent_eval_stress.json ke liye): kuch aur rows jo uske cases maangte hain."""
    today = date.today()
    habits.add_habit("walking")
    habits.add_habit("meditation")
    items.remember_item("passport", "office locker")
    things.add_thing("shoe", "Nike Pegasus", "rack", None, {"color": "black"})
    things.add_thing("book", "Atomic Habits", "shelf 2", "reading", {})
    contacts.add_contact("Mummy", "9876543210", ["mumi", "maa"])
    planner.add_task("bijli ka bill bharna", f"{today.isoformat()} 20:00")
    planner.add_task("doodh lena", f"{(today + timedelta(days=1)).isoformat()} 18:00")
    planner.add_task("gas cylinder book karna", None if stress else f"{(today + timedelta(days=1)).isoformat()} 11:00")
    planner.add_goal("Marathon daudna", "2027-03-01")
    health.log_health("sleep", 7)
    if stress:
        habits.add_habit("reading")
        for days_ago in (1, 2, 4):  # walking: streak 2, is hafte 3/7
            habits.check_in("walking", (today - timedelta(days=days_ago)).isoformat())
        items.remember_item("umbrella", "chhata stand")
        planner.add_task("dentist appointment", f"{(today + timedelta(days=2)).isoformat()} 10:00")
        contacts.add_contact("Rahul", "9812345678", [])
        health.log_health("hydration", 4)


def fill(text):
    today = date.today()
    out = (str(text).replace("<TODAY>", today.isoformat())
           .replace("<TOMORROW>", (today + timedelta(days=1)).isoformat())
           .replace("<DAYAFTER>", (today + timedelta(days=2)).isoformat())
           .replace("<YESTERDAY>", (today - timedelta(days=1)).isoformat())
           .replace("<THISYEAR>", str(today.year))
           .replace("<NEXTYEAR>", str(today.year + 1)))
    def _nextmonth(match):
        day = int(match.group(1))
        year, month = today.year + (1 if today.month == 12 else 0), (today.month % 12) + 1
        return date(year, month, min(day, 28)).isoformat()
    out = re.sub(r"<NEXTMONTH:(\d{1,2})>", _nextmonth, out)
    def _weekday(match):
        ahead = (int(match.group(1)) - today.weekday()) % 7 or 7
        return (today + timedelta(days=ahead)).isoformat()
    out = re.sub(r"<WEEKDAY:(\d)>", _weekday, out)
    def _next_time(match):
        hour, minute = int(match.group(1)), int(match.group(2))
        now = datetime.now()
        day = today if (hour, minute) > (now.hour, now.minute) else today + timedelta(days=1)
        return f"{day.isoformat()} {hour:02d}:{minute:02d}"
    out = re.sub(r"<NEXT:(\d{2}):(\d{2})>", _next_time, out)
    return out


def args_match(expected, actual):
    for key, want in expected.items():
        got = actual.get(key)
        if isinstance(want, (int, float)):
            try:
                if float(got) != float(want):
                    return False
            except (TypeError, ValueError):
                return False
        elif fill(str(want)).lower() not in str(got).lower():
            return False
    return True


def judge(case, calls, reply):
    """(pass?, wajah) deta hai."""
    wanted = case["tools"]
    if not wanted:
        return (not calls, "koi tool nahi chalna tha" if calls else "")
    matching = [c for c in calls if c["name"] in wanted]
    if not matching:
        return False, "galat tool"
    if case.get("args") and not any(args_match(case["args"], c["arguments"]) for c in matching):
        return False, "arguments galat"
    if case.get("args_absent") and any(c["arguments"].get(k) for c in matching for k in case["args_absent"]):
        return False, f"{case['args_absent']} nahi hona chahiye tha (user ne bola hi nahi)"
    if any("error" in c["result"] for c in matching):
        return False, "tool ne error diya"
    if case.get("reply_has") and case["reply_has"].lower() not in reply.lower():
        return False, f"jawab mein '{case['reply_has']}' nahi"
    if case.get("reply_any") and not any(word.lower() in reply.lower() for word in case["reply_any"]):
        return False, f"jawab mein {case['reply_any']} mein se kuch nahi"
    strict = case.get("strict") or {}
    for spec in strict.get("calls", []):  # multi-intent: YE saare calls hone chahiye (sirf ek nahi)
        if not any(c["name"] == spec["name"] and args_match(spec.get("args", {}), c["arguments"]) for c in calls):
            return False, f"missing call {spec['name']} {spec.get('args')}"
    for word in strict.get("reply_not_has", []):
        if word.lower() in reply.lower():
            return False, f"jawab mein '{word}' nahi hona chahiye tha"
    for field, word in (strict.get("arg_not_has") or {}).items():
        if any(str(word).lower() in str(c["arguments"].get(field, "")).lower() for c in matching):
            return False, f"{field} mein '{word}' nahi hona chahiye tha"
    return True, ""


def _tasks_like(word):
    return [t for t in planner.list_tasks() if word.lower() in t["title"].lower()]


def _checked_in(habit, day):
    from db import connect
    with connect() as conn:
        row = conn.execute("SELECT 1 FROM habit_checkins c JOIN habits h ON h.id = c.habit_id "
                           "WHERE h.name = ? COLLATE NOCASE AND c.day = ?", (habit, day)).fetchone()
    return row is not None


def check_db(check):
    """Case ke baad database sach mein waisa hai? (jaise 'haan' ke baad task sach mein hata,
    reschedule ke baad due sach mein badla, recurrence sach mein store hui)"""
    titles = [t["title"].lower() for t in planner.list_tasks()]
    for key, value in (check or {}).items():
        if key == "task_absent" and any(value.lower() in t for t in titles):
            return False, f"'{value}' wala task abhi bhi hai"
        if key == "task_present" and not any(value.lower() in t for t in titles):
            return False, f"'{value}' wala task hat gaya (nahi hatna tha)"
        if key == "item_absent" and items.find_item(value.lower()):
            return False, f"'{value}' entry abhi bhi hai"
        if key == "habit_present" and not any(h["habit"] == value.lower() for h in habits.habit_status()):
            return False, f"'{value}' habit hat gayi (nahi hatni thi)"
        if key == "habit_absent" and any(h["habit"].lower() == value.lower() for h in habits.habit_status()):
            return False, f"'{value}' habit abhi bhi hai"
        if key == "task_due":
            for word, want in value.items():
                want = fill(want)
                rows = _tasks_like(word)
                if not rows:
                    return False, f"'{word}' wala task mila hi nahi"
                if not any((t["due_at"] or "").startswith(want) for t in rows):
                    return False, f"'{word}' ka due {rows[0]['due_at']} hai, chahiye tha {want}"
        if key == "task_count":
            for word, want in value.items():
                if len(_tasks_like(word)) != int(want):
                    return False, f"'{word}' wale {len(_tasks_like(word))} task hain, chahiye the {want}"
        if key == "task_recurrence":
            for word, want in value.items():
                if not any(t.get("recurrence") == want for t in _tasks_like(word)):
                    return False, f"'{word}' ki recurrence {want} nahi hai"
        if key == "task_due_within_any":
            for word, (minutes, tolerance) in value.items():
                rows = [t for t in _tasks_like(word) if t.get("due_at")]
                target = datetime.now() + timedelta(minutes=minutes)
                ok = any(abs((datetime.strptime(t["due_at"], "%Y-%m-%d %H:%M") - target).total_seconds()) <= tolerance * 60
                         for t in rows)
                if not ok:
                    return False, f"'{word}' ka due ab se ~{minutes} min par nahi hai"
        if key == "checkin_day":
            for habit, day in value.items():
                if not _checked_in(habit, fill(day)):
                    return False, f"{habit} ki {fill(day)} ki check-in nahi hui"
        if key == "checkin_absent":
            for habit, day in value.items():
                if _checked_in(habit, fill(day)):
                    return False, f"{habit} ki {fill(day)} ki check-in NAHI honi chahiye thi"
        if key == "health_today":
            for kind, want in value.items():
                got = health.value_on(kind)
                if got is None or float(got) != float(want):
                    return False, f"aaj ka {kind} {got} hai, chahiye tha {want}"
        if key == "item_place":
            for name, place in value.items():
                rows = items.find_item(name)
                if not any(place.lower() in r["place"].lower() for r in rows):
                    return False, f"'{name}' ki jagah '{place}' nahi mili"
        if key == "thing_any":
            for name, words in value.items():
                rows = things.find_things(query=name)
                blob = json.dumps(rows, ensure_ascii=False, default=str).lower()
                if not any(w.lower() in blob for w in words):
                    return False, f"'{name}' mein {words} mein se kuch nahi"
        if key == "contact_phone":
            for name, phone in value.items():
                found = contacts.find_contact(name)
                if not found or found["phone"] != phone:
                    return False, f"{name} ka number {phone} nahi hai"
    return True, ""


def run_turn_checked(history, turn):
    calls, info = [], {}

    def remember(name, arguments, result):
        try:
            parsed = json.loads(result)
        except ValueError:
            parsed = {}
        calls.append({"name": name, "arguments": arguments if isinstance(arguments, dict) else {}, "result": parsed})

    started = time.perf_counter()
    try:
        reply = agent.run_turn(history, turn["text"], on_tool=remember, info=info)
    except TypeError:  # purana agent jo info nahi leta
        reply = agent.run_turn(history, turn["text"], on_tool=remember)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    ok, why = judge(turn, calls, reply)
    return ok, why, elapsed_ms, info.get("route", "model"), [c["name"] for c in calls], reply


def run_case(case):
    """Ek line wala case, ya "turns" wala (jaise: 'hata do' -> 'haan'), ek hi baat-cheet mein."""
    turns = case.get("turns") or [case]
    history, total_ms, tools, routes = [], 0, [], []
    ok, why, reply = True, "", ""
    for number, turn in enumerate(turns, start=1):
        turn_ok, turn_why, ms, route, turn_tools, reply = run_turn_checked(history, turn)
        total_ms += ms
        tools += turn_tools or ["-"]
        routes.append(route)
        if not turn_ok and ok:
            ok, why = False, (f"turn {number}: {turn_why}" if len(turns) > 1 else turn_why)
    if ok:
        ok, why = check_db(case.get("check"))
    text = " -> ".join(t["text"] for t in turns)
    return {"text": text, "ok": ok, "why": why, "ms": total_ms, "route": "/".join(routes),
            "tools": [t for t in tools if t != "-"] if len(turns) == 1 else tools, "reply": reply}


def reset_db(stress):
    """--fresh-db: har case apne hi database par (stress cases ek doosre ka data kha jate hain)."""
    for suffix in ("", "-wal", "-shm"):
        Path(os.environ["ASSISTANT_DB"] + suffix).unlink(missing_ok=True)
    seed(stress=stress)


def main():
    # Alag file do to (jaise naye, pehle na dekhe sawal) sirf natija dikhao, dashboard wali file mat badlo.
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    files = [a for a in sys.argv[1:] if not a.startswith("--")]
    custom = Path(files[0]) if files else None
    fresh = "--fresh-db" in flags or (custom and "stress" in custom.name)
    stress = bool(custom and "stress" in custom.name)
    cases = json.loads((custom or AGENT_EVAL_CASES_FILE).read_text(encoding="utf-8"))
    seed(stress=stress)
    if hasattr(agent, "warm_up"):
        agent.warm_up()  # model pehle se memory mein ho, taaki pehla case dheema na dikhe
    results = []
    for case in cases:
        if fresh:
            reset_db(stress)
        try:
            result = run_case(case)
        except OSError:
            print("Ollama se connect nahi ho paya. Ollama app kholo aur dobara chalao.")
            sys.exit(1)
        results.append(result)
        mark = "PASS" if result["ok"] else "FAIL"
        tools = ", ".join(result["tools"]) or "-"
        print(f"{mark}  {result['ms']:>6} ms  {result['route']:<8}  {result['text']:<55} -> {tools}")
        if not result["ok"]:
            print(f"      wajah: {result['why']}. Jawab: {result['reply'][:120]!r}")
    correct = sum(r["ok"] for r in results)
    times = sorted(r["ms"] for r in results)
    summary = {
        "correct": correct,
        "total": len(results),
        "avg_ms": round(sum(times) / len(times)),
        "p50_ms": times[len(times) // 2],
        "ran_at": time.strftime("%Y-%m-%d %H:%M"),
        "cases": results,
    }
    if custom is None:
        AGENT_EVAL_RESULTS_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nScore: {correct} of {len(results)} ({round(100 * correct / len(results))}%)."
          f"  Average {summary['avg_ms']} ms, median {summary['p50_ms']} ms.")


if __name__ == "__main__":
    main()
