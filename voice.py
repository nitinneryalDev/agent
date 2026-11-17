"""Awaaz se text: offline Whisper (whisper.cpp), sab kuch isi Mac par.

Tez aur live kaise:
  - whisper-server ek baar chalu karke model memory mein rakhte hain (har baar 500 MB model load nahi hota),
    isliye bolte waqt har ~1 second mein adhoora text (partial) bhi mil jata hai.
  - Sabse achha model jo poora download ho chuka ho wahi chalta hai (pehle large-v3-turbo, warna small).
Sahi kaise:
  - Prompt mein Hinglish ke example aur aapke saved naam (habits, cheezein, contacts) jaate hain, taaki Whisper
    unhe sahi spelling mein likhe ("walking", "passport", "Mummy").
  - Aam galat-suni shabd theek karte hain: "phoon" -> "phone", "aaad" -> "yaad", "perso" -> "parso".
"""
import difflib
import unicodedata
import io
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import atexit
import time
import uuid
import wave
from pathlib import Path
from threading import Lock
from urllib.request import Request, urlopen

from config import BASE_DIR, WHISPER_MODEL
import translit
from db import connect

WHISPER_SERVER = shutil.which("whisper-server")
WHISPER_CLI = shutil.which("whisper-cli")
FFMPEG = shutil.which("ffmpeg")
# Pasand ke kram mein: pehla jo poora download ho chuka ho wahi chalega. Size se adhoori file pakadte hain.
MODELS = [
    (BASE_DIR / "models" / "ggml-large-v3-turbo-q5_0.bin", 574_041_195),
    (BASE_DIR / "models" / "ggml-small.bin", 487_601_967),
]
THREADS = str(min(8, os.cpu_count() or 4))
LANGS = {"hi": "hi", "en": "en", "auto": "auto"}
# Label ("likho:", "Naam:") nahi: Whisper kabhi label hi copy kar deta tha ("mera: ... mera:").
BASE_PROMPT = ("walking ho gayi aaj. kal shaam 6 baje doodh lena yaad dilao. mera passport kahan "
               "hai. doodh wala reminder hata do. mummy ko phone karna hai. aaj 8 glass paani piya.")
MAX_PROMPT_CHARS = 600

_LOCK = Lock()  # ek samay mein ek hi transcription (partial aur final aapas mein na takrayein)
_ATEXIT_SET = False


# ---------- Kaunsa model, aur kya Whisper taiyar hai ----------
def best_model():
    # config.WHISPER_MODEL pehle (user ki pasand), warna list mein se pehla poora downloaded model.
    candidates = [(WHISPER_MODEL, 100_000_000)] + [(p, size) for p, size in MODELS if p != WHISPER_MODEL]
    for path, size in candidates:
        try:
            if path.stat().st_size >= size:
                return path
        except OSError:
            continue
    return None


def ready():
    return bool(best_model() and (WHISPER_SERVER or WHISPER_CLI))


def model_name():
    model = best_model()
    return model.name.replace("ggml-", "").replace(".bin", "") if model else None


# ---------- whisper-server: model memory mein rakhne wala chhota local server ----------
def _kill_orphan_servers():
    """Achanak band hue (kill/crash) dashboard ka whisper-server peeche reh jata hai (~600 MB): uska parent mar chuka
    hota hai, isliye wo PID 1 (launchd) ka bachcha ban jata hai. Sirf aise anaath servers band karo; kisi doosre chalu
    dashboard ka server (jiska parent zinda hai) kabhi nahi chhedte."""
    try:
        listing = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return
    models_dir = str(BASE_DIR / "models")
    for line in listing.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[1] == "1" and "whisper-server" in parts[2] and models_dir in parts[2]:
            try:
                os.kill(int(parts[0]), 15)
            except (OSError, ValueError):
                pass


class _Server:
    def __init__(self):
        self.process = None
        self.port = None
        self.model = None
        self.lock = Lock()
        self.cleaned = False
        self.last_used = 0.0

    def running(self):
        return self.process is not None and self.process.poll() is None

    def ensure(self, model):
        """Server chal raha ho (isi model ke saath) to uska port, warna chalu karke port. Fail ho to OSError."""
        with self.lock:
            if self.running() and self.model == model:
                return self.port
            if not self.cleaned:
                _kill_orphan_servers()
                self.cleaned = True
            self._stop()
            with socket.socket() as probe:  # khali port dhundho
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            self.process = subprocess.Popen(
                [WHISPER_SERVER, "-m", str(model), "--host", "127.0.0.1", "--port", str(port), "-l", "auto", "-nt",
                 "-t", THREADS],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.port, self.model = port, model
            global _ATEXIT_SET
            if not _ATEXIT_SET:
                atexit.register(SERVER.stop)  # jo bhi script server chalaye, exit par band bhi kare (orphan na bache)
                _ATEXIT_SET = True
            self.last_used = time.time()
            deadline = time.time() + 90  # bada model pehli baar disk se padhne mein der lagti hai
            while time.time() < deadline:
                if self.process.poll() is not None:
                    raise OSError("whisper-server band ho gaya")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                        return port
                except OSError:
                    time.sleep(0.25)
            self._stop()
            raise OSError("whisper-server chalu nahi hua")

    def _stop(self):
        if self.running():
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

    def stop(self):
        with self.lock:
            self._stop()


SERVER = _Server()


def _multipart(fields, audio):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8"))
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
                 f"Content-Type: audio/wav\r\n\r\n".encode("utf-8") + audio + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def _audio_ctx(wav, partial=True):
    """Whisper hamesha 30 second ki khidki padhta hai (1500 = 30 s). Chhoti recording ke liye chhoti khidki:
    turbo model 2 s se ~0.5 s ho jata hai, aur test mein text utna hi sahi raha. Kam se kam 512 (~10 s)."""
    if not partial:
        return 1500  # final text: asli recordings par chhoti khidki se galtiyan 38% -> 23% (kal->kar, walk->wak), ~0.6 s zyada
    with wave.open(io.BytesIO(wav)) as file:
        seconds = file.getnframes() / file.getframerate()
    needed = int(seconds * 50) + 128
    return min(1500, max(512, -(-needed // 64) * 64))


def _via_server(wav, lang, prompt, partial=True):
    port = SERVER.ensure(best_model())
    body, content_type = _multipart({"response_format": "json", "language": lang, "prompt": prompt,
                                     "temperature": "0.0", "no_timestamps": "true",
                                     "audio_ctx": str(_audio_ctx(wav, partial))}, wav)
    request = Request(f"http://127.0.0.1:{port}/inference", data=body, headers={"Content-Type": content_type})
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read()).get("text", "")


def _via_cli(wav, lang, prompt, partial=True):
    """Server na chale to purana tareeka: har baar whisper-cli (thoda dheema, par chalta hai)."""
    with tempfile.TemporaryDirectory(prefix="assistant-voice-") as folder:
        path = Path(folder) / "audio.wav"
        path.write_bytes(wav)
        result = subprocess.run([WHISPER_CLI, "-m", str(best_model()), "-f", str(path), "-nt", "-np", "-t", THREADS,
                                 "-l", lang, "--prompt", prompt, "-ac", str(_audio_ctx(wav, partial))],
                                check=True, timeout=180, capture_output=True, text=True)
    return result.stdout


# ---------- Audio taiyar karna ----------
def _is_wav16k(audio):
    if audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        return False
    try:
        with wave.open(io.BytesIO(audio)) as file:
            return file.getframerate() == 16000 and file.getnchannels() == 1 and file.getsampwidth() == 2
    except (wave.Error, EOFError):
        return False


def to_wav(audio):
    """Browser 16 kHz WAV bhejta hai (seedha chalega). Baaki formats (webm/mp4/aiff) ffmpeg se WAV."""
    if _is_wav16k(audio):
        return audio
    if not FFMPEG:
        raise OSError("ffmpeg nahi mila")
    with tempfile.TemporaryDirectory(prefix="assistant-voice-") as folder:
        source, target = Path(folder) / "input", Path(folder) / "audio.wav"
        source.write_bytes(audio)
        subprocess.run([FFMPEG, "-nostdin", "-loglevel", "error", "-y", "-i", str(source), "-ar", "16000", "-ac", "1",
                        "-c:a", "pcm_s16le", str(target)], check=True, timeout=60, capture_output=True)
        return target.read_bytes()


def silence_wav(seconds=0.5, rate=16000):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(rate)
        file.writeframes(b"\x00\x00" * int(seconds * rate))
    return buffer.getvalue()


# ---------- Prompt aur shabd theek karna ----------
def known_names(with_aliases=False):
    """Database ke naam (habits, cheezein, contacts, aur chahiye to nicknames bhi)."""
    sql = ("SELECT name FROM habits UNION SELECT name FROM items UNION SELECT name FROM things "
           "UNION SELECT name FROM contacts" + (" UNION SELECT alias FROM aliases" if with_aliases else ""))
    try:
        with connect() as conn:
            rows = [r[0] for r in conn.execute(sql)]
    except OSError:
        return []
    return [r for r in rows if r and len(r) <= 40]


_ENGLISH = None


def _english_words():
    """Mac ki apni English word list: jo shabd asli English hai ("track", "books") use kabhi mat badlo."""
    global _ENGLISH
    if _ENGLISH is None:
        try:
            with open("/usr/share/dict/words", encoding="utf-8", errors="ignore") as words:
                _ENGLISH = {w.strip().lower() for w in words}
        except OSError:
            _ENGLISH = set()
    return _ENGLISH


def build_prompt():
    names = []
    for name in known_names():
        if len(BASE_PROMPT) + len(", ".join(names + [name])) + 10 > MAX_PROMPT_CHARS:
            break
        names.append(name)
    return BASE_PROMPT + (f" {', '.join(names)}." if names else "")


# Command ke shabd jinhe Whisper aksar thoda galat sunta hai. Inke paas ke galat shabd inhi mein badal dete hain.
LEXICON = {
    "yaad", "dilao", "dilana", "dilane", "reminder", "phone", "call", "karna", "hatao", "habit", "habits",
    "kahan", "glass", "paani", "neend", "ghante", "subah", "shaam", "dopahar", "baje", "parso", "doodh", "mummy",
    "papa", "passport", "charger", "chabi", "joote", "jootein", "kitab", "book", "shoes", "walking", "meditation",
    "reading", "training", "minute", "energy", "health", "summary", "dikhao", "batao", "number", "contact",
    "delete", "cancel", "goal", "goals", "task", "tasks", "pending", "streak", "dentist", "appointment", "meeting",
    "umbrella", "wallet", "laptop", "almari", "drawer", "locker", "office", "kitchen", "bedroom", "shelf", "rack",
}
# Seedhe dekhe gaye galat-sune shabd (user ke asli test se): bina andaze ke badlo.
CONFUSIONS = {
    "aaad": "yaad", "yad": "yaad", "phoon": "phone", "bajay": "baje", "baaje": "baje", "bje": "baje", "bajeh": "baje",
    "fone": "phone", "perso": "parso", "parsoo": "parso", "aaaj": "aaj", "jim": "gym",
    "panee": "paani", "panni": "paani", "shm": "shaam", "sham": "shaam",
    "subha": "subah", "subeh": "subah", "swere": "savere", "dodh": "doodh", "dudh": "doodh",
    "kitaab": "kitab", "chaabi": "chabi", "chabe": "chabi", "chata": "chhata", "chatri": "chhatri",
    "ghnta": "ghanta", "ghnte": "ghante", "remindr": "reminder", "remnder": "reminder",
    "habbit": "habit", "habbits": "habits",
    "vajay": "baje", "wajay": "baje", "vaje": "baje", "waje": "baje", "bil": "bill", "bijhli": "bijli",
    "kl": "kal", "yd": "yaad",
}
# Aam shabd jinhe kabhi nahi chhedna (inke paas koi lexicon shabd ho tab bhi).
COMMON = {"mera", "meri", "mere", "main", "mujhe", "kya", "hai", "hain", "aur", "kal", "aaj", "nahi", "haan", "wala",
          "wali", "wale", "kaise", "kitna", "kitne", "kitni", "kyun", "abhi", "bhai", "karo", "kiya", "diya", "liya",
          "gaya", "gayi", "hoga", "hogi", "raha", "rahi", "rahe", "tha", "thi", "the", "maine", "apna", "apni", "unka",
          "inka", "kaam", "baat", "please", "thanks", "sirf", "bahut", "achha", "theek", "chahiye", "lena", "dena",
          "chai", "dila", "hata", "khana", "sabzi", "dawai", "dawa", "paise", "rupaye", "bhaiya", "didi", "mausi", "chacha",
          "chachi", "nani", "nana", "dadi", "dada", "beta", "beti", "dost", "ghar", "kapde", "naam", "kitab", "subah"}


def correct(text, fuzzy=True):
    """Galat-sune shabd theek karo. Bahut sambhal kar: sirf 5+ akshar wale anjaan shabd, sirf jab koi command-shabd ya
    saved naam bahut paas (84%+) ho. Asli English shabd, aam Hinglish shabd aur saved naam/nicknames kabhi nahi badalte.
    Chhote shabdon ke liye sirf CONFUSIONS ki pakki list ("aaad" -> "yaad")."""
    saved = known_names(with_aliases=True)
    names = {w for name in saved for w in re.findall(r"[a-z]+", name.lower())}
    vocabulary = set(LEXICON) | {w for w in names if len(w) >= 4}
    choices = sorted(vocabulary)
    english = _english_words()

    def fix(match):
        word = match.group(0)
        lower = word.lower()
        if lower in names:
            return word  # saved naam (jaise contact "Jim") ko kabhi mat badlo
        if lower in CONFUSIONS:
            better = CONFUSIONS[lower]
        elif (not fuzzy or len(lower) < 5 or lower in vocabulary or lower in COMMON or lower in english
              or (lower.endswith("s") and lower[:-1] in english)):  # "books" = book ka plural, asli shabd
            return word
        else:
            close = difflib.get_close_matches(lower, choices, n=1, cutoff=0.84)
            if not close or abs(len(close[0]) - len(lower)) > 2:
                return word
            better = close[0]
        return better.capitalize() if word[:1].isupper() else better

    return re.sub(r"[A-Za-z]+", fix, text)


def _clean(text):
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", text or "")  # [BLANK_AUDIO], (music) jaisa hatao
    # Whisper kabhi Hindi ko Gujarati/Bengali/Gurmukhi akshar mein likh deta hai: unhe Devanagari bana do
    # (Unicode mein inke akshar Devanagari jaise hi kram mein hain), phir translit Roman banayega.
    text = "".join(chr(ord(c) - _OFFSETS[ord(c) >> 7 << 7]) if (ord(c) >> 7 << 7) in _OFFSETS else c for c in text)
    # "ṣaam" jaise nishaan wale Roman akshar: nishaan hatao -> "saam"
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c) or "\u0900" <= c <= "\u097f")
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"^\s*\w+:\s*|\s*\w+:\s*$", " ", " ".join(text.split()))  # prompt ka label copy ("mera: ...")
    text = re.sub(r"\b(?:a+h+|u+m+|h+m+)\b[.,]?", " ", text, flags=re.I)  # bharaav: "aaah", "umm"
    text = re.sub(r"\b(?:chhe|chhah|chye|che|chah)\s+(baje|bajay|vajay|wajay|vaje|waje)\b", r"6 \1", text, flags=re.I)
    return translit.to_roman(" ".join(text.split()).strip())


_OFFSETS = {0x0980: 0x80, 0x0A00: 0x100, 0x0A80: 0x180}  # Bengali, Gurmukhi, Gujarati -> Devanagari


# ---------- Bahar ke liye ----------
def transcribe(audio, lang="auto", partial=False):
    """Recording (koi bhi format) -> Roman Hinglish text. partial=True: bolte waqt ka adhoora text (live dikhane ke liye)."""
    if not ready():
        raise OSError("Whisper taiyar nahi hai")
    wav = to_wav(audio)
    SERVER.last_used = time.time()
    lang = LANGS.get(lang, "auto")
    prompt = build_prompt()
    with _LOCK:
        text = None
        if WHISPER_SERVER:
            try:
                text = _via_server(wav, lang, prompt, partial)
            except (OSError, ValueError):
                text = None  # server mein dikkat: neeche cli se try
        if text is None:
            text = _via_cli(wav, lang, prompt, partial)
    if not partial:
        _keep_recording(wav)
    return correct(_clean(text))


RECORDINGS = Path(__file__).resolve().parent / "recordings"
KEEP_RECORDINGS = 10


def _keep_recording(wav):
    """Aakhri 10 recordings isi Mac par (git se bahar): galat sunne par asli awaaz se test kar sakein."""
    if len(wav) < 32000:  # 1 second se chhoti (jaise warm-up ki khamoshi): rakhne layak nahi
        return
    try:
        RECORDINGS.mkdir(exist_ok=True)
        (RECORDINGS / f"{time.strftime('%Y%m%d-%H%M%S')}.wav").write_bytes(wav)
        for old in sorted(RECORDINGS.glob("*.wav"))[:-KEEP_RECORDINGS]:
            old.unlink(missing_ok=True)
    except OSError:
        pass


def idle_shutdown(idle_seconds=900):
    """Awaaz der tak use nahi hui to whisper-server band kar do (~700 MB memory chhoot jati hai).
    Agli baar mic dabate hi prewarm() use wapas chalu kar deta hai (~1.5 s)."""
    if SERVER.running() and SERVER.last_used and time.time() - SERVER.last_used > idle_seconds:
        SERVER.stop()
        return True
    return False


def prewarm():
    """Mic button dabte hi background mein server chalu (cold start bolne ke samay mein chhip jata hai)."""
    model = best_model()
    if model and WHISPER_SERVER:
        try:
            SERVER.ensure(model)
        except OSError:
            pass


def warm_up():
    """Server chalu karke ek baar khamoshi sunwa do, taaki pehli asli recording tez ho."""
    if ready():
        try:
            transcribe(silence_wav())
        except (OSError, subprocess.SubprocessError):
            pass


def shutdown():
    SERVER.stop()
