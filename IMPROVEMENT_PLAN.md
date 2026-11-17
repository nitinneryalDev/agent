# Improvement scope: kya behtar ho sakta hai (14 Nov 2026)

Kaise naapa: 6 hisson ki jaanch (reliability, product, samajh, awaaz, UI, quality).
- Reliability aur product ke analyst ne poora kaam kiya.
- Baaki 4 usage-limit ki wajah se beech mein ruke. Unka bacha hua data (test runs, screenshots, Whisper naap, coverage) maine padha aur sabse zaroori daave khud dobara chalaye.
- Alag reviewer (jo har daave ko galat saabit karne ki koshish karta) limit ki wajah se nahi chal paya.

"Jaanch" column ka matlab:
- **✔** = maine code padhkar ya command chalakar khud dekha.
- **A** = analyst ka naap, maine dobara nahi chalaya.

## 1. Sabse pehle: reminder ke bugs (chhota kaam, roz ka asar)

| # | Kya galat hai | Saboot | Fix | Kaam | Jaanch |
|---|---|---|---|---|---|
| 1 | "roz / har somvar" reminder ek baar bajkar hamesha ke liye chup ho jata hai, agar us din done tick na kiya | `planner.py:100-103`: agla din sirf `complete_task` set karta hai. `planner.py:119-130`: notify ke baad `notified=1`. Fake clock par 10 din mein 1/10 baar baja | `check_and_notify_due_tasks` mein recurring row ko pichhli beeti occurrence par le jao aur `notified=0` karo. Saalana ("har saal", birthday) bhi jodo | S | ✔ code |
| 2 | Bina ghante wale reminder ("kal subah doodh…", "kal bill bharna") raat 23:59 par bajte hain | `planner.py:27-28` tareekh ko 23:59 bana deta hai. `when.parse` "kal subah" ko sirf tareekh deta hai. Asli data: 12 mein se 6 reminder 23:59 par | Subah 9, dopahar 2, shaam 6, raat 9 default. Sirf tareekh = us din subah 9 baje alert (`remind_at` column). Jawab mein bolo "subah 9 baje yaad dilaunga" | S | ✔ code + run |
| 3 | Notification: title AppleScript mein jaata hai (sirf `"` escape hota hai, `\` nahi), isliye khaas title shell command chala sakta hai. Backslash wala title fail ho jaata hai, aur fail hone par bhi "bhej diya" maana jaata hai | `planner.py:107-116`, `:127-129` | `osascript -e 'on run argv' … title message` (text argv se, script mein nahi). returncode check karo, fail ho to `notified=0`, retry | S | ✔ code |
| 4 | Backup: same din restart = us din ka achha backup overwrite. `ASSISTANT_DB` ko nazarandaaz karke hamesha project ke `backups/` mein. Sirf startup par chalta hai | `db.py:146-149`. Lamba chalta dashboard naya backup nahi leta | `DB_PATH.parent/backups`, overwrite nahi (`_HHMM`), pehle `PRAGMA quick_check`, roz ek baar reminder loop se. Restore ka command (`python3 db.py restore`, SQLite backup API se, WAL-safe) | S | ✔ code |
| 5 | Reminder sirf tab bajte hain jab `dashboard.py` chalu ho | Checker ka akela caller `dashboard.py:611-623`. Koi LaunchAgent nahi | `remind.py` + LaunchAgent (har 60 s, login par), ya dashboard ko login par chalao | M | A |

## 2. Samajh (accuracy)

**Naap:**
- 70 nayi lines par strict 32/70 (46%), naram judge 41/70.
- Purane 40 cases 40/40 hain, kyunki router un lines ke hisaab se tune hua hai (overfit).
- Category ke hisaab se: multi-intent 0/3, recurring 0/3, query 0/2, pronoun 0/2, ASR-noisy 2/5, reminder-time 7/10. Devanagari 4/4 aur notes 2/2 poore sahi.

| Wajah | Udaharan (asli run) | Fix (code mein) | Kaam | Jaanch |
|---|---|---|---|---|
| Type kiye text par spelling-map nahi lagta (sirf awaaz par lagta hai) | "kal sham 7 bajay doodh lana yad dilana" → koi tool nahi. "kl 8 bje gym…" → `log_health` | Har input par `voice.correct(text, fuzzy=False)` | S | ✔ run |
| `when.py` ki kamiyan | Raat ko "7 baje gym" → kal 19:00 (07:00 chahiye). "subha" nahi pehchanta. "tomorrow at 7" → sirf tareekh. "agle mahine 20 tareekh" → is mahine. "agle saal june" → kuch nahi | Bina subah/shaam wale ghante ke liye agla aane wala samay (raat 1-5 chhodkar). "subha", "at N", "agle mahine/saal" jodo | S | ✔ run |
| Router ki kamiyan | "reading habit band kar do" → `add_habit`. "umbrella wali entry mita do" → `remember_item`. "gas cylinder book kar diya" → `add_thing`. "kal kya kya hai" / "is hafte kya pending hai" → koi tool nahi | Hatane ke shabd (band kar, mita, nikaal). "kar diya / bhar diya" + saved kaam ka naam = done. Agenda ke sawal → `list_tasks` (din ke filter ke saath) | S-M | ✔ run |
| Model value gadh leta hai | "mujhe neend aa rahi hai" → neend 8 ghante log. "aaj office mein kaam bahut tha" → `complete_task` | `_grounded`: number user ke text mein hona chahiye. Chit-chat guard | S | A |
| Multi-intent | Router line todta hai, par model sirf ek kaam karta hai | Har hissa code se alag turn mein | M | A |
| Recurrence kho jaati hai | Model title se "roz" hata deta hai → recurrence None | `_repair` mein recurrence user ke text se | S | A |
| Badalne ka koi tool nahi | "5 nahi 6 baje" → 3 duplicate reminder bane | `reschedule_task` (sirf saaf "shift / badal / N baje kar do" par) + correction code mein | M | A |

**Bana-banaya saamaan (scratchpad mein):**
- Analyst ka patch (U1-U6), jo sirf copy par lagaya gaya aur test nahi hua: `scratchpad/improve/understanding/patch_copy.py`.
- 70 lines: `scratchpad/improve/understanding/agent_eval_stress.json`. Pehla kadam: ise project mein naye eval ki tarah rakho, taaki aage overfit pakda jaye.

## 3. Awaaz

| Baat | Naap | Fix | Kaam | Jaanch |
|---|---|---|---|---|
| Poori window (1500) hi sabse sahi hai | Asli recordings par word error: 1500 = 30.6%, 1280 = 38.4%, 1024/768 = 45.8%. Final text ~0.93 s. Teeno commands ka matlab sahi. Synthetic Hinglish (Isha/Rishi/Lekha) par 36%: TTS ka apna uchchaaran galat hai, isliye wo test ke kaam ka nahi | Kuch nahi. Kal wala badlaav sahi tha | - | ✔ data dobara nikala |
| Lambi line beech mein kat jaati hai | Bolte waqt noise floor badhta hai, aur silence counter sirf "loud" frame par reset hota hai. Simulation (3 recordings + 200-450 ms gap): 14/18 baar beech mein kati. Floor freeze karne par 0/18 (+~85 ms) | `dashboard.js` `onaudioprocess`: speech shuru hone ke baad floor freeze. Beech ke frames par bhi silence reset | S | A |
| Bolna khatam → jawab ≈ 5.5 s | 1.3 s chuppi + 0.93 s final + 2 s countdown + ~1.3 s model | Countdown 1 s ka option. 0.5 s chuppi par pehle se final shuru (~0.8 s chhupta hai) | S-M | A |
| Sirf 3 asli recordings | Test ke liye bahut kam | Auto-send se pehle user jo text sudhaarta hai, us (awaaz, sahi text) jodi ko local save karo: apna voice eval apne aap banega | M | idea |

## 4. UI/UX

| Baat | Saboot | Fix | Kaam | Jaanch |
|---|---|---|---|---|
| Contrast kam | `--text-3` AA fail: dark 3.94:1, light 3.14:1 (dates, time, table header, placeholder). Checkbox/input border 1.45:1 (3:1 chahiye). Light theme `--good` 4.36:1 | `dashboard.css` tokens | S | A (hisaab) |
| Phone (390px) | "System" tab kat-ta hai (32px). Chat table screen se bahar. Placeholder kata. Settings ~100px lete hain. Today card chat ke neeche | Voice/Mic/Language ek settings popover mein. Tabs scroll ya icon. Table → stacked rows | M | ✔ screenshot |
| Focus kho jaata hai | Har poll par rows dobara bante hain, isliye keyboard focus BODY par chala jaata hai | Rows ko id se patch karo ya focus wapas do | S | A |
| Dialog aur navigation | ⌘K aur shortcuts dialog mein focus-trap nahi. `hashchange` listener nahi (back/forward se tab nahi badalta) | Focus-trap + `hashchange` | S | A |
| System KPI bhatkata hai | "avg LLM calls" shortcuts ko bhi ginta hai: 3 retry par bhi 0.8 dikhata hai aur status "good" | Sirf model turns par average | S | A |
| My data | Dates do format mein ("08 Nov…" aur "2026-11-07 16:44"). Belongings headers Hinglish, baaki English. Habits card mein badi khaali jagah | Ek date formatter, ek bhasha, card height auto | S | ✔ screenshot |
| Bhejna fail hone par | "Dobara bhejo" button nahi | Error bubble mein Retry | S | ✔ code |

## 5. Quality, tests, notes

| Baat | Saboot | Fix | Kaam | Jaanch |
|---|---|---|---|---|
| Test coverage 38% | dashboard.py 0% (524 lines), overview 0%, habits 26%, planner 39% (reminder loop untested: wahi bugs mile), replies 28% | Fake-clock reminder tests, overview/views/streak tests, dashboard routes ka smoke test | M | A (trace) |
| Notes eval galat raasta naapta hai | `run_eval.py:19` `search()` test karta hai, app `search_best()` use karti hai (`tools.py:125`, `dashboard.py:251`). hit@5: 34/46 vs 42/46 | `run_eval.py` mein `search_best` | S | ✔ code |
| "BM25" boost BM25 nahi hai | `notes.py:100-103` mein `ORDER BY rank` nahi: koi bhi 10 milte hisse boost pa jaate hain | Rank ke hisaab se boost: hit@1 36→39/46, MRR 0.832→0.868 | S | ✔ code, A naap |
| Galti par jawab hi nahi aata | Non-dict JSON, DB lock >10 s, disk full, health value "inf": koi HTTP jawab nahi, UI kehta hai "server band". "inf" se My data toot jaata hai (JSON Infinity) | `do_GET`/`do_POST` mein try/except → JSON 500/503. `isfinite` check. System tab par `db_ok` | M | A |
| Galat error message | Model na ho (404) to "Ollama nahi mil raha". Ek non-UTF-8 note se startup thread mar jaata hai (notes 0, warm-up nahi) | HTTPError ka asli message. `errors="replace"`. Har startup step alag try mein | S | A |
| Git | Staged snapshot purana hai (purana dashboard.html). `static/` aur `tests/` untracked. `*.db-wal`/`*.db-shm` ignore nahi | `.gitignore` mein `assistant.db-*`, `logs/`. Phir `git add -A` + commit | S | A |

## 6. Privacy aur system

| Baat | Saboot | Fix | Kaam | Jaanch |
|---|---|---|---|---|
| "New chat" se baatein sach mein nahi mitti | DB file mein 25/31 purane jawab ab bhi padhe ja sakte hain, aur 7 din backup mein | `PRAGMA secure_delete=ON`, reset par checkpoint, backup se `chat_messages` hatao | S | A |
| Anaath whisper-server | Parent `-9` se mare ya koi script transcribe kare, to ~700 MB pakde rehta hai (kal 13 ghante) | Watchdog/atexit, 15 min idle par band, mic dabate hi pre-warm | M | ✔ ps |

## 7. Naye features (aapke kaam ke hisaab se)

1. **Morning brief / evening review**, code se, bina model ke. "good morning", "aaj ka plan", "kal kya hai" ka jawab ~5 ms mein, aur tay samay par bolkar. (S-M)
2. **Snooze/reschedule.** Notification mein button: "10 min baad", "kal subah", "ho gaya". (M)
3. **Awaaz se note:** "note karo: …" → `my_data/inbox.md`, jo notes search mein bhi aaye. (S)
4. **⌘K se saved data dhundho:** cheezein, contacts, reminders. Abhi ye sirf navigation karta hai. (S)
5. **Settings table:** default reminder ghanta, brief ka samay, quiet hours, paani ka target. (S)
6. **Lena-dena (udhaar) hisaab:** "Rahul ko 500 diye". (M)
7. **Kisi bhi app se bolne ka hotkey:** Shortcuts.app + ffmpeg + `/api/transcribe`. (M)
8. **Call:** `call_contact` → Phone.app (`tel:`), sirf "haan" ke baad. (S)

Abhi nahi: phone se Wi-Fi access (auth/HTTPS ka bada kaam aur privacy khatra), export/import, naye note formats.

## Suggested order

1. Reminder bugs 1-4 + unke fake-clock unit tests.
2. Samajh: 70 lines ko project eval banao, phir U1-U4 fixes. Pehle aur baad ka naap lo (40/40 bana rehna chahiye).
3. Morning brief + snooze/reschedule.
4. UI quick wins: contrast tokens, phone layout, focus.
5. VAD freeze + awaaz ki sudhaari hui jodiyan save karna.
6. Auto-start (LaunchAgent), error handling, git commit.
