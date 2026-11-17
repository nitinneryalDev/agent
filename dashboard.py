#!/usr/bin/env python3
"""Personal assistant ka dashboard: chat (tools ke saath), aapka saara data, notes se sawal-jawab, aur system stats.

Chalane ka tareeka:   python3 dashboard.py
Phir browser mein kholo: http://127.0.0.1:8001   (port config.py ya PORT=... se badlo)
"""
import atexit
import json
import math
import re
import signal
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback
from collections import Counter, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from threading import Lock, Thread
from urllib.parse import parse_qs, urlparse

import agent
import db
import llm
import notes
import overview
import planner
import replies
import translit
import planner
import views
import voice
import when
from config import (AGENT_EVAL_RESULTS_FILE, BASE_DIR, CHAT_MODEL, EMBED_MODEL, EVAL_RESULTS_FILE, HISTORY_FILE,
                    HOST, PORT, SAVE_HISTORY, TOP_K)
from db import connect
from tools import confirm_delete, run_tool

HTML_FILE = BASE_DIR / "dashboard.html"
STATIC_DIR = BASE_DIR / "static"  # dashboard.css, dashboard.js: sirf isi folder ki files, sirf in types ki
STATIC_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
MAX_RECORDS = 500
SERIES_LENGTH = 40
MAX_QUESTION_CHARS = 1000
MAX_BODY_BYTES = 10_000
MAX_AUDIO_BYTES = 15_000_000  # ~10 minute ki awaaz bhi isse chhoti hoti hai

# Browser ko sirf apne server se baat karne do. Bahar ki koi cheez load nahi hogi.
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; media-src 'self' blob:",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}


class Stats:
    """Poochhe gaye sawalon ka hisaab (sirf memory mein, lock ke saath)."""

    def __init__(self):
        self.started_at = time.time()
        self.lock = Lock()
        self.records = deque(maxlen=MAX_RECORDS)      # notes ke sawal
        self.assistant = deque(maxlen=MAX_RECORDS)    # assistant ki baatein (New chat se nahi mitti)
        self.index_error = ""
        self.warm = False


STATS = Stats()

# Assistant ki chat (sirf memory mein). Lock isliye ki ek samay mein ek hi baat-cheet chale.
ASSISTANT_HISTORY = []           # model ke liye (tool calls ke saath)
CHAT_LOG = deque(maxlen=100)     # screen ke liye (page refresh par bhi chat wapas dikhe)
ASSISTANT_LOCK = Lock()
MAX_ASSISTANT_MESSAGES = 100
_ENTRY_IDS = count(1)


# ---------- Metrics ----------
def add_record(entry):
    with STATS.lock:
        STATS.records.append(entry)
    if SAVE_HISTORY:
        with HISTORY_FILE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry) + "\n")


def load_history():
    # 1. Database se pichhle chat messages load karo taaki browser refresh/restart par chat zinda rahe
    try:
        with connect() as conn:
            rows = conn.execute("SELECT content FROM chat_messages ORDER BY id DESC LIMIT 50").fetchall()
            for r in reversed(rows):
                try:
                    entry = json.loads(r["content"])
                except Exception:
                    continue
                if not isinstance(entry, dict) or not entry.get("text") or "reply" not in entry:
                    continue  # adhoori/kharab entry: chat dikhane mein dikkat na kare
                if entry.get("pending") and not entry["pending"].get("resolved"):
                    entry["pending"]["resolved"] = "stale"  # restart ke baad purana "pakka?" sawal band dikhe
                CHAT_LOG.append(entry)
    except Exception:
        pass

    if not SAVE_HISTORY or not HISTORY_FILE.exists():
        return
    for line in HISTORY_FILE.read_text(encoding="utf-8").splitlines()[-MAX_RECORDS:]:
        try:
            STATS.records.append(json.loads(line))
        except ValueError:
            continue


def mean(values):
    return sum(values) / len(values) if values else None


def percentile(values, pct):
    # Nearest-rank: kam sawal hon to ye sabse bade value ke barabar aata hai.
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(math.ceil(pct / 100 * len(ordered)) - 1, 0)]


def rounded(value, digits=0):
    return None if value is None else round(value, digits)


def read_eval():
    try:
        data = json.loads(EVAL_RESULTS_FILE.read_text(encoding="utf-8"))
        correct, total = int(data["correct"]), int(data["total"])
        return {"correct": correct, "total": total, "ran_at": str(data.get("ran_at", ""))} if total > 0 else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def read_agent_eval():
    try:
        data = json.loads(AGENT_EVAL_RESULTS_FILE.read_text(encoding="utf-8"))
        return {k: data[k] for k in ("correct", "total", "avg_ms", "p50_ms", "ran_at")} if data.get("total") else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def assistant_stats():
    with STATS.lock:
        records = list(STATS.assistant)
    now = time.time()
    times = [r["ms"] for r in records]
    return {
        "turns": len(records),
        "last_minute": sum(1 for r in records if now - r["ts"] <= 60),
        "avg_ms": rounded(mean(times)),
        "p95_ms": rounded(percentile(times, 95)),
        "shortcut_rate": rounded(100 * mean([r["route"] == "shortcut" for r in records]), 0) if records else None,
        # Sirf model wale turns ka average (shortcut/code turns 0 call ke saath ise jhootha "good" bana dete the).
        "avg_llm_calls": rounded(mean([r["llm_calls"] for r in records if r["route"] == "model"]), 1),
        "error_turns": sum(1 for r in records if r["errors"]),
        "series": [{"ts": r["ts"], "ms": r["ms"], "route": r["route"], "text": r["text"]} for r in records[-SERIES_LENGTH:]],
    }


def build_stats():
    with STATS.lock:
        records = list(STATS.records)
        index_error = STATS.index_error
    now = time.time()
    speeds = [r["tokens_per_s"] for r in records if r.get("tokens_per_s")]
    unknowns = [1 if r["dont_know"] else 0 for r in records]
    series = [
        {
            "ts": r["ts"],
            "question": r["question"],
            "search_ms": r["search_ms"],
            "wait_ms": max(r["first_word_ms"] - r["search_ms"], 0),
            "write_ms": max(r["total_ms"] - r["first_word_ms"], 0),
            "top_score": r["top_score"],
            "dont_know": r["dont_know"],
        }
        for r in records[-SERIES_LENGTH:]
    ]
    recent = [
        {k: r[k] for k in ("ts", "question", "top_file", "top_score", "total_ms", "dont_know")}
        for r in reversed(records[-8:])
    ]
    file_counts = Counter(name for r in records for name in r["files"])
    return {
        "ollama_ok": llm.is_running(),
        "warm": STATS.warm,
        "can_say": SAY_AVAILABLE,
        "whisper_ok": voice.ready(),
        "whisper_model": voice.model_name(),
        "top_k": TOP_K,
        "chat_model": CHAT_MODEL,
        "embed_model": EMBED_MODEL,
        "index_error": index_error,
        "uptime_s": int(now - STATS.started_at),
        "files": notes.INDEX.file_count,
        "chunks": notes.INDEX.chunk_count,
        "questions_total": len(records),
        "questions_last_minute": sum(1 for r in records if now - r["ts"] <= 60),
        "avg_total_ms": rounded(mean([r["total_ms"] for r in records])),
        "p95_total_ms": rounded(percentile([r["total_ms"] for r in records], 95)),
        "avg_search_ms": rounded(mean([r["search_ms"] for r in records])),
        "avg_first_word_ms": rounded(mean([r["first_word_ms"] for r in records])),
        "avg_tokens_per_s": rounded(mean(speeds), 1),
        "avg_top_score": rounded(mean([r["top_score"] for r in records]), 2),
        "dont_know_rate": rounded(100 * mean(unknowns), 0) if unknowns else None,
        "eval": read_eval(),
        "agent_eval": read_agent_eval(),
        "assistant": assistant_stats(),
        "files_used": [{"file": f, "count": n} for f, n in file_counts.most_common(8)],
        "series": series,
        "recent": recent,
    }


# ---------- Notes se sawal ka jawab (streaming) ----------
def send_event(handler, payload):
    handler.wfile.write(b"data: " + json.dumps(payload).encode("utf-8") + b"\n\n")
    handler.wfile.flush()


def start_stream(handler):
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    for name, value in SECURITY_HEADERS.items():
        handler.send_header(name, value)
    handler.end_headers()


def tokens_per_second(final, pieces, write_seconds):
    # Ollama ka apna token count aur time sabse sahi hai; na mile to chunks se andaza lagao.
    eval_seconds = (final.get("eval_duration") or 0) / 1e9
    if eval_seconds:
        return (final.get("eval_count") or pieces) / eval_seconds
    return pieces / write_seconds if write_seconds > 0 else None


def run_question(handler, question, started):
    """Search -> sources bhejo -> jawab ke tokens stream karo -> metrics save karo."""

    def elapsed_ms():
        return round((time.perf_counter() - started) * 1000)

    notes.INDEX.ensure_built()
    # Hindi lipi ka sawal Roman mein badalkar dhundho (notes ka search Roman/English behtar samajhta hai).
    passages = notes.INDEX.search_best([translit.to_roman(question)])
    if not passages:
        send_event(handler, {"type": "error", "message": "No notes loaded. Add .md or .txt files to my_data, then press Reload notes."})
        return
    search_ms = elapsed_ms()
    send_event(handler, {
        "type": "sources",
        "search_ms": search_ms,
        "passages": [{"file": c["source"], "score": round(s, 3), "text": c["text"]} for s, c in passages],
    })
    parts, first_word_ms, final = [], None, {}
    stream = llm.stream_chat(notes.build_prompt(question, passages))
    try:
        for chunk in stream:
            piece = chunk.get("message", {}).get("content", "")
            if piece:
                first_word_ms = first_word_ms or elapsed_ms()
                parts.append(piece)
                send_event(handler, {"type": "token", "text": piece})
            if chunk.get("done"):
                final = chunk
    finally:
        stream.close()  # Ollama ko bhi band karo, warna wo jawab likhta rahega
    total_ms = elapsed_ms()
    first_word_ms = first_word_ms or total_ms
    speed = tokens_per_second(final, len(parts), (total_ms - first_word_ms) / 1000)
    entry = {
        "ts": time.time(), "question": question, "top_file": passages[0][1]["source"],
        "top_score": round(passages[0][0], 3), "files": [c["source"] for _, c in passages],
        "search_ms": search_ms, "first_word_ms": first_word_ms, "total_ms": total_ms,
        "tokens_per_s": rounded(speed, 1), "dont_know": notes.is_dont_know("".join(parts)),
    }
    add_record(entry)
    send_event(handler, {"type": "done", **{k: entry[k] for k in ("search_ms", "first_word_ms", "total_ms", "tokens_per_s", "dont_know")}})


def ask_and_stream(handler, question):
    start_stream(handler)
    try:
        run_question(handler, question, time.perf_counter())
    except (BrokenPipeError, ConnectionResetError):
        return  # user ne Stop dabaya ya page band kar diya
    except (OSError, ValueError, KeyError):
        try:
            send_event(handler, {"type": "error", "message": "Can't reach Ollama. Open the Ollama app, then press Reload notes."})
        except OSError:
            pass


# ---------- Assistant (tools ke saath) ----------
def parse_tool_result(result):
    try:
        return json.loads(result)
    except ValueError:
        return result


def run_assistant_turn(text, confirm_token=None):
    """Agent ko ek baat bolo. Jawab ke saath ye bhi: kaunse tools chale, kaunse tables badle, kitna time laga,
    aur agar kuch hatane ka sawal poochha hai to uska token (Haan/Nahi buttons ke liye)."""
    tools_used, tables, info = [], [], {}

    def remember_tool(name, arguments, result):
        parsed = parse_tool_result(result)
        failed = isinstance(parsed, dict) and "error" in parsed
        tools_used.append({"name": name, "arguments": arguments, "result": parsed, "ok": not failed})
        table = views.table_data(name, result)  # terminal wala wahi status table, ab asli rows ke saath
        if table and table not in tables:
            tables.append(table)

    started = time.perf_counter()
    with ASSISTANT_LOCK:
        reply = agent.run_turn(ASSISTANT_HISTORY, text, on_tool=remember_tool, info=info, confirm_token=confirm_token)
        del ASSISTANT_HISTORY[:-MAX_ASSISTANT_MESSAGES]  # purani baatein hata do, memory na bhare
        elapsed = round((time.perf_counter() - started) * 1000)
        # Pichhle message ka "pakka hata doon?" sawal ab band: refresh ke baad bhi uske buttons kaam na karein.
        for old in CHAT_LOG:
            if old.get("pending") and not old["pending"].get("resolved"):
                old["pending"]["resolved"] = info.get("confirm_result") or "dropped"
        pending = info.get("pending")
        entry = {
            "id": next(_ENTRY_IDS), "ts": time.time(), "text": text, "understood": info.get("understood"),
            "reply": reply, "tools": tools_used, "tables": tables, "route": info.get("route", "model"),
            "shortcut": info.get("shortcut"), "offered": info.get("tools_offered", []), "reason": info.get("reason", ""),
            "when": info.get("when"), "llm_calls": info.get("llm_calls", 0), "ms": elapsed,
            "pending": {k: pending[k] for k in ("token", "kind", "label")} if pending else None,
        }
        CHAT_LOG.append(entry)
        try:
            with connect() as conn:
                conn.execute(
                    "INSERT INTO chat_messages (role, content, route, tools, created_at) VALUES (?, ?, ?, ?, ?)",
                    ("turn", json.dumps(entry, ensure_ascii=False), entry.get("route"), json.dumps(entry.get("tools", []), ensure_ascii=False), str(time.time())),
                )
                conn.execute("DELETE FROM chat_messages WHERE id <= (SELECT MAX(id) - 500 FROM chat_messages)")
        except Exception:
            pass
    with STATS.lock:
        STATS.assistant.append({"ts": entry["ts"], "ms": elapsed, "route": entry["route"], "text": text,
                                "llm_calls": entry["llm_calls"], "errors": sum(not t["ok"] for t in tools_used)})
    return entry


# Dashboard ke buttons (habit done, kaam done, paani +1): bina model ke, seedha tool se.
def _quick_task(data):
    """Sidebar ka quick-add: "kal 6 baje doodh lena" -> naam "doodh lena", samay code se (model nahi)."""
    text = voice.correct(translit.to_roman(str(data.get("text", "")).strip())[:200], fuzzy=False)
    due = when.reminder_time(text)  # "kal subah X" jaise bina-ghante text ko subah ka default samay mile
    return {"title": planner.clean_title(text), **({"due": due} if due else {})}


ACTIONS = {
    "add_task": ("add_task", _quick_task),
    "add_habit": ("add_habit", lambda d: {"name": translit.to_roman(str(d.get("name", "")).strip())[:60]}),
    "check_in": ("check_in_habit", lambda d: {"habit": str(d.get("habit", ""))}),
    "complete_task": ("complete_task", lambda d: {"task": str(d.get("task_id", ""))}),
    "log_health": ("log_health", lambda d: {"kind": str(d.get("kind", "")), "value": d.get("value")}),
}


def run_action(data):
    action = ACTIONS.get(str(data.get("action", "")))
    if action is None:
        return 400, {"ok": False, "message": "Ye action nahi pata."}
    tool, build_arguments = action
    arguments = build_arguments(data)
    parsed = parse_tool_result(run_tool(tool, arguments))
    if not isinstance(parsed, dict) or "error" in parsed:
        message = parsed.get("error") if isinstance(parsed, dict) else "Kuch gadbad ho gayi."
        return 200, {"ok": False, "message": message}
    return 200, {"ok": True, "message": replies.reply_for(tool, arguments, parsed), "overview": overview.build_overview()}


# Dashboard ke "hatao" button: UI pehle khud "Hata dein? Haan/Nahi" poochhta hai, phir yahan aata hai.
DELETE_TARGETS = {"task": int, "item": str, "thing": int, "habit": int, "goal": int, "contact": int}


def run_delete(data):
    kind = str(data.get("kind", ""))
    if kind not in DELETE_TARGETS:
        return 400, {"ok": False, "message": "Ye cheez hatayi nahi ja sakti."}
    try:
        target = DELETE_TARGETS[kind](data.get("id"))
    except (TypeError, ValueError):
        return 400, {"ok": False, "message": "Galat id."}
    name = str(data.get("name", ""))  # screen par dikha poora naam: id ke saath ye bhi milna chahiye
    label = str(data.get("label", "") or name)[:200]
    if not name:
        return 400, {"ok": False, "message": "Kya hatana hai, naam nahi mila."}
    try:
        confirm_delete(kind, target, name, label)
    except ValueError as error:
        return 200, {"ok": False, "message": str(error)}
    return 200, {"ok": True, "message": f"Hata diya: {label}." if label else "Hata diya.", "overview": overview.build_overview()}


# ---------- Bolkar jawab (Mac ka apna `say`, poora offline) ----------
SAY_PROCESS = None
SAY_LOCK = Lock()
MAX_SPEAK_CHARS = 2000
SAY_AVAILABLE = shutil.which("say") is not None
DEVANAGARI = re.compile(r"[ऀ-ॿ]")


_VOICES = None


def best_voice(lang):
    """Is Mac par us bhasha ki sabse natural awaaz: Premium > Enhanced > baaki. (`say -v ?` ek baar padhte hain.)"""
    global _VOICES
    if _VOICES is None:
        try:
            out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=5).stdout
        except Exception:
            out = ""
        _VOICES = [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"^(.+?)\s+([a-z]{2}_[A-Z]{2})\s+#", out, re.M)]
    rank = lambda name: 2 if "Premium" in name else 1 if "Enhanced" in name else 0
    names = sorted((n for n, l in _VOICES if l == lang), key=rank, reverse=True)
    return names[0] if names else None


def stop_speaking():
    global SAY_PROCESS
    with SAY_LOCK:
        if SAY_PROCESS and SAY_PROCESS.poll() is None:
            SAY_PROCESS.terminate()
        SAY_PROCESS = None


def speak_text(text):
    """Text ko Mac ki awaaz mein bolo. Hindi ke liye Lekha, English ke liye Rishi, warna system default voice."""
    global SAY_PROCESS
    stop_speaking()
    voice = best_voice("hi_IN" if DEVANAGARI.search(text) else "en_IN") or ("Lekha" if DEVANAGARI.search(text) else "Rishi")
    try:
        process = subprocess.Popen(["say", "-v", voice, "-f", "-"], stdin=subprocess.PIPE,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process.stdin.write(text.encode("utf-8"))
        process.stdin.close()
    except Exception:
        try:
            process = subprocess.Popen(["say", "-f", "-"], stdin=subprocess.PIPE,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.stdin.write(text.encode("utf-8"))
            process.stdin.close()
        except Exception:
            return
    with SAY_LOCK:
        SAY_PROCESS = process


# ---------- HTTP server ----------
class Handler(BaseHTTPRequestHandler):
    server_version = "AssistantDashboard/3.0"

    def log_message(self, format, *args):
        pass  # request log band, taaki terminal mein kuch private na dikhe

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def host_is_allowed(self):
        # DNS rebinding se bachne ke liye: sirf apna hi Host naam maano.
        return self.headers.get("Host", "") in ALLOWED_HOSTS

    def body_length(self):
        try:
            return int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return 0

    def read_json_body(self):
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            return None
        length = self.body_length()
        if length <= 0 or length > MAX_BODY_BYTES:
            return None
        try:
            data = json.loads(self.rfile.read(length))
        except ValueError:
            return None
        return data if isinstance(data, dict) else None  # [] ya "text" body par crash nahi, saaf 400

    def send_file(self, path, content_type):
        try:
            body = path.read_bytes()
        except OSError:
            return self.send_json(404, {"error": "not found"})
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        return self.wfile.write(body)

    def do_GET(self):
        # Koi bhi anhoni error (DB lock, disk full, kharab value) par bhi JSON jawab jaye: pehle connection hi
        # band ho jata tha aur UI galat kehta tha "dashboard.py chal nahi raha".
        try:
            return self._get()
        except sqlite3.Error as error:
            return self.send_json(503, {"error": "db", "message": f"Database mein dikkat: {error}. "
                                        "Backup se wapas: python3 db.py restore"})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            traceback.print_exc()
            return self.send_json(500, {"error": "server", "message": "Server mein dikkat aa gayi (terminal dekho)."})

    def do_POST(self):
        try:
            return self._post()
        except sqlite3.Error as error:
            return self.send_json(503, {"error": "db", "message": f"Database mein dikkat: {error}. "
                                        "Backup se wapas: python3 db.py restore"})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            traceback.print_exc()
            return self.send_json(500, {"error": "server", "message": "Server mein dikkat aa gayi (terminal dekho)."})

    def _get(self):
        if not self.host_is_allowed():
            return self.send_json(403, {"error": "forbidden"})
        path = urlparse(self.path).path
        if path.startswith("/static/"):
            target = (STATIC_DIR / path[len("/static/"):]).resolve()
            if target.parent != STATIC_DIR.resolve() or target.suffix not in STATIC_TYPES:
                return self.send_json(404, {"error": "not found"})  # folder ke bahar ya anjaan type: mana
            return self.send_file(target, STATIC_TYPES[target.suffix])
        if path == "/api/stats":
            return self.send_json(200, build_stats())
        if path == "/api/overview":
            return self.send_json(200, overview.build_overview())
        if path == "/api/assistant/history":
            return self.send_json(200, {"messages": list(CHAT_LOG)})
        if path in ("/", "/index.html"):
            return self.send_file(HTML_FILE, "text/html; charset=utf-8")
        self.send_json(404, {"error": "not found"})

    def _post(self):
        if not self.host_is_allowed():
            return self.send_json(403, {"error": "forbidden"})
        url = urlparse(self.path)
        if url.path == "/api/voice/warm":  # mic button dabte hi whisper-server pehle se chalu (idle ke baad bhi tez)
            Thread(target=voice.prewarm, daemon=True).start()
            return self.send_json(200, {"ok": True})
        if url.path == "/api/transcribe":  # awaaz JSON nahi, seedhe bytes aati hai
            query = parse_qs(url.query)
            return self.handle_transcribe(query.get("lang", ["auto"])[0], query.get("partial", ["0"])[0] == "1")
        data = self.read_json_body()
        if data is None:
            return self.send_json(400, {"error": "JSON body chahiye"})
        if url.path == "/api/ask":
            question = str(data.get("question", "")).strip()
            if not question or len(question) > MAX_QUESTION_CHARS:
                return self.send_json(400, {"error": "sawal khali ya bahut lamba hai"})
            return ask_and_stream(self, question)
        if url.path == "/api/assistant":
            text = str(data.get("text", "")).strip()
            if not text or len(text) > MAX_QUESTION_CHARS:
                return self.send_json(400, {"message": "Text khali ya bahut lamba hai."})
            token = data.get("confirm_token")  # "" = screen par koi sawal nahi. Sirf field hi na ho to None (CLI jaisa)
            try:
                return self.send_json(200, run_assistant_turn(text, None if token is None else str(token)))
            except llm.OllamaError as error:
                return self.send_json(502, {"message": str(error)})
            except OSError:
                return self.send_json(502, {"message": "Can't reach Ollama. Open the Ollama app, then try again."})
        if url.path == "/api/assistant/reset":
            with ASSISTANT_LOCK:
                ASSISTANT_HISTORY.clear()
                CHAT_LOG.clear()
                try:
                    with connect() as conn:  # "New chat" restart ke baad bhi naya rahe
                        conn.execute("DELETE FROM chat_messages")
                    with connect() as conn:  # WAL ko bhi saaf karo: purani baatein file ke andar na bachi rahen
                        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except Exception:
                    pass
            return self.send_json(200, {"ok": True})
        if url.path == "/api/action":
            status, payload = run_action(data)
            return self.send_json(status, payload)
        if url.path == "/api/delete":
            status, payload = run_delete(data)
            return self.send_json(status, payload)
        if url.path == "/api/voice/fix":  # browser mic ka text: sirf pakki galtiyan (phoon -> phone), andaza nahi
            text = str(data.get("text", ""))[:MAX_QUESTION_CHARS]
            return self.send_json(200, {"text": voice.correct(text, fuzzy=False)})
        if url.path == "/api/speak":
            text = str(data.get("text", "")).strip()[:MAX_SPEAK_CHARS]
            if not SAY_AVAILABLE:
                return self.send_json(501, {"message": "Is computer par `say` nahi hai."})
            if not text:
                stop_speaking()
                return self.send_json(200, {"ok": True})
            speak_text(text)
            return self.send_json(200, {"ok": True})
        if url.path == "/api/reload":
            try:
                notes.INDEX.build()
                STATS.index_error = ""
            except OSError:
                STATS.index_error = "ollama"
                return self.send_json(502, {"ok": False, "message": "Can't reach Ollama. Open the Ollama app, then try again."})
            return self.send_json(200, {"ok": True, "files": notes.INDEX.file_count, "chunks": notes.INDEX.chunk_count})
        self.send_json(404, {"error": "not found"})

    def handle_transcribe(self, lang, partial):
        if not voice.ready():
            return self.send_json(503, {"message": "Whisper abhi taiyar nahi hai (model download ya install baaki)."})
        if not self.headers.get("Content-Type", "").startswith(("audio/", "video/", "application/octet-stream")):
            return self.send_json(400, {"message": "Audio chahiye."})
        length = self.body_length()
        if length <= 0 or length > MAX_AUDIO_BYTES:
            return self.send_json(413, {"message": "Recording khali ya bahut lambi hai."})
        audio = self.rfile.read(length)
        started = time.perf_counter()
        try:
            text = voice.transcribe(audio, lang, partial=partial)
        except (subprocess.SubprocessError, OSError):
            return self.send_json(500, {"message": "Awaaz samajh nahi paya. Dobara bolkar dekho."})
        return self.send_json(200, {"text": text, "partial": partial, "ms": round((time.perf_counter() - started) * 1000)})


VOICE_IDLE_S = 900  # itni der awaaz use na ho to whisper-server band (~700 MB wapas); mic dabate hi dobara chalu


def _reminder_loop():
    while True:
        try:
            planner.check_and_notify_due_tasks()
        except Exception:
            traceback.print_exc()
        try:
            db.backup_db()  # din badla to naya backup (pehle sirf startup par banta tha; ab lamba chalta server bhi roz lega)
            voice.idle_shutdown(VOICE_IDLE_S)
        except Exception:
            pass
        time.sleep(30)


def prepare():
    """Server chalu hote hi background mein: notes ka index, models load, Whisper, auto-backup aur desktop reminder
    checker. Har kadam apni try mein: ek kharab cheez (jaise ek kharab note file) baaki taiyari nahi rokti."""
    try:
        db.backup_db()
    except Exception:
        traceback.print_exc()
    Thread(target=_reminder_loop, daemon=True).start()
    try:
        notes.INDEX.build()
    except OSError:
        STATS.index_error = "ollama"  # Ollama band hai; pehle sawal par ya Reload se dobara try hoga
    except Exception:
        traceback.print_exc()
        STATS.index_error = "notes"
    try:
        STATS.warm = llm.warm_up()
    except Exception:
        STATS.warm = False
    try:
        voice.warm_up()  # whisper-server chalu + ek baar khamoshi: pehli asli recording bhi tez
    except Exception:
        traceback.print_exc()


def _graceful_exit(signum, frame):
    raise KeyboardInterrupt  # "kill" ya terminal band hone par bhi neeche wala finally chale (whisper-server band ho)


LAUNCH_AGENT_LABEL = "local.assistant.dashboard"


def install_launch_agent():
    """Login par dashboard apne aap chale (reminder aur backup bhi tabhi milte hain jab ye chal raha ho)."""
    from pathlib import Path
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_LABEL}.plist"
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{LAUNCH_AGENT_LABEL}</string>
  <key>ProgramArguments</key><array>
    <string>{sys.executable}</string>
    <string>{BASE_DIR / 'dashboard.py'}</string>
  </array>
  <key>WorkingDirectory</key><string>{BASE_DIR}</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>StandardErrorPath</key><string>{BASE_DIR / 'logs' / 'dashboard.err.log'}</string>
</dict></plist>
"""
    (BASE_DIR / "logs").mkdir(exist_ok=True)
    plist_path.write_text(plist)
    import os
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LAUNCH_AGENT_LABEL}"], capture_output=True)
    done = subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)], capture_output=True, text=True)
    if done.returncode == 0:
        print(f"Ho gaya: ab login par dashboard khud chalega (http://{HOST}:{PORT}).")
        print(f"Hataane ke liye:  python3 dashboard.py --uninstall-agent")
    else:
        print(f"launchctl chala nahi paya: {done.stderr.strip()}\nPlist yahan hai: {plist_path}")


def uninstall_launch_agent():
    from pathlib import Path
    import os
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_LABEL}.plist"
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LAUNCH_AGENT_LABEL}"], capture_output=True)
    plist_path.unlink(missing_ok=True)
    print("Auto-start hata diya.")


def main():
    if "--install-agent" in sys.argv:
        return install_launch_agent()
    if "--uninstall-agent" in sys.argv:
        return uninstall_launch_agent()
    signal.signal(signal.SIGTERM, _graceful_exit)
    signal.signal(signal.SIGHUP, _graceful_exit)
    atexit.register(voice.shutdown)
    load_history()
    Thread(target=prepare, daemon=True).start()  # page turant khule, taiyari peeche chalti rahe
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Dashboard chal raha hai: http://{HOST}:{PORT}  (band karne ke liye Ctrl+C)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBand ho raha hai.")
    finally:
        stop_speaking()
        voice.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
