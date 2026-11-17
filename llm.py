"""Ollama se baat karne ka code. Baaki saari files yahin se baat karti hain."""
import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from config import (CHAT_MAX_TOKENS, CHAT_MODEL, CHAT_NUM_CTX, CHAT_TEMPERATURE, EMBED_MODEL, OLLAMA_BASE,
                    OLLAMA_KEEP_ALIVE, OLLAMA_TIMEOUT_S)


CHAT_OPTIONS = {"num_ctx": CHAT_NUM_CTX, "temperature": CHAT_TEMPERATURE, "num_predict": CHAT_MAX_TOKENS}


class OllamaError(OSError):
    """Ollama chal raha hai par request fail hui (jaise model pull nahi hua). Message mein asli wajah hoti hai,
    taaki UI "Ollama band hai" ka galat ilaaj na bataye."""


def _request(path, payload):
    return Request(
        f"{OLLAMA_BASE}/api/{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


def _http_error(error):
    try:
        detail = json.loads(error.read()).get("error", "")
    except Exception:
        detail = ""
    if "not found" in detail and "model" in detail:
        model = CHAT_MODEL if CHAT_MODEL in detail else EMBED_MODEL if EMBED_MODEL in detail else "model"
        return OllamaError(f"Model '{model}' Ollama mein nahi mila. Terminal mein chalao: ollama pull {model}")
    return OllamaError(detail or f"Ollama ne {error.code} diya.")


def post_json(path, payload):
    try:
        with urlopen(_request(path, payload), timeout=OLLAMA_TIMEOUT_S) as response:
            return json.loads(response.read())
    except HTTPError as error:
        raise _http_error(error) from error


def embed(texts, prefix=""):
    # nomic-embed-text ke liye document aur sawal ke alag prefix lagte hain.
    payload = {"model": EMBED_MODEL, "input": [prefix + t for t in texts], "keep_alive": OLLAMA_KEEP_ALIVE}
    return post_json("embed", payload)["embeddings"]


_RUNNING = {"at": 0.0, "ok": False}


def is_running(max_age=10.0):
    """Ollama chal raha hai? Jawab 10 s tak yaad rakhte hain (har stats poll par ping nahi; band ho to 1.5 s ka atkav bhi nahi)."""
    now = time.monotonic()
    if now - _RUNNING["at"] < max_age:
        return _RUNNING["ok"]
    try:
        with urlopen(f"{OLLAMA_BASE}/api/tags", timeout=1.5):
            ok = True
    except OSError:
        ok = False
    _RUNNING.update(at=now, ok=ok)
    return ok


def warm_up():
    """Dono models ko pehle se memory mein load kar do, taaki pehla sawal bhi tez ho. Ollama band ho to False."""
    try:
        post_json("chat", {"model": CHAT_MODEL, "messages": [], "keep_alive": OLLAMA_KEEP_ALIVE})  # khali = sirf load
        embed(["warm up"])
        return True
    except (OSError, ValueError, KeyError):
        return False


def chat(messages, tools=None):
    """Poora jawab ek saath. tools do to model 'tool_calls' bhi bhej sakta hai."""
    payload = {"model": CHAT_MODEL, "messages": messages, "stream": False, "options": CHAT_OPTIONS,
               "keep_alive": OLLAMA_KEEP_ALIVE}
    if tools:
        payload["tools"] = tools
    return post_json("chat", payload)["message"]


def stream_chat(prompt):
    """Jawab ke tukde ek-ek karke deta hai (dashboard ki streaming ke liye)."""
    payload = {
        "model": CHAT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "options": CHAT_OPTIONS,
        "keep_alive": OLLAMA_KEEP_ALIVE,
    }
    try:
        with urlopen(_request("chat", payload), timeout=OLLAMA_TIMEOUT_S) as response:
            for raw_line in response:
                line = raw_line.strip()
                if line:
                    yield json.loads(line)
    except HTTPError as error:
        raise _http_error(error) from error
