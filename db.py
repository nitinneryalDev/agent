"""SQLite database: saare tables ek jagah, aur connection kholne ka ek hi tareeka."""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from config import BASE_DIR, DB_PATH

# Saari tables yahan. IF NOT EXISTS ka matlab: pehle se hon to chhedi nahi jayengi (tumhara data safe).
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS items (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    place      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS contacts (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL,
    phone TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aliases (
    alias      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    contact_id INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY,
    title      TEXT NOT NULL,
    due_at     TEXT,
    done       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    notified   INTEGER NOT NULL DEFAULT 0,
    recurrence TEXT
);
CREATE TABLE IF NOT EXISTS goals (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    target_date TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS health_logs (
    day   TEXT NOT NULL,
    kind  TEXT NOT NULL,
    value REAL NOT NULL,
    PRIMARY KEY (day, kind)
);
CREATE TABLE IF NOT EXISTS habits (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE COLLATE NOCASE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS habit_checkins (
    habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    day      TEXT NOT NULL,
    PRIMARY KEY (habit_id, day)
);
CREATE TABLE IF NOT EXISTS things (
    id         INTEGER PRIMARY KEY,
    category   TEXT NOT NULL COLLATE NOCASE,
    name       TEXT NOT NULL,
    status     TEXT,
    place      TEXT,
    details    TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id         INTEGER PRIMARY KEY,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    route      TEXT,
    tools      TEXT,
    created_at TEXT NOT NULL
);
"""


def _migrate(conn):
    """Pehle se bane database mein naye columns jodna, bina data khoye."""
    cursor = conn.execute("PRAGMA table_info(tasks)")
    columns = {row["name"] for row in cursor.fetchall()}
    if "notified" not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN notified INTEGER NOT NULL DEFAULT 0")
    if "recurrence" not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN recurrence TEXT")


# Dhundhte waqt in shabdon ka koi matlab nahi ("passport wali entry hata do" -> "passport").
FILLER_WORDS = {"ka", "ki", "ke", "ko", "kaa", "wala", "wali", "wale", "ye", "yeh", "wo", "woh", "vo", "is", "us", "entry",
                "item", "cheez", "hata", "hataa", "hatao", "hatado", "do", "delete", "remove", "cancel", "karo", "kar",
                "mera", "meri", "mere", "my", "the", "please", "plz", "apna", "apni", "apne", "contact", "habit", "goal"}


def clean_query(text):
    """Bharti ke shabd hatao. Sab hi hat jayein to asli text wapas (kuch to dhundhna hai)."""
    words = [w for w in str(text or "").split() if w.lower().strip(".,!?") not in FILLER_WORDS]
    return " ".join(words) or str(text or "").strip()


def like_pattern(text):
    """LIKE search ke liye: % aur _ ko normal akshar banao (warna "find %" sab kuch dikha deta hai).
    Use karte waqt SQL mein  ESCAPE '\\'  likhna zaroori hai."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


_READY = set()  # jin database files ka schema is process mein ban chuka (path + inode)


def _file_key():
    """File ki pehchaan: chalte server mein assistant.db hata kar nayi bani to inode badal jata hai -> schema dobara."""
    try:
        info = os.stat(DB_PATH)
        return (str(DB_PATH), info.st_ino, info.st_dev)
    except OSError:
        return (str(DB_PATH), None, None)


@contextmanager
def connect():
    """Use: `with connect() as conn:`. Andar ka kaam poora ho to save, error aaye to sab wapas.
    Connection apne aap band ho jata hai."""
    conn = sqlite3.connect(DB_PATH, timeout=10)  # doosra thread likh raha ho to 10 s tak intezaar, turant error nahi
    conn.row_factory = sqlite3.Row  # rows ko naam se padh sakein: row["place"]
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite mein ye har connection par khud on karna padta hai
    conn.execute("PRAGMA secure_delete = ON")  # delete ka matlab sach mein delete: purani chat file ke andar na bachi rahe
    key = _file_key()
    if key not in _READY:
        # Tables/columns banana aur WAL mode: har process mein sirf ek baar (pehle har connection par hota tha).
        # WAL = dashboard ke threads, reminder loop aur terminal agent ek saath padh-likh sakte hain.
        conn.executescript(SCHEMA_SQL)
        _migrate(conn)
        conn.execute("PRAGMA journal_mode = WAL")
        _READY.add(_file_key())
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def backup_db(keep_days=7):
    """Database ka daily snapshot. Suraksha ke niyam:
    - ASSISTANT_DB set hai (test/eval/dev run) to kuch nahi: asli backup kabhi test data se na bade.
    - Us din ka backup pehle se ho to use NAHI badalte (restart galti ke baad ka 'achha' backup mita deta tha).
    - Pehle quick_check: kharab database kabhi achhe backup ki jagah nahi leta.
    - Backup mein chat_messages nahi rakhte (baat-cheet private hai aur restore mein kisi kaam ki nahi)."""
    if os.environ.get("ASSISTANT_DB") or not DB_PATH.exists():
        return None
    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    target_path = backup_dir / f"assistant_{datetime.now().strftime('%Y-%m-%d')}.db"
    if target_path.exists():
        return target_path  # aaj ka backup ban chuka hai: use overwrite mat karo

    try:
        src = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            if src.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                return None
            dst = sqlite3.connect(target_path)
            with dst:
                src.backup(dst)
            try:
                dst.execute("DELETE FROM chat_messages")
                dst.commit()
                dst.execute("VACUUM")
            except sqlite3.Error:
                pass  # bahut purane backup format mein ye table nahi hai: backup phir bhi sahi hai
            dst.close()
        finally:
            src.close()
    except Exception:
        target_path.unlink(missing_ok=True)  # adhoora backup mat chhodo
        return None

    # Purane backups (keep_days se purane) saaf karo
    cutoff = datetime.now() - timedelta(days=keep_days)
    for old_file in backup_dir.glob("assistant_*.db"):
        try:
            file_date = datetime.strptime(old_file.stem.replace("assistant_", ""), "%Y-%m-%d")
            if file_date < cutoff:
                old_file.unlink(missing_ok=True)
        except (ValueError, OSError):
            continue
    return target_path


def restore_db(backup_path):
    """Backup ko wapas chadhao, SQLite backup API se (WAL-safe: `cp` se stale -wal purana data wapas le aata tha).
    Pehle abhi wale database ki safety copy banti hai."""
    backup_path = Path(backup_path)
    if not backup_path.exists():
        raise ValueError(f"Backup file nahi mili: {backup_path}")
    src = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)
    try:
        if src.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Ye backup file hi kharab hai, isse restore nahi kar sakte.")
        safety = None
        if DB_PATH.exists():
            safety = DB_PATH.parent / "backups" / f"pre_restore_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.db"
            safety.parent.mkdir(exist_ok=True)
            current = sqlite3.connect(DB_PATH)
            try:
                keep = sqlite3.connect(safety)
                with keep:
                    current.backup(keep)
                keep.close()
            finally:
                current.close()
        dst = sqlite3.connect(DB_PATH, timeout=10)
        try:
            src.backup(dst)  # chalte dashboard ke saath bhi safe, aur -wal/-shm ka dhyan khud rakhta hai
        finally:
            dst.close()
    finally:
        src.close()
    return safety


def _counts(path):
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 0").fetchone()[0]
            checkins = conn.execute("SELECT COUNT(*) FROM habit_checkins").fetchone()[0]
            return f"{tasks} pending tasks, {checkins} habit check-ins"
        finally:
            conn.close()
    except sqlite3.Error:
        return "padh nahi paya"


if __name__ == "__main__":
    import sys
    backups = sorted((DB_PATH.parent / "backups").glob("*.db"))
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        chosen = Path(sys.argv[2]) if len(sys.argv) > 2 else (backups[-1] if backups else None)
        if not chosen:
            print("Koi backup nahi mila.")
        else:
            print(f"Restore: {chosen} ({_counts(chosen)})")
            saved = restore_db(chosen)
            print(f"Ho gaya. Database ab: {_counts(DB_PATH)}" + (f"\nPurana data yahan rakha hai: {saved}" if saved else ""))
    else:
        print(f"Abhi ka database: {DB_PATH} ({_counts(DB_PATH)})\n")
        for backup in backups:
            print(f"  {backup.name}  ({_counts(backup)})")
        print("\nWapas lane ke liye:  python3 db.py restore [backups/assistant_YYYY-MM-DD.db]  (bina naam = sabse naya)")
