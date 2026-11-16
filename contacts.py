"""Contacts aur unke nicknames ("mumi", "mummy", "maa" = ek hi insaan)."""
import sqlite3

from db import clean_query, connect


def add_contact(name, phone, aliases=()):
    """Naya contact jodo. Uske naam aur saare nicknames se wo mil jayega."""
    name, phone = name.strip(), phone.strip()
    if not name or not phone:
        raise ValueError("Naam aur phone dono chahiye.")
    # Contact ka apna naam bhi ek alias hai. Set se duplicate hat jate hain.
    names = {alias.strip().lower() for alias in (name, *aliases) if alias.strip()}
    try:
        with connect() as conn:  # contact aur aliases ek saath save hon, ya dono bilkul nahi
            contact_id = conn.execute("INSERT INTO contacts (name, phone) VALUES (?, ?)", (name, phone)).lastrowid
            conn.executemany(
                "INSERT INTO aliases (alias, contact_id) VALUES (?, ?)",
                [(alias, contact_id) for alias in sorted(names)],
            )
    except sqlite3.IntegrityError as error:  # koi alias pehle se kisi aur ka tha
        raise ValueError("Ye naam ya nickname pehle se kisi aur contact ka hai.") from error
    return contact_id


def find_contact(spoken):
    """Bole gaye naam (jaise "mumi") se contact dhundho. Na mile to None."""
    spoken = spoken.strip()
    if not spoken:
        return None
    with connect() as conn:
        row = conn.execute(
            "SELECT contacts.name, contacts.phone FROM aliases "
            "JOIN contacts ON contacts.id = aliases.contact_id "  # alias se contact tak ka rasta
            "WHERE aliases.alias = ?",
            (spoken,),
        ).fetchone()
    return dict(row) if row else None


def find_contact_row(spoken):
    """Contact ko naam ya nickname (pura ya adhoora) se dhundho: {'id', 'name', 'phone'}. Na mile to ValueError."""
    spoken = clean_query(str(spoken or "").strip().lower()).lower()
    if not spoken:
        raise ValueError("Kiska contact? Naam batao.")
    with connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT contacts.id, contacts.name, contacts.phone FROM aliases "
            "JOIN contacts ON contacts.id = aliases.contact_id WHERE aliases.alias = ?", (spoken,)).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT DISTINCT contacts.id, contacts.name, contacts.phone FROM aliases "
                "JOIN contacts ON contacts.id = aliases.contact_id WHERE aliases.alias LIKE ? OR contacts.name LIKE ?",
                (f"%{spoken}%", f"%{spoken}%")).fetchall()
    if not rows:
        raise ValueError(f"'{spoken}' naam ka koi contact nahi mila.")
    if len(rows) > 1:
        raise ValueError("Kai contacts milte hain: " + ", ".join(r["name"] for r in rows[:5]) + ". Poora naam batao.")
    return dict(rows[0])


def delete_contact(contact_id, name):
    """Contact aur uske nicknames hatao (foreign key se nicknames apne aap hat jaate hain). id + naam dono milein."""
    with connect() as conn:
        return conn.execute("DELETE FROM contacts WHERE id = ? AND name = ?", (int(contact_id), name)).rowcount > 0
