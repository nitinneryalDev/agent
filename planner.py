"""Kaam (tasks), reminders aur goals."""
import re
import subprocess
from datetime import datetime, timedelta

import when
from config import REMINDER_DAY_TIME
from db import connect

DATETIME_FORMAT = "%Y-%m-%d %H:%M"
DATE_FORMAT = "%Y-%m-%d"


def _now_text():
    return datetime.now().isoformat(timespec="seconds")


def parse_due(text):
    """'2026-11-10 18:30' ya sirf '2026-11-10' ko ek hi format mein badlo. Galat ho to ValueError."""
    text = str(text).strip().replace("T", " ")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text):
        text = text[:16]  # seconds bhi aa gaye to hata do
    for fmt in (DATETIME_FORMAT, DATE_FORMAT):
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if fmt == DATE_FORMAT:
            parsed = parsed.replace(hour=23, minute=59)  # sirf tareekh di to din ke ant tak
        return parsed.strftime(DATETIME_FORMAT)
    today = datetime.now().strftime(DATE_FORMAT)
    raise ValueError(f"Tareekh aise likho: poori date ke saath, jaise '{today} 18:30' (aaj = {today}). Retry with the full YYYY-MM-DD HH:MM.")


def add_task(title, due=None, recurrence=None):
    """Naya kaam jodo. due do to wo reminder bhi ban jata hai. Kaam ki id wapas deta hai."""
    title = title.strip()
    if not title:
        raise ValueError("Kaam ka naam chahiye.")
    due_at = parse_due(due) if due and str(due).strip() else None
    if not recurrence:
        recurrence = when.parse_recurrence(title)
    with connect() as conn:
        return conn.execute(
            "INSERT INTO tasks (title, due_at, created_at, recurrence) VALUES (?, ?, ?, ?)",
            (title, due_at, _now_text(), recurrence),
        ).lastrowid


def list_tasks(include_done=False):
    """Baaki kaam, jaldi wale pehle. Bina tareekh wale sabse neeche."""
    where = "" if include_done else "WHERE done = 0"
    with connect() as conn:
        rows = conn.execute(
            f"SELECT id, title, due_at, done, recurrence FROM tasks {where} ORDER BY due_at IS NULL, due_at, id"
        ).fetchall()
    return [dict(row) for row in rows]


def _step(moment, recurrence):
    """Recurrence ka ek kadam aage: daily +1 din, weekly +7, monthly agla mahina, yearly agla saal."""
    if recurrence and recurrence.startswith("weekly"):
        return moment + timedelta(days=7)
    if recurrence == "monthly":
        year = moment.year + (1 if moment.month == 12 else 0)
        month = 1 if moment.month == 12 else moment.month + 1
        for day in (moment.day, 30, 29, 28):  # 31 tareekh wale mahine ke baad chhota mahina aaye to pichhla din
            try:
                return moment.replace(year=year, month=month, day=day)
            except ValueError:
                continue
    if recurrence == "yearly":
        try:
            return moment.replace(year=moment.year + 1)
        except ValueError:  # 29 Feb
            return moment.replace(year=moment.year + 1, day=28)
    return moment + timedelta(days=1)  # daily (aur anjaan recurrence bhi daily jaisa)


def _next_due(current_due_text, recurrence, now=None):
    """Recurring task ka agla (future) time."""
    now = now or datetime.now()
    try:
        base = datetime.strptime(current_due_text, DATETIME_FORMAT)
    except (ValueError, TypeError):
        base = now
    nxt = _step(base, recurrence)
    while nxt <= now:
        nxt = _step(nxt, recurrence)
    return nxt.strftime(DATETIME_FORMAT)


def _latest_not_after(base, recurrence, now):
    """base se shuru karke wo aakhri occurrence jo `now` tak aa chuki hai (reminder dobara bajane ke liye)."""
    current = base
    while True:
        following = _step(current, recurrence)
        if following > now:
            return current
        current = following


def complete_task(task_id):
    """Kaam ho gaya mark karo. Agar recurring hai to agle din/hafte par set karo."""
    try:
        task_id = int(task_id)
    except (TypeError, ValueError):
        raise ValueError("task_id number honi chahiye.")
    with connect() as conn:
        row = conn.execute("SELECT id, title, due_at, recurrence FROM tasks WHERE id = ? AND done = 0", (task_id,)).fetchone()
        if not row:
            return False
        if row["recurrence"]:
            nxt_due = _next_due(row["due_at"], row["recurrence"])
            conn.execute("UPDATE tasks SET due_at = ?, notified = 0 WHERE id = ?", (nxt_due, task_id))
            return True
        return conn.execute("UPDATE tasks SET done = 1 WHERE id = ? AND done = 0", (task_id,)).rowcount > 0


def notify_desktop(title, message, sound="Glass"):
    """macOS desktop notification. Title/message argv se jaate hain, AppleScript source mein NAHI jude:
    naam mein `"`, `\\` ya 'do shell script' ho to bhi wo sirf text ki tarah dikhta hai, chalta kuch nahi.
    Fail hua (permission band, osascript error) to False, taaki reminder kho na jaye aur dobara try ho."""
    script = ('on run argv\n'
              f'display notification (item 2 of argv) with title (item 1 of argv) sound name "{sound}"\n'
              'end run')
    try:
        proc = subprocess.run(["osascript", "-e", script, str(title), str(message)],
                              timeout=5, capture_output=True, check=False)
        return proc.returncode == 0
    except Exception:
        return False


def _late_note(due_text, now):
    """15 min se zyada der se pahuncha reminder bata de ki kab ka tha."""
    try:
        due = datetime.strptime(due_text, DATETIME_FORMAT)
    except (ValueError, TypeError):
        return ""
    if due_text.endswith("23:59") or (now - due) <= timedelta(minutes=15):
        return ""
    return f" ({due_text[11:16]} ka tha)"


def check_and_notify_due_tasks(now=None):
    """Due tasks par desktop notification. Teen niyam:
    1. Recurring task jiska waqt nikal gaya use aaj ki aakhri occurrence par laao aur notified=0 karo,
       taaki wo DOBARA baje (pehle ek baar bajkar hamesha ke liye chup ho jata tha).
    2. Bina samay wale reminder (23:59 convention) us din subah REMINDER_DAY_TIME par bajte hain, 23:59 par nahi.
    3. Pehle claim (notified=1 sirf tab jab 0 tha), phir notification; fail ho to notified wapas 0 (retry hogi,
       aur do checker ek saath chalein to bhi ek hi notification jati hai)."""
    now = now or datetime.now()
    now_text = now.strftime(DATETIME_FORMAT)
    sent = 0
    with connect() as conn:
        # 1. Recurring: beeti hui occurrences ko aaj tak le aao.
        rows = conn.execute(
            "SELECT id, due_at, recurrence FROM tasks WHERE done = 0 AND recurrence IS NOT NULL "
            "AND due_at IS NOT NULL AND due_at <= ?", (now_text,)).fetchall()
        for row in rows:
            try:
                base = datetime.strptime(row["due_at"], DATETIME_FORMAT)
            except (ValueError, TypeError):
                continue
            latest = _latest_not_after(base, row["recurrence"], now)
            if latest > base:
                conn.execute("UPDATE tasks SET due_at = ?, notified = 0 WHERE id = ?",
                             (latest.strftime(DATETIME_FORMAT), row["id"]))
        # 2. Ab jo due hain: samay wale apne samay par, date-only (23:59) wale subah ke alert time se.
        rows = conn.execute(
            "SELECT id, title, due_at FROM tasks WHERE done = 0 AND notified = 0 AND due_at IS NOT NULL AND ("
            "  (due_at NOT LIKE '% 23:59' AND due_at <= ?)"
            "  OR (due_at LIKE '% 23:59' AND substr(due_at, 1, 10) || ? <= ?) )",
            (now_text, f" {REMINDER_DAY_TIME}", now_text)).fetchall()
        due = [dict(row) for row in rows]
        claimed = [row for row in due
                   if conn.execute("UPDATE tasks SET notified = 1 WHERE id = ? AND notified = 0",
                                   (row["id"],)).rowcount == 1]
        if len(claimed) > 3:  # dashboard der se khula: ek hi summary, 6-7 alag pop-up nahi
            titles = "; ".join(row["title"] for row in claimed[:6])
            if notify_desktop("Assistant Reminder", f"{len(claimed)} reminders due: {titles}"):
                sent = len(claimed)
            else:
                for row in claimed:
                    conn.execute("UPDATE tasks SET notified = 0 WHERE id = ?", (row["id"],))
        else:
            for row in claimed:
                if notify_desktop("Assistant Reminder", row["title"] + _late_note(row["due_at"], now)):
                    sent += 1
                else:
                    conn.execute("UPDATE tasks SET notified = 0 WHERE id = ?", (row["id"],))
    return sent


def last_notified_task():
    """Sabse haal mein baja hua (par done nahi hua) reminder: "snooze" isi par lagta hai."""
    with connect() as conn:
        row = conn.execute("SELECT id, title, due_at FROM tasks WHERE done = 0 AND notified = 1 "
                           "AND due_at IS NOT NULL ORDER BY due_at DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def reschedule_task(task_id, due):
    """Pending kaam ka samay badlo (snooze/shift). notified wapas 0: naye samay par phir bajega."""
    due_at = parse_due(due)
    with connect() as conn:
        row = conn.execute("SELECT id, title FROM tasks WHERE id = ? AND done = 0", (int(task_id),)).fetchone()
        if not row:
            raise ValueError("Ye kaam pending list mein nahi mila.")
        conn.execute("UPDATE tasks SET due_at = ?, notified = 0 WHERE id = ?", (due_at, row["id"]))
        return {"task_id": row["id"], "title": row["title"], "due": due_at}


_TASK_FILLER = {"wala", "wali", "wale", "kaam", "task", "ka", "kaa", "ki", "ke", "ko", "ho", "gaya", "gayi", "done",
                "mera", "meri", "mere", "aaj", "ab", "the", "my", "complete", "kar", "karo", "diya", "liya", "li", "do",
                "reminder", "yaad", "dila", "dilao", "dilana", "dilane", "dilanae", "hata", "hataa", "hatao", "hatado",
                "delete", "remove", "cancel", "kal", "parso", "sham", "shaam", "subah", "raat", "dopahar", "baje",
                "wo", "vo", "ye", "is", "us", "mujhe", "please", "entry",
                "jagah", "pe", "par", "shift", "badal", "badlo", "samay", "time", "snooze", "phir", "dobara", "baad",
                "dena", "dedo", "karna", "karne", "hai", "hain", "h", "usko", "isko", "use", "aaj"}


def find_open_task(text):
    """Pending kaam ko id ya naam ke kuch shabdon se dhundho ("bijli ka bill" -> "bijli ka bill bharna").
    Ek hi mile to wo row, warna ValueError (saaf wajah ke saath)."""
    text = str(text or "").strip()
    if not text:
        raise ValueError("Kaunsa kaam? Naam ya id batao.")
    with connect() as conn:
        if text.isdigit():
            row = conn.execute("SELECT id, title, due_at FROM tasks WHERE id = ? AND done = 0", (int(text),)).fetchone()
            if row is None:
                raise ValueError(f"Id {text} wala koi pending kaam nahi mila.")
            return dict(row)
        words = [w for w in re.findall(r"\w+", text.lower()) if w not in _TASK_FILLER] or [text.lower()]
        rows = conn.execute("SELECT id, title, due_at FROM tasks WHERE done = 0").fetchall()
    scored = [(sum(w in row["title"].lower() for w in words), row) for row in rows]
    best = max((score for score, _ in scored), default=0)
    matches = [dict(row) for score, row in scored if score == best and best > 0]
    if not matches:
        raise ValueError(f"'{text}' jaisa koi pending kaam nahi mila.")
    if len(matches) > 1:
        raise ValueError("Kai kaam milte hain: " + ", ".join(m["title"] for m in matches[:5]) + ". Thoda aur saaf batao.")
    return matches[0]


def delete_task(task_id, title):
    """Kaam hamesha ke liye hatao. Sirf tab bulana jab user ne pakka 'haan' bola ho.
    id ke saath naam bhi milna chahiye: SQLite hatayi gayi id agle naye kaam ko de deta hai, to purani id
    akeli kisi doosre kaam ko hata sakti hai."""
    with connect() as conn:
        return conn.execute("DELETE FROM tasks WHERE id = ? AND title = ?", (int(task_id), title)).rowcount > 0


_TITLE_NOISE = re.compile(
    r"\b(?:yaad\s+(?:dila\w*|kara\w*)(?:\s+(?:do|dena|dijiye))?|remind\w*(?:\s+me)?|reminder|"
    r"(?:sava|sawa|sadhe|saadhe|sade|saade|paune)\s+\w+\s+baje|\d{1,2}(?:[:.]\d{2})?\s*(?:baje|bje|am|pm)|"
    r"kal|aaj|parso|perso|tomorrow|today|tonight|subah|savere|dopahar|shaam|sham|raat|baje|please|plz)\b",
    re.IGNORECASE)


def clean_title(title):
    """Kaam ke naam se samay aur 'yaad dilana' jaise shabd hatao: 'dentist subah 10 baje yaad dilana' -> 'dentist'.
    Sab kuch hi hat jaye to asli naam wapas."""
    text = _TITLE_NOISE.sub(" ", str(title))
    words = text.split()
    while words and words[0].lower() in {"mujhe", "mera", "meri", "mere", "ko", "ka", "ki", "ke", "ki"}:
        words.pop(0)
    while words and words[-1].lower() in {"ko", "ka", "ki", "ke", "hai", "h", "hain", "wala", "wali", "do", "ka samay"}:
        words.pop()
    cleaned = " ".join(words).strip(" ,.-")
    return cleaned if len(cleaned) >= 3 else str(title).strip()


def due_soon(hours=24):
    """Aane wale `hours` ghante mein ya nikal chuke (overdue) kaam."""
    now = datetime.now()
    limit = (now + timedelta(hours=hours)).strftime(DATETIME_FORMAT)
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, title, due_at FROM tasks WHERE done = 0 AND due_at IS NOT NULL AND due_at <= ? ORDER BY due_at",
            (limit,),
        ).fetchall()
    now_text = now.strftime(DATETIME_FORMAT)
    return [{**dict(row), "overdue": row["due_at"] < now_text} for row in rows]


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def parse_target_date(text):
    """'2027-07-01', '2027-07', 'July 2027' ya sirf '2027' ko YYYY-MM-DD banao."""
    text = str(text or "").strip().lower()
    try:
        return datetime.strptime(text, DATE_FORMAT).strftime(DATE_FORMAT)
    except ValueError:
        pass
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", text)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}-01"
    match = re.fullmatch(r"([a-z]+)\.?,?\s+(\d{4})", text)
    if match and match.group(1)[:3] in _MONTHS:
        return f"{match.group(2)}-{_MONTHS[match.group(1)[:3]]:02d}-01"
    if re.fullmatch(r"\d{4}", text):
        return f"{text}-12-31"
    raise ValueError("target_date aise likho: 2027-07-01.")


def add_goal(title, target_date):
    """Goal jodo (jaise 'AI engineer ban na', '2027-07-01')."""
    title = title.strip()
    if not title:
        raise ValueError("Goal ka naam chahiye.")
    target = parse_target_date(target_date)
    with connect() as conn:
        return conn.execute(
            "INSERT INTO goals (title, target_date, created_at) VALUES (?, ?, ?)",
            (title, target, _now_text()),
        ).lastrowid


def find_goal(text):
    """Goal ko id ya naam ke shabdon se dhundho. Ek hi mile to row, warna ValueError."""
    text = str(text or "").strip()
    if not text:
        raise ValueError("Kaunsa goal? Naam batao.")
    with connect() as conn:
        rows = conn.execute("SELECT id, title, target_date FROM goals").fetchall()
    if text.isdigit():
        rows = [r for r in rows if r["id"] == int(text)]
    else:
        words = [w for w in re.findall(r"\w+", text.lower()) if w not in _TASK_FILLER | {"goal", "lakshya"}] or [text.lower()]
        scored = [(sum(w in r["title"].lower() for w in words), r) for r in rows]
        best = max((score for score, _ in scored), default=0)
        rows = [r for score, r in scored if score == best and best > 0]
    if not rows:
        raise ValueError(f"'{text}' jaisa koi goal nahi mila.")
    if len(rows) > 1:
        raise ValueError("Kai goals milte hain: " + ", ".join(r["title"] for r in rows[:5]) + ". Thoda aur saaf batao.")
    return dict(rows[0])


def delete_goal(goal_id, title):
    with connect() as conn:
        return conn.execute("DELETE FROM goals WHERE id = ? AND title = ?", (int(goal_id), title)).rowcount > 0


def list_goals():
    """Saare goals, aur har ek mein kitne din baaki (days_left)."""
    today = datetime.now().date()
    with connect() as conn:
        rows = conn.execute("SELECT id, title, target_date, created_at FROM goals ORDER BY target_date").fetchall()
    return [
        {**dict(row), "days_left": (datetime.strptime(row["target_date"], DATE_FORMAT).date() - today).days}
        for row in rows
    ]
