# Private Personal Assistant

Tumhare laptop par chalne wala assistant. Saara data (notes, database) isi folder mein rehta hai, bahar kuch nahi jata.

## Chalane se pehle

- Python 3.9 ya naya (koi extra library install nahi karni).
- Ollama app chalu ho, aur ye models downloaded hon:
  `ollama pull llama3.2` aur `ollama pull nomic-embed-text`
- Apni notes `my_data/` folder mein rakho (`.md` ya `.txt`, paragraph ke beech mein khali line).

## Teen cheezein jo chalti hain (project folder se)

| Command | Kya karta hai |
|---|---|
| `python3 agent.py` | Assistant se baat karo: cheezein, contacts, kaam, goals, health, habits, kitabein, kapde, notes |
| `python3 dashboard.py` | Browser mein `http://127.0.0.1:8000`: notes se sawal-jawab aur live stats |
| `python3 run_eval.py` | Test: `eval_questions.json` ke sawalon par kitne jawab sahi aaye |

## Files

| File | Kaam |
|---|---|
| `config.py` | Saari settings (models, folders, port) |
| `llm.py` | Ollama se baat |
| `notes.py` | Notes mein search (RAG) |
| `db.py` | Database aur uske saare tables |
| `items.py` | Cheez kahan rakhi hai |
| `contacts.py` | Contacts aur nicknames |
| `planner.py` | Kaam, reminders, goals |
| `health.py` | Roz ke health numbers |
| `habits.py` | Roz ki aadatein aur streak |
| `things.py` | Kitabein, jootein, kapde (details ke saath) |
| `tools.py` | Wo tools jo model bula sakta hai |
| `agent.py` | Model + tools ka chat |
| `dashboard.py`, `dashboard.html` | Web dashboard |
| `run_eval.py`, `eval_questions.json` | Eval |

## Privacy

- `assistant.db`, `my_data/`, `history.jsonl` mein personal data hai. `.gitignore` inhe git se bahar rakhta hai.
- Dashboard sirf `127.0.0.1` par sunta hai, network par nahi.
- Model ko delete, shell ya internet wala koi tool nahi diya gaya.
# agent
