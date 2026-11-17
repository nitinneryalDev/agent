"""Tumhare notes (my_data folder) mein se jawab dhundhna (RAG)."""
import hashlib
import json
import math
import re
import sqlite3
from collections import OrderedDict
from threading import Lock

import llm
from config import EMBED_CACHE_FILE, EMBED_MODEL, NOTES_FOLDER, SUPPORTED_EXTENSIONS, TOP_K

MAX_CACHED_QUESTIONS = 200


def cosine(a, b):
    # Do vectors kitne milte-julte hain (1 ke paas = bahut milte-julte).
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def load_chunks(folder):
    # Har file ko khali line par todo, aur har tukde ke saath file ka naam rakho.
    chunks = []
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        # errors="replace": ek non-UTF-8 file (jaise Windows/WhatsApp export) poora notes index nahi todegi.
        for part in path.read_text(encoding="utf-8", errors="replace").split("\n\n"):
            if part.strip():
                chunks.append({"source": str(path.relative_to(folder)), "text": part.strip()})
    return chunks


class NotesIndex:
    """Notes ke tukde aur unke vectors. Lock isliye ki kai requests ek saath aa sakte hain."""

    def __init__(self):
        self.lock = Lock()
        self.chunks = []
        self.vectors = []
        self.question_vectors = OrderedDict()  # wahi sawal dobara aaye to embedding dobara na banao
        self.fts_conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.fts_conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(chunk_id UNINDEXED, source, text)")

    def build(self):
        """Notes padho aur vectors banao. Jo tukde pehle bhi the unke vectors disk ki cache se aate hain,
        sirf naye/badle tukdon ke liye Ollama ko bulate hain (startup aur Reload tez)."""
        chunks = load_chunks(NOTES_FOLDER) if NOTES_FOLDER.exists() else []
        cache = _load_cache()
        keys = [_key(c["text"]) for c in chunks]
        missing = [i for i, key in enumerate(keys) if key not in cache]
        if missing:
            fresh = llm.embed([chunks[i]["text"] for i in missing], "search_document: ")
            for i, vector in zip(missing, fresh):
                cache[keys[i]] = vector
        vectors = [cache[key] for key in keys if key in cache]
        _save_cache({key: cache[key] for key in keys if key in cache})  # purane (hata diye gaye) tukdon ki entry hata do
        with self.lock:
            self.chunks, self.vectors = chunks, vectors
            self.fts_conn.execute("DELETE FROM notes_fts")
            for idx, c in enumerate(chunks):
                self.fts_conn.execute("INSERT INTO notes_fts (chunk_id, source, text) VALUES (?, ?, ?)",
                                      (idx, c["source"], c["text"]))

    def ensure_built(self):
        # Ollama pehle band tha to jab zaroorat pade tab dobara koshish karo.
        if not self.chunks:
            self.build()

    def search(self, question, k=TOP_K):
        """Hybrid Search: Vector Embeddings + SQLite FTS5 BM25.
        Ollama band ho to FTS fallback bina error ke kaam karta hai."""
        with self.lock:
            chunks, vectors = self.chunks, self.vectors

        if not chunks:
            return []

        # 1. Vector Search (agar Ollama chalu hai)
        vector_scores = {}
        try:
            query_vector = self.question_vectors.get(question)
            if query_vector is None:
                query_vector = llm.embed([question], "search_query: ")[0]
                with self.lock:
                    self.question_vectors[question] = query_vector
                    while len(self.question_vectors) > MAX_CACHED_QUESTIONS:
                        self.question_vectors.popitem(last=False)
            for idx, v in enumerate(vectors):
                vector_scores[idx] = cosine(query_vector, v)
        except Exception:
            pass  # Ollama offline ho to vector scores khali rahenge

        # 2. SQLite FTS5 BM25 Keyword Search: rank ke KRAM mein (pehle bina ORDER BY ke koi bhi k*2 rows aati
        #    thin aur sabko ek jaisa boost milta tha, yaani BM25 asal mein use hi nahi ho raha tha).
        fts_rank = {}
        clean_words = [w for w in re.findall(r"\w+", question.lower()) if len(w) >= 3]
        if clean_words:
            fts_query = " OR ".join(f'"{w}"' for w in clean_words[:8])
            try:
                rows = self.fts_conn.execute(
                    "SELECT chunk_id FROM notes_fts WHERE notes_fts MATCH ? ORDER BY rank LIMIT ?",
                    (fts_query, k * 2)
                ).fetchall()
                fts_rank = {r[0]: i for i, r in enumerate(rows)}
            except Exception:
                pass

        # 3. Hybrid Scoring: vector + rank ke hisaab se ghat-ta hua keyword boost.
        #    (Asli sawalon par naapa: hit@1 36/46 -> 39/46, MRR 0.832 -> 0.868.)
        scored = []
        for idx, chunk in enumerate(chunks):
            v_score = vector_scores.get(idx, 0.0)
            boost = 0.25 * (1 - fts_rank[idx] / max(len(fts_rank), 1)) if idx in fts_rank else 0.0
            total_score = v_score * 0.75 + boost if vector_scores else (1.0 - fts_rank[idx] / 100 if idx in fts_rank else 0.0)
            scored.append((total_score, chunk))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:k]

    def search_best(self, questions, k=TOP_K):
        """Kai roop mein poochha gaya sawal (model ka English, user ka Hinglish): dono se dhundho, best tukde rakho."""
        best = {}
        for question in dict.fromkeys(q for q in questions if q):
            for score, chunk in self.search(expand_query(question), k):
                key = chunk["text"]
                if key not in best or score > best[key][0]:
                    best[key] = (score, chunk)
        return sorted(best.values(), key=lambda pair: pair[0], reverse=True)[:k]

    @property
    def chunk_count(self):
        return len(self.chunks)

    @property
    def file_count(self):
        return len({c["source"] for c in self.chunks})


# Notes English mein hain; Hinglish sawal ke shabdon ka English matlab bhi jod do, taaki search sahi tukda pakde.
HINGLISH_HINTS = {
    "janamdin": "birthday date of birth born", "janmdin": "birthday date of birth born", "janam": "born birth",
    "umar": "age", "naam": "name", "ghar": "home hometown", "gaon": "hometown village", "sheher": "city",
    "kaam": "work job", "naukri": "job work", "company": "company employer work", "papa": "father",
    "pita": "father", "mummy": "mother", "maa": "mother", "mata": "mother", "parivaar": "family",
    "bhai": "brother", "behen": "sister", "shaadi": "married wife", "padhai": "education study",
    "sapna": "dream goal", "lakshya": "goal", "khana": "food diet", "neend": "sleep", "subah": "morning routine",
    "rehta": "live city", "rahta": "live city", "rehti": "live city", "kahan": "where", "kab": "when",
}


def expand_query(question):
    words = re.findall(r"[a-z]+", question.lower())
    extra = [HINGLISH_HINTS[w] for w in words if w in HINGLISH_HINTS]
    return question + (" (" + " ".join(extra) + ")" if extra else "")


def _key(text):
    return hashlib.sha1(f"{EMBED_MODEL}|{text}".encode("utf-8")).hexdigest()


def _load_cache():
    try:
        data = json.loads(EMBED_CACHE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_cache(cache):
    try:
        EMBED_CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass  # cache na bane to bhi kaam chalta hai, bas thoda dheema


# Poore project mein ek hi index share hota hai (dashboard aur agent dono yahi use karte hain).
INDEX = NotesIndex()


def build_prompt(question, passages):
    context = "\n\n".join(chunk["text"] for _, chunk in passages)
    rules = (
        "The context below contains notes written by the user about themselves. "
        "Answer the user's question in second person ('you'), using only this context. "
        "If the answer is not in the context, say 'I don't know'."
    )
    if any("\u0900" <= ch <= "\u097f" for ch in question):  # Hindi (Devanagari) sawal
        rules += " Answer in simple Hinglish written in English letters, for example 'Aap Gurgaon mein rehte ho'."
    return f"{rules}\n\nContext:\n{context}\n\nQuestion: {question}"


def answer(question, passages):
    """Notes ke tukdon se jawab (wahi prompt jo dashboard aur eval mein hai). passages = [(score, chunk)]."""
    reply = llm.chat([{"role": "user", "content": build_prompt(question, passages)}])
    return reply.get("content", "").strip()


def is_dont_know(answer):
    return answer.strip().lower().replace("\u2019", "'").startswith("i don't know")
