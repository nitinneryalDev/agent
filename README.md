# Private Personal Assistant

Tumhare laptop par chalne wala assistant. Saara data (notes, database, awaaz) isi folder mein rehta hai, bahar kuch nahi jata.

## Chalane se pehle

- Python 3.9 ya naya (koi extra Python library install nahi karni).
- Ollama app chalu ho, aur ye models downloaded hon:
  `ollama pull llama3.2` aur `ollama pull nomic-embed-text`
- Apni notes `my_data/` folder mein rakho (`.md` ya `.txt`, paragraph ke beech mein khali line).
- Offline awaaz ke liye (optional): `brew install ffmpeg whisper-cpp`, aur [huggingface.co/ggerganov/whisper.cpp](https://huggingface.co/ggerganov/whisper.cpp)
  se `models/ggml-large-v3-turbo-q5_0.bin` (~575 MB, sabse sahi) ya `models/ggml-small.bin` (~490 MB). Jo poora ho wahi chalta hai.

## Kya chalta hai (project folder se)

| Command | Kya karta hai |
|---|---|
| `python3 dashboard.py` | Browser mein `http://127.0.0.1:8001`: chat, aapka data, notes se sawal, system stats |
| `python3 agent.py` | Terminal mein assistant se baat (har tool ke baad status table) |
| `python3 run_agent_eval.py` | Assistant ka test: 40 Hinglish cases (kai-turn wale bhi) par sahi tool + arguments + time |
| `python3 run_eval.py` | Notes ka test: `eval_questions.json` ke sawalon par kitne jawab sahi |

## Dashboard ke chaar tab

Upar **Search or jump… (⌘K)**: ek jagah se tab badlo, nayi chat, awaaz, paani +1, theme, ya kuch bhi likhkar "assistant se poochho / reminder jodo". **?** dabao = saare keyboard shortcuts. My data ke cards band/khol sakte ho (yaad rehta hai), aur sidebar/cards mein seedha reminder ya habit jod sakte ho (samay code samajhta hai, model nahi).

- **Assistant**: chat. Likho ya mic se bolo: bolte waqt shabd **live** dikhte hain, chup hote hi 2 second baad bhej deta hai (Esc ya kuch type karo = roko). Har jawab ke saath kaunsa tool chala, data ka table, aur "Kaise kiya". Daayein "Aaj": habit ek click mein done, kaam done, paani +1.
- **Hatana (delete) hamesha poochhkar**: "doodh wala reminder hata do" → "Pakka hata doon? doodh lena (kal shaam 6 baje)" → "Haan" (bolo ya button) tabhi hatta hai. "Nahi", ya kuch aur bolna = kuch nahi hatta. My data mein har row par 🗑 button bhi pehle "Hata dein?" poochhta hai.
- **My data**: habits ka 14 din ka grid aur streak, pending kaam, health ke trend, goals ki progress, kitabein/joote, cheezein kahan hain, contacts.
- **Notes**: sirf notes se jawab (streaming), kaunse passages padhe gaye.
- **System**: assistant aur notes ki speed/quality, eval score, Whisper status, charts.

## Ek message ka safar (kyun tez aur sahi hai)

1. **Hindi lipi → Roman** (`translit.py`): "मेरा छाता कहाँ है" → "mera chhata kahan hai".
2. **Shortcut** (`shortcuts.py`): "walking ho gayi", "habits dikhao", "passport kahan hai", "hi": bina model ke, ~1 ms.
3. **Router** (`router.py`): 18 mein se sirf 1-3 kaam ke tools model ko. Database mein saved naam (habit, cheez, contact) sabse pakka ishara.
4. **Samay** (`when.py`): "parso subah 10 baje" → `2026-11-09 10:00`, "30 minute baad" → abhi + 30 min, code se, model ke andaze se nahi. Samay bola hi nahi to reminder bina samay ke (model apna samay nahi daal sakta).
5. **Model** tool chunta hai, phir code arguments jaanchta hai (naam user ke shabdon mein hai? din sahi hai?).
6. **Jawab** (`replies.py`): confirmation code likhta hai, isliye ek hi model call aur koi jhooth nahi. Notes ke sawal ka jawab tested notes prompt se.
7. **Hatana** (`tools.py`): model ke `remove_*` tools sirf poochhte hain. Asli `confirm_delete` model ki list mein hai hi nahi; wo sirf user ke "haan" (ya button ke token) par chalta hai.

## Awaaz (voice.py)

- `whisper-server` ek baar chalu hokar model memory mein rakhta hai, isliye har ~1 second live (adhoora) text aur ~0.5 s mein final text.
- Prompt mein Hinglish examples + aapke saved naam (habits, cheezein, contacts), aur chhoti recording ke liye chhoti "audio_ctx" khidki (turbo 2 s → 0.5 s).
- Galat-sune aam shabd theek: "phoon" → "phone", "aaad" → "yaad", "perso" → "parso", "bajay" → "baje". Saved naam kabhi nahi badalte.

Nateeja (Nov 2026, llama3.2 3B, isi Mac par): shuru mein 16/26 sahi aur ~3.3 s; ab 40/40 (hatane wale flows samet) aur ~1.2 s average (system prompt ko cache-friendly banane ke baad).
Bilkul nayi 12 lines par pehli baar 11/12 (92%) aaye the.

## Files

| File | Kaam |
|---|---|
| `config.py` | Saari settings (models, folders, port, Whisper model) |
| `llm.py` | Ollama se baat (model 30 min memory mein rehta hai) |
| `notes.py` | Notes mein search (RAG), vectors ki disk cache |
| `db.py` | Database aur uske saare tables |
| `items.py`, `contacts.py`, `planner.py`, `health.py`, `habits.py`, `things.py` | Har cheez ka data |
| `tools.py` | Wo tools jo model bula sakta hai |
| `translit.py`, `shortcuts.py`, `router.py`, `when.py`, `replies.py` | Upar wala "safar" |
| `agent.py` | Sab jodne wala: message → jawab |
| `views.py`, `overview.py` | Tables aur dashboard ka data |
| `dashboard.py`, `dashboard.html`, `static/dashboard.css`, `static/dashboard.js` | Web dashboard: server, markup, design system (rang/type/spacing tokens), aur UI ka code |
| `voice.py` | Offline awaaz se text (whisper-server, prompt, galat shabd theek) |
| `run_agent_eval.py`, `agent_eval_cases.json` | Assistant ka eval (kai-turn bhi, jaise "hata do" → "haan"). `agent_eval_holdout.json`, `agent_eval_blind.json`, `agent_eval_adversarial.json`: nayi lines |
| `run_eval.py`, `eval_questions.json` | Notes ka eval |
| `OPTIMIZATION_PLAN.md` | Kahan samay jaata hai (naap), kya optimize kiya, aage kya |

## Privacy

- `assistant.db`, `my_data/`, `history.jsonl`, `embed_cache.json` mein personal data hai. `.gitignore` inhe git se bahar rakhta hai.
- Dashboard sirf `127.0.0.1` par sunta hai, network par nahi.
- Whisper aur `say` dono isi Mac par chalte hain. Sirf "Browser" mic (Chrome/Safari) awaaz Google/Apple ko bhejta hai.
- Model khud kuch delete nahi kar sakta: uske `remove_*` tools sirf poochhte hain, asli delete sirf aapke "haan" par. Shell ya internet wala koi tool nahi.
