"""Saari settings ek hi jagah. Kuch badalna ho to sirf yahan badlo."""
import os
from pathlib import Path

# Ye project ka folder hai. Isse files ke raaste banate hain, isliye terminal kisi bhi
# folder mein ho, programs apni files sahi jagah dhundh lete hain.
BASE_DIR = Path(__file__).resolve().parent

# ---------- Ollama aur models ----------
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "llama3.2"
CHAT_NUM_CTX = 8192  # model ek saath kitna text yaad rakhe (tools ke saath chhota hone par galtiyan badhti hain)
OLLAMA_TIMEOUT_S = 120
CHAT_TEMPERATURE = 0  # 0 = har baar sabse pakka jawab, kam 'kalpana' (tool chunne mein bhi madad karta hai)
CHAT_MAX_TOKENS = 400  # ek jawab ki zyada se zyada lambai (lamba bakwas na likhe, jaldi khatam ho)
OLLAMA_KEEP_ALIVE = "30m"  # model itni der memory mein rahe; warna 5 min baad hat jata hai aur agla sawal dheema hota hai

# ---------- Awaaz se input (offline Whisper) ----------
# Pasand ka model: ye file ho to yahi chalega, warna voice.py apne aap doosra poora-downloaded model chun leta hai.
WHISPER_MODEL = BASE_DIR / "models" / "ggml-large-v3-turbo-q5_0.bin"

# ---------- Files aur folders ----------
NOTES_FOLDER = BASE_DIR / "my_data"
SUPPORTED_EXTENSIONS = {".txt", ".md"}
DB_PATH = Path(os.environ.get("ASSISTANT_DB", BASE_DIR / "assistant.db"))
EVAL_RESULTS_FILE = BASE_DIR / "eval_results.json"
EVAL_QUESTIONS_FILE = BASE_DIR / "eval_questions.json"
AGENT_EVAL_CASES_FILE = BASE_DIR / "agent_eval_cases.json"
AGENT_EVAL_RESULTS_FILE = BASE_DIR / "agent_eval_results.json"
HISTORY_FILE = BASE_DIR / "history.jsonl"
EMBED_CACHE_FILE = BASE_DIR / "embed_cache.json"  # notes ke vectors ki copy, taaki har baar dobara na banane padein

# ---------- Search ----------
TOP_K = 5  # model ko kitne passages dene hain

# ---------- Reminders ----------
# Bina samay wale reminder ("kal bill bharna") us din is samay yaad dilaye jate hain (pehle 23:59 par bajte the).
REMINDER_DAY_TIME = "09:00"

# ---------- Dashboard ----------
HOST = "127.0.0.1"  # sirf isi laptop se khulega, network par nahi
PORT = int(os.environ.get("PORT", "8001"))
SAVE_HISTORY = False  # True karoge to sawal history.jsonl mein save honge (private data!)
