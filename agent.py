#!/usr/bin/env python3
"""Personal assistant: tum bolo, assistant tay karta hai kaunsa tool chalana hai.

Ek message ka safar:
  1. Hindi lipi ho to Roman Hinglish mein badlo (translit.py)
  2. Bilkul seedhi baat ho to bina model ke jawab (shortcuts.py)       -> milliseconds
  3. Warna sirf kaam ke 1-3 tools chuno (router.py), samay ke shabd tareekh mein badlo (when.py)
  4. Model tool chune -> tool chale -> jawab code khud likhe (replies.py) -> zyaadatar ek hi model call

Chalane ka tareeka:   python3 agent.py
"""
import json
import re
import secrets
import time
from datetime import datetime, timedelta

import health
import llm
import notes
import planner
import replies
import router
import shortcuts
import things
import tools as tools_module
import translit
import views
import voice
import when
from tools import TOOL_FUNCTIONS, confirm_delete, run_tool, schemas_for

MAX_STEPS = 4      # ek sawal par model zyada se zyada itni baar bulaya ja sakta hai
MAX_HISTORY = 12   # pichhle itne messages hi model ko bhejte hain (chhota prompt = tez jawab)
# Ye galtiyan model khud sudhaar sakta hai (format galat tha): inhe model ko wapas dikhate hain.
RETRYABLE = ("Wrong arguments", "Unknown tool", "Arguments must", "Tareekh aise", "day aise", "days number",
             "target_date aise", "kind inme se", "value number", "category aur name", "Kaunsa kaam", "Kaunsi cheez",
             "Cheez saved nahi")

# Hatane se pehle "pakka?" ka jawab: itni der tak hi maana jata hai, aur sirf agle hi message mein.
CONFIRM_TTL_S = 600
YES = {"haan", "han", "ha", "haa", "haan ji", "haanji", "ji", "ji haan", "yes", "y", "yeah", "yep", "ok", "okay",
       "theek hai", "thik hai", "kar do", "hata do", "hatao", "haan hatao", "haan hata do", "sure", "confirm",
       "bilkul", "pakka", "haan pakka", "yes please", "ha hata do", "haan kar do"}
NO = {"nahi", "nahin", "na", "no", "nope", "mat", "mat karo", "mat hatao", "cancel", "rehne do", "ruko", "chhodo",
      "nai", "nahi hatana", "mat hatana", "nahi nahi", "no thanks", "rukho", "abhi nahi"}

SYSTEM_PROMPT = """You are a private personal assistant that runs only on the user's laptop. You act by calling tools.
Today: {now}. kal (tomorrow) = {tomorrow}. parso = {day_after}.
Rules:
- To save, find, update, list or log anything, call a tool. Never say something is saved unless a tool did it. Never guess saved data.
- Dates for tools: YYYY-MM-DD, or YYYY-MM-DD HH:MM (24 hour). subah = morning, dopahar = afternoon, shaam = evening (6 baje shaam = 18:00), raat = night (9 baje raat = 21:00).
- Copy names, titles and places EXACTLY from the user's message. Never use names from these rules.
- "<habit> ho gayi / kar li" -> check_in_habit(habit). "<name> naam ki habit shuru karo" -> add_habit(name).
- The user STATES a book/shoes/shirt/dress they own -> add_thing(category = book/shoe/shirt/dress/clothes, name, details object like {{"color": "<color>"}}, place). A book title can contain words like "Habits"; it is still a book. "<book> khatam ho gayi / padh li" -> update_thing(thing, status="finished").
- "<task> ho gaya" -> complete_task(task = a few words of that task). Reminder ("yaad dilao") -> add_task(title = short task in the user's words, due).
- log_health only for numbers: glasses of water, hours of sleep, minutes of training, energy 1-10.
- The user STATES where an object is ("<object> <place> mein hai") -> remember_item(item = <object>, place = <place>). ASKS where -> find_item.
- search_notes only to answer a QUESTION about the user's own life (job, family, hometown, birthday, goals).
- To delete, remove or cancel something ("hata do", "delete", "cancel") call the matching remove_* tool. It only ASKS the user to confirm; never say it is already deleted.
- If no tool fits, reply briefly. Never invent facts about the user (birthday, family, plans): if you don't know, say so.
- Always reply in short, simple Hinglish using English letters only, never Devanagari."""

# Samay jaisa koi bhi ishara. Ye ho aur when.py na samjhe, to model ka (jaancha hua) samay rehne do.
TIME_WORDS = re.compile(
    r"\d|\b(?:baje|bje|bajay|baad|bad|ghante|ghanta|minute|min|din|hafte|hafta|mahine|tareekh|tarikh|date|subah|"
    r"savere|dopahar|shaam|sham|raat|kal|parso|aaj|tomorrow|today|tonight|morning|evening|night|week|month|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|somvar|mangalvar|budhvar|guruvar|shukravar|"
    r"shanivar|ravivar|itvaar|jan\w*|feb\w*|march|april|may|june|july|aug\w*|sep\w*|oct\w*|nov\w*|dec\w*)\b",
    re.IGNORECASE)

FALLBACK = "Samajh nahi paya. Thoda saaf likho, jaise 'kal shaam 6 baje doodh lena yaad dilao'."
NUDGE = "You did not call a tool. Call one of these tools now: {names}. Reply only with the tool call."


def system_message():
    """System prompt din bhar EK JAISA rehta hai (sirf tareekh, minute nahi). Isse Ollama pichhle turn ka
    KV-cache dobara use karta hai: naap mein prompt-processing ~1160 ms se ~200 ms, har turn ~0.9 s tez.
    Samay (minute) ka kaam when.py karta hai, aur uska hint aakhri user message ke saath jata hai."""
    now = datetime.now()
    content = SYSTEM_PROMPT.format(now=now.strftime("%A, %Y-%m-%d"),
                                   tomorrow=(now + timedelta(days=1)).strftime("%Y-%m-%d"),
                                   day_after=(now + timedelta(days=2)).strftime("%Y-%m-%d"))
    return {"role": "system", "content": content}


def _with_hint(messages, hint, part=None):
    """Samay ka hint (aur multi-intent mein "abhi sirf is hisse par kaam karo") sirf aakhri user message mein,
    copy par. System prompt cache-friendly rehta hai."""
    note = ""
    if part:
        note += f'\n[Work ONLY on this part now: "{part}". The other parts are handled separately.]'
    if hint:
        note += f'\n[Time words in this message mean {hint}. Use exactly due = "{hint}".]'
    if not note:
        return messages
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            return messages[:i] + [{**messages[i], "content": messages[i]["content"] + note}] + messages[i + 1:]
    return messages


def warm_up():
    """Model ko pehle se memory mein load karo (pehla sawal tez ho)."""
    return llm.warm_up()


def _recent(history):
    """Pichhle kuch messages, par hamesha kisi user message se shuru (aadha tool-chakkar model ko confuse karta hai).
    "_" se shuru hone wali keys (jaise _pending) sirf hamare liye hain: model ko nahi bhejte."""
    recent = history[-MAX_HISTORY:]
    while recent and recent[0].get("role") != "user":
        recent = recent[1:]
    return [{k: v for k, v in m.items() if not k.startswith("_")} for m in recent]


def _parse(result):
    try:
        data = json.loads(result)
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _json_objects(text):
    """Text ke andar ke saare {...} JSON tukde (nested bhi), unki jagah (start, end) ke saath."""
    found, depth, start = [], 0, None
    for i, ch in enumerate(text or ""):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0:
                try:
                    found.append((start, i + 1, json.loads(text[start:i + 1])))
                except ValueError:
                    pass
    return found


def _tool_call_in_text(content):
    """llama3.2 kabhi tool call ko text mein likh deta hai: {"name": "add_task", "parameters": {...}}. Use pakdo."""
    for _, _, data in _json_objects(content):
        if isinstance(data, dict) and data.get("name") in TOOL_FUNCTIONS:
            arguments = data.get("parameters", data.get("arguments", {}))
            return {"function": {"name": data["name"], "arguments": arguments if isinstance(arguments, dict) else {}}}
    return None


def _calls_from_text(content, allowed):
    call = _tool_call_in_text(content)
    return [call] if call and call["function"]["name"] in allowed else []


def _clean_reply(text):
    """Model ke jawab se JSON/tool-call jaisa kachra hatao (user ko kabhi {"name": ...} na dikhe)."""
    text = text or ""
    for start, end, data in reversed(_json_objects(text)):
        if isinstance(data, dict) and ({"name", "parameters", "arguments"} & set(data)):
            text = text[:start] + text[end:]
    lines = [line for line in text.splitlines()
             if not re.match(r"^\s*[a-z]+_[a-z_]+\s*(?:\(|\w+\s*=)", line)]
    return " ".join(" ".join(lines).split()).strip(" `\"'")


def _valid_due(value):
    try:
        planner.parse_due(value)
        return True
    except ValueError:
        return False


def _repair(name, arguments, context):
    """Arguments mein jaani-pehchaani galtiyan theek karo, model ko dobara bulaye bina."""
    arguments = dict(arguments) if isinstance(arguments, dict) else {}
    if name in ("check_in_habit", "log_health"):
        # Check-in aur log beete hue kaam hain: din user ke shabdon se lo ("kal" = beeta kal), model ke andaze se nahi.
        day = when.past_day(context["text"])
        if day:
            arguments["day"] = day
        else:
            arguments.pop("day", None)  # din nahi bola = aaj
    if name == "log_health":
        kind = health.kind_in(context["text"])
        if kind:
            arguments["kind"] = kind  # "7 ghante soya" = sleep, chahe model kuch aur likhe
    if name in REMOVE_FIELDS:
        field, keys = REMOVE_FIELDS[name]
        target = str(arguments.get(field) or "")
        if not target or set(re.findall(r"[a-z]+", target.lower())) <= _POINTER_WORDS:
            # "ye reminder hata do": pichhli baat ki cheez ka naam lo. Phir bhi "Pakka? <naam>" poochha jayega.
            remembered = _last_mentioned(context.get("history", []), keys)
            if remembered:
                arguments[field] = remembered
    if name == "search_notes":
        arguments["original"] = context["text"]  # model ke English sawal ke saath user ke apne shabd bhi
    if name == "add_task":
        recurrence = when.parse_recurrence(context["text"])
        if recurrence:
            arguments["recurrence"] = recurrence  # "roz subah 7 baje" ka 'roz' model ke title se kho jata hai
    if name == "add_goal":
        # Model aksar beeti tareekh bana deta hai ("june" = is saal ki June). User ke shabdon se nikli tareekh pakki hai.
        hint = context.get("when")
        try:
            target_ok = planner.parse_target_date(arguments.get("target_date")) >= datetime.now().strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            target_ok = False
        if not target_ok and hint:
            arguments["target_date"] = hint[:10]
    if name == "log_health":
        said_kind = health.KIND_SYNONYMS.get(str(arguments.get("kind", "")).strip().lower(),
                                             str(arguments.get("kind", "")).strip().lower())
        if said_kind == "hydration" and re.search(r"\baur\b|\bmore\b", context["text"].lower()):
            already = health.value_on("hydration", arguments.get("day"))
            try:
                arguments["value"] = (already or 0) + float(arguments.get("value") or 0)  # "2 glass aur" = total + 2
            except (TypeError, ValueError):
                pass
    if name == "find_things":
        category = things.category_in(context["text"])
        if category and not arguments.get("category"):
            arguments["category"] = category
        if arguments.get("query") and not things.meaningful_words(arguments["query"]):
            arguments.pop("query")  # "mere paas" jaisa khali query: sab dikhao
    if name == "add_task" and arguments.get("title"):
        arguments["title"] = planner.clean_title(arguments["title"])  # "dentist subah 10 baje yaad dilana" -> "dentist"
    hint = context.get("prompt_hint") or context.get("when")
    if name == "add_task" and not hint and not TIME_WORDS.search(context["text"]):
        arguments.pop("due", None)  # user ne samay jaisa kuch bola hi nahi: model ka banaya samay mat lagao
    if name == "add_task" and hint:
        due = str(arguments.get("due") or "").strip()
        wrong_day = not _valid_due(due) or due[:10] != hint[:10]
        # User ne ghanta bola hi nahi (hint sirf tareekh) to model ka banaya hua samay bhi hata do.
        wrong_time = (len(hint) > 10 and due[11:16] != hint[11:16]) or (len(hint) == 10 and len(due) > 10)
        if wrong_day or wrong_time:
            arguments["due"] = hint  # user ke apne shabdon se nikli tareekh model ke andaze se zyada pakki hai
    return arguments


# Model ke ye arguments user ke apne shabdon se aane chahiye. Na mile = model ne kahin aur se naam utha liya.
GROUNDED_FIELDS = {"remember_item": "item", "add_thing": "name", "add_habit": "name", "add_task": "title",
                   "add_contact": "name", "add_goal": "title", "update_thing": "thing", "check_in_habit": "habit",
                   "complete_task": "task", "find_item": "query", "call_contact": "name"}
# remove_* yahan nahi: "ye reminder hata do" mein naam nahi hota. Wahan suraksha "Pakka hata doon: <naam>?" hai.
REMOVE_FIELDS = {"remove_task": ("task", ("task_id", "title")), "remove_item": ("item", ("item",)),
                 "remove_thing": ("thing", ("thing_id", "name")), "remove_habit": ("habit", ("habit_id", "name", "habit")),
                 "remove_goal": ("goal", ("goal_id", "title")), "remove_contact": ("name", ("name",))}
_POINTER_WORDS = {"ye", "yeh", "isko", "isse", "iska", "usko", "use", "wo", "woh", "vo", "pichhla", "pichla", "last",
                  "reminder", "task", "kaam", "entry", "cheez", "habit", "goal", "contact", "wala", "wali", "wale"}


def _last_mentioned(history, keys):
    """Pichhli baat mein jis cheez ka zikr hua (jaise abhi bana 'yoga' reminder), uska naam."""
    for message in reversed(history):
        if message.get("role") != "tool":
            continue
        data = _parse(message.get("content", ""))
        for key in keys[1:]:
            if data.get(key):
                return str(data[key])
    return None


def _words(text):
    return {w for w in re.findall(r"[a-z0-9]+", str(text).lower()) if len(w) >= 3}


def _grounded(name, arguments, text, previous=""):
    """True agar argument ka koi shabd (3+ akshar) user ke message (ya "usko/wo" ke liye pichhle message) mein ho,
    ya argument number ho."""
    field = GROUNDED_FIELDS.get(name)
    value = arguments.get(field) if field else None
    if not value or str(value).isdigit():
        return True
    said = _words(text) | _words(previous)
    return any(w in said or any(s.startswith(w[:4]) for s in said if len(w) >= 4) for w in _words(value))


def _friendly_error(error):
    if error.startswith("Tareekh aise"):
        return "Samay samajh nahi aaya. Aise bolo: 'kal shaam 6 baje doodh lena yaad dilao'."
    if error.startswith(("Wrong arguments", "Unknown tool", "Arguments must")):
        return "Samajh nahi paya kis cheez ki baat hai. Naam ke saath bolo, jaise 'doodh wala reminder hata do'."
    return f"Ye nahi ho paya: {error}"


def _run_calls(calls, history, on_tool, context, outcome):
    """Model ke maange tools chalao. Lautata hai: kya model ko dobara bulana padega?"""
    needs_model = False
    for call in calls:
        name = call["function"]["name"]
        arguments = _repair(name, call["function"].get("arguments") or {}, context)
        if _grounded(name, arguments, context["text"], context.get("prev_text", "")):
            result = run_tool(name, arguments)
        else:
            field = GROUNDED_FIELDS[name]
            result = json.dumps({"error": f"Wrong arguments: '{arguments.get(field)}' is not in the user's message. "
                                          f"Use the user's own words for {field}."})
        history.append({"role": "tool", "tool_name": name, "content": result})
        if on_tool:
            on_tool(name, arguments, result)  # dashboard ya terminal ko batao ki tool chala
        data = _parse(result)
        error = data.get("error")
        if error and error.startswith(RETRYABLE):
            outcome["last_error"] = error
            needs_model = True
        elif error:
            outcome["replies"].append(error)  # asli galti (jaise "habit nahi mili") seedha dikhao
        elif name == "search_notes":
            outcome["success"] = True
            # Notes ka jawab usi tested prompt se jo "Ask my notes" mein hai (eval 9/9), agent ke lambe prompt se nahi.
            passages = [(p["score"], {"source": p["file"], "text": p["text"]}) for p in data.get("passages", [])]
            started = time.perf_counter()
            outcome["replies"].append(notes.answer(data.get("question") or context["text"], passages) or FALLBACK)
            outcome["llm_ms"] = outcome.get("llm_ms", 0) + round((time.perf_counter() - started) * 1000)
        else:
            outcome["success"] = True
            if "confirm" in data:
                outcome["pending"] = data["confirm"]  # hatane ka sawal: user ke "haan" ka intezaar
                outcome["confirms"] = outcome.get("confirms", 0) + 1
            text = replies.reply_for(name, arguments, data)
            if text is None:
                needs_model = True
            else:
                outcome["replies"].append(text)
    return needs_model


def _finish(history, final, outcome, info):
    """Aakhri jawab history mein likho. Hatane ka sawal poochha ho to uska token bhi saath rakho."""
    message = {"role": "assistant", "content": final}
    pending = outcome.get("pending")
    if pending and outcome.get("confirms") == 1:  # ek hi hatane ka sawal ho tabhi "haan" ka matlab saaf hai
        pending = {**pending, "token": secrets.token_hex(4), "ts": time.time()}
        message["_pending"] = pending
        info["pending"] = pending
    history.append(message)
    return final


def _chat_loop(history, on_tool, offered, context, info):
    schemas = schemas_for(offered)
    outcome = {"replies": [], "success": False, "last_error": None}
    nudged = False
    rerouted = False
    for _ in range(MAX_STEPS):
        messages = [system_message()] + _with_hint(_recent(history), context.get("prompt_hint"), context.get("part"))
        if nudged == "pending":
            messages.append({"role": "user", "content": NUDGE.format(names=", ".join(offered))})
            nudged = True
        started = time.perf_counter()
        reply = llm.chat(messages, tools=schemas or None)
        info["llm_calls"] = info.get("llm_calls", 0) + 1
        info["llm_ms"] = info.get("llm_ms", 0) + round((time.perf_counter() - started) * 1000)
        calls = reply.get("tool_calls") or _calls_from_text(reply.get("content", ""), offered)
        guessed = None if calls else _tool_call_in_text(reply.get("content", ""))
        if guessed and not offered and not rerouted:
            # Router ko topic nahi mila, par model tool chalana chahta hai: ek baar asli tools dekar dobara poochho.
            name = guessed["function"]["name"]
            offered = router.ALL_TOOLS + ([name] if name not in router.ALL_TOOLS else [])
            schemas, rerouted = schemas_for(offered), True
            info["tools_offered"], info["route"] = offered, "model"
            context["prompt_hint"] = context.get("when")
            continue
        history.append({"role": "assistant", "content": reply.get("content", "") if not calls else "",
                        **({"tool_calls": calls} if calls else {})})
        if not calls:
            if offered and not nudged and not outcome["success"] and not outcome["replies"] and not outcome["last_error"]:
                history.pop()  # model ne tool nahi bulaya: ek baar yaad dilao
                nudged = "pending"
                continue
            text = _clean_reply(reply.get("content", ""))
            if not outcome["success"] and outcome["last_error"]:
                text = _friendly_error(outcome["last_error"])  # model "ho gaya" na bole jab hua hi nahi
            final = " ".join(outcome["replies"] + ([text] if text else [])) or FALLBACK
            history.pop()
            return _finish(history, final, outcome, info)
        needs_model = _run_calls(calls, history, on_tool, context, outcome)
        if outcome.get("llm_ms"):
            info["llm_calls"] = info.get("llm_calls", 0) + 1
            info["llm_ms"] = info.get("llm_ms", 0) + outcome.pop("llm_ms")
        if not needs_model:
            return _finish(history, " ".join(outcome["replies"]) or FALLBACK, outcome, info)
    if outcome["last_error"] and not outcome["success"]:
        return _friendly_error(outcome["last_error"])
    return " ".join(outcome["replies"]) or "Mujhe ye poora nahi ho paya. Sawal thoda chhota karke dobara poochho."


def _open_pending(history):
    """Pichhla assistant message hatane ka sawal tha aur abhi bhi taaza hai? To wo sawal, warna None."""
    if not history or history[-1].get("role") != "assistant":
        return None
    pending = history[-1].get("_pending")
    if not pending or time.time() - pending["ts"] > CONFIRM_TTL_S:
        return None
    return pending


# "haan"/"nahi" ke baad sirf yahi shabd hon tabhi jawab maana jata hai. "haan gym bhi yaad dilao" confirmation NAHI hai.
_YES_TAIL = {"haan", "han", "ha", "ji", "hata", "hatao", "do", "de", "dena", "dijiye", "kar", "karo", "please", "bilkul",
             "pakka", "theek", "thik", "hai", "ok", "okay", "sure", "yes", "confirm", "zaroor"}
_NO_TAIL = {"nahi", "nahin", "nai", "no", "mat", "hatao", "hatana", "rehne", "do", "abhi", "yaar", "bhai", "ruko", "cancel",
            "karo", "please", "thanks", "chhodo", "rukho"}


def _decision(text):
    """'yes' / 'no' / None (kuch aur bola). Shak ho to None: kuch hatane se behtar hai dobara poochhna."""
    clean = router.normalize(text)
    words = clean.split()
    if not words:
        return None
    if clean in NO or (words[0] in {"nahi", "nahin", "no", "mat", "nai"} and set(words[1:]) <= _NO_TAIL):
        return "no"
    if clean in YES or (words[0] in {"haan", "han", "yes", "ji", "ha", "haa"} and set(words[1:]) <= _YES_TAIL):
        # "haan?"/"ji?" = "kya bola?", "pakka?" = "sach mein?": sawal hai, haan nahi. "ha ha" hansi bhi ho sakti hai.
        if "?" in text or (len(words) > 1 and set(words) == {"ha"}):
            return "unclear"
        return "yes"
    return None


def _handle_confirmation(history, text, pending, decision, on_tool, info):
    history.append({"role": "user", "content": text})
    info.update(route="confirm", tools_offered=[], confirm_result=decision)
    if decision == "yes":
        arguments = {"kind": pending["kind"], "target": pending["id"], "name": pending.get("name"),
                     "label": pending["label"]}
        try:
            result = json.dumps(confirm_delete(**arguments), ensure_ascii=False)
            final = f"Hata diya: {pending['label']}."
        except ValueError as error:
            result = json.dumps({"error": str(error)}, ensure_ascii=False)
            final = str(error)
        if on_tool:
            on_tool("confirm_delete", arguments, result)
    else:
        final = f"Theek hai, nahi hataya: {pending['label']}."
    history.append({"role": "assistant", "content": final})
    return final


# ---------- Samay badalna (reschedule / correction / snooze): model ke bina, seedha code se ----------
RESCHED_WORDS = {"shift", "badal", "badlo", "badalo", "badalna", "postpone", "reschedule", "resched",
                 "sarkao", "sarka", "khiskao", "khiska"}
_RESCHED_HINT = re.compile(r"\bki jagah\b|\bkar (?:do|dena|de)\b|\bpe (?:kar|shift)\b|\bpar (?:kar|shift)\b")
_TASK_NOUN = re.compile(r"\b(?:wala|wale|wali|reminder|task|kaam|meeting|appointment|alarm|usko|isko|use|ise|wo|ye)\b")
_SNOOZE = re.compile(r"\bsnooze\b|\b(?:thodi der|baad mein|abhi nahi)\b.*\byaad\b|"
                     r"\b(\d{1,3})\s*(?:min\w*|ghant\w*)\s*baad\b.*\b(?:phir|dobara|wapas|yaad)\b")
_CORRECTION = re.compile(r"^\s*(?:nahi|nhi|nahin|no|sorry|arre|are|oops|galat)\b")


def _last_task_in_history(history):
    """History ke tool results mein aakhri bana/badla task (id ke saath), jo abhi bhi pending ho."""
    for message in reversed(history[-10:]):
        if message.get("role") != "tool":
            continue
        data = _parse(message.get("content", ""))
        if data.get("task_id") and not data.get("completed"):
            try:
                return planner.find_open_task(str(data["task_id"]))
            except ValueError:
                return None
    return None


def _do_reschedule(history, text, found, due, on_tool, info, kind):
    arguments = {"task_id": found["id"], "due": due}
    try:
        result = tools_module.reschedule_task(**arguments)
        final = replies.reply_for("reschedule_task", arguments, result)
        payload = json.dumps(result, ensure_ascii=False)
    except ValueError as error:
        final, payload = str(error), json.dumps({"error": str(error)}, ensure_ascii=False)
    if on_tool:
        on_tool("reschedule_task", arguments, payload)
    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": final})
    # Tool-result history mein bhi rahe taaki "nahi 7 baje" jaisi agli correction isi task par lage.
    history.insert(-1, {"role": "tool", "tool_name": "reschedule_task", "content": payload})
    info.update(route="code", shortcut=kind, tools_offered=["reschedule_task"], when=due)
    return final


def _try_correction(history, text, on_tool, info):
    """'nahi 6 nahi 7 baje' / 'sorry 5 nahi 6 baje': abhi banaya reminder sahi samay par le jao, bina model ke."""
    clean = router.normalize(text)
    if not _CORRECTION.match(clean) or len(clean.split()) > 8:
        return None
    found = _last_task_in_history(history)
    if not found or not found.get("due_at"):
        return None
    hit = when._find_time(f" {clean} ", has_context=True)
    if not hit:
        return None
    hour, minute = hit[0], hit[1]
    old = found["due_at"]
    try:
        old_hour = int(old[11:13])
    except (ValueError, IndexError):
        old_hour = 9
    low = hour - 12 if hour >= 12 else hour
    candidates = [c for c in (low, low + 12) if 0 <= c <= 23]
    new_hour = min(candidates, key=lambda c: abs(c - old_hour))  # "nahi 7 baje": subah 6 wala tha to subah 7 hi hoga
    due = f"{old[:10]} {new_hour:02d}:{minute:02d}"
    return _do_reschedule(history, text, found, due, on_tool, info, "correction")


def _try_reschedule(history, text, on_tool, info):
    """'dentist wala reminder 5 baje kar do', 'usko kal pe shift kar do', 'snooze': samay code se badlo."""
    clean = router.normalize(text)
    words = set(clean.split())
    snooze = _SNOOZE.search(clean)
    wants = bool(words & RESCHED_WORDS) or snooze or (_RESCHED_HINT.search(clean) and _TASK_NOUN.search(clean)
                                                      and TIME_WORDS.search(clean))
    if not wants:
        return None
    # "cancel karna yaad dilao" jaisa naya reminder to nahi? Aakhri kriya jeet-ti hai.
    creates = [m.start() for m in router.CREATE_PHRASE.finditer(clean)]
    marks = [m.start() for m in re.finditer(r"\b(?:shift|badal|badlo|postpone|sarka|khiska|snooze|ki jagah|kar do|kar dena)\b", clean)]
    if creates and (not marks or max(creates) > max(marks)):
        return None
    if router._wants_remove(clean, words):
        return None  # "hata do" wala flow alag hai
    found = None
    try:
        found = planner.find_open_task(text)
    except ValueError:
        # Naam se nahi mila: "usko/snooze/ki jagah" jaisa PAKKA ishara ho tabhi pichhle task par lagao.
        sure = snooze or "ki jagah" in clean or (words & RESCHED_WORDS) or (words & router.PRONOUNS)
        if sure:
            found = _last_task_in_history(history) or (planner.last_notified_task() if snooze else None)
    if not found:
        return None
    if snooze:
        minutes = int(snooze.group(1)) if snooze.group(1) else 10
        due = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")
    else:
        source = text.split("ki jagah")[-1] if "ki jagah" in clean else text
        due = when.reminder_time(source)
        if not due:
            return None
        if len(due) == 10 and found.get("due_at") and not str(found["due_at"]).endswith("23:59"):
            due = f"{due} {found['due_at'][11:16]}"  # "kal pe shift": din badla, purana samay wahi
    return _do_reschedule(history, text, found, due, on_tool, info, "snooze" if snooze else "reschedule")


_NUMBER_HINT = re.compile(r"\d|\b(?:ek|do|teen|chaa?r|paa?nch|chhe|chhah|saat|aath|nau|das|dus|aadha|aadhe|half|"
                          r"dedh|dhaa?i|sau|hazaar)\b")


def _filter_tools(tools, text):
    """Jo tool is message par chal hi nahi sakta use model ko mat do (galat guess se behtar chat jawab)."""
    if "log_health" in tools and not _NUMBER_HINT.search(text):
        tools = [t for t in tools if t != "log_health"]  # "mujhe neend aa rahi hai": koi number hi nahi bola
    return tools


def run_turn(history, user_text, on_tool=None, info=None, confirm_token=None):
    """Ek sawal ka poora chakkar. on_tool(name, arguments, result): har tool ke baad (optional).
    info: diya ho to isme bhar dete hain ki kya hua (route, tools, samay) - dashboard aur eval ke liye.
    confirm_token: dashboard ke "Haan/Nahi" button se aaya ho to us sawal ka token (purane sawal par galti se delete na ho)."""
    info = info if info is not None else {}
    text = voice.correct(translit.to_roman(user_text), fuzzy=False)  # type kiye "yad"/"bajay"/"kl" bhi sudhre
    if text != user_text:
        info["understood"] = text  # Hindi lipi thi ya spelling sudhri: model ko ye bheja
    checkpoint = len(history)

    # 1. Hatane ka sawal khula hai? To ye message uska jawab ho sakta hai. Sirf saaf "haan" par hi kuch hatta hai.
    #    confirm_token: dashboard har message ke saath us sawal ka token bhejta hai jo screen par khula hai
    #    ("" = koi nahi). Token na mile = doosre tab/purani screen ka "haan": kuch mat hatao. CLI None bhejta hai.
    pending = _open_pending(history)
    decision = _decision(text)
    if decision in ("yes", "no") and confirm_token is not None and (pending is None or pending["token"] != confirm_token):
        history.append({"role": "user", "content": text})
        final = "Ye sawal purana ho gaya, isliye kuch nahi hataya. Dobara bolo kya hatana hai."
        history.append({"role": "assistant", "content": final})
        info.update(route="confirm", tools_offered=[], confirm_result="stale")
        return final
    if pending is not None and decision in ("yes", "no"):
        return _handle_confirmation(history, text, pending, decision, on_tool, info)
    if pending is not None and decision == "unclear":
        history.append({"role": "user", "content": text})
        final = f"Pakka karna hai: {pending['label']} hata doon? Saaf 'haan' ya 'nahi' bolo."
        pending = {**pending, "ts": time.time()}  # wahi sawal, wahi token: phir se poochha
        history.append({"role": "assistant", "content": final, "_pending": pending})
        info.update(route="confirm", tools_offered=[], confirm_result="asked_again", pending=pending)
        return final
    if pending is not None:
        # User ne kuch aur bola: sawal abhi band karo (history se bhi), taaki Ollama fail hone par rollback ke baad
        # wo purana "pakka?" sawal phir se zinda na ho jaye aur baad ka koi "haan" use na laga de.
        history[-1].pop("_pending", None)
        info["confirm_result"] = "dropped"
    elif decision in ("yes", "no"):
        # Akela "haan"/"nahi" bina kisi sawal ke: model ko mat do (wo pichhla kaam "ho gaya" bol deta hai).
        history.append({"role": "user", "content": text})
        final = "Abhi koi sawal pending nahi hai. Batao kya karna hai."
        history.append({"role": "assistant", "content": final})
        info.update(route="confirm", tools_offered=[], confirm_result="none")
        return final

    # Samay badalna ("5 baje kar do", "nahi 6 nahi 7 baje", "snooze"): bina model ke, seedha code se.
    handled = _try_correction(history, text, on_tool, info) or _try_reschedule(history, text, on_tool, info)
    if handled:
        return handled

    shortcut = shortcuts.try_shortcut(text)
    if shortcut:
        info.update(route="shortcut", shortcut=shortcut["kind"], tools_offered=[])
        history.append({"role": "user", "content": text})
        texts = [shortcut["reply"]] if shortcut["reply"] else []
        for call in shortcut["calls"]:
            if on_tool:
                on_tool(call["name"], call["arguments"], call["result"])
            data = _parse(call["result"])
            texts.append(data.get("error") or replies.reply_for(call["name"], call["arguments"], data) or "")
        final = " ".join(t for t in texts if t) or FALLBACK
        history.append({"role": "assistant", "content": final})
        return final

    prev_text = next((m["content"] for m in reversed(history) if m.get("role") == "user"), "")
    plan = router.route(text, context_text=prev_text)
    plan["tools"] = _filter_tools(plan["tools"], text)
    only_remove = plan.get("remove") and "add_task" not in plan["tools"]  # "hata do aur kal 6 baje ..." mein samay chahiye
    info.update(route="model" if plan["tools"] else "chat", tools_offered=plan["tools"], reason=plan["reason"])

    # Multi-intent ("X aur Y"): har hisse par alag chhota model-chakkar, taaki dono kaam hon (model aksar ek hi karta tha).
    parts = router.split_parts(text)
    if len(parts) > 1 and not plan.get("remove"):
        part_plans = [(part, [] if set(router.normalize(part).split()) & router.PRONOUNS
                      else _filter_tools(router.route(part, context_text=prev_text)["tools"], part)) for part in parts]
        # Pronoun wala hissa ("..., wo reminder done kar do") usi baat ko dohraata hai: use alag kaam mat banao.
        if sum(1 for _, tools in part_plans if tools) >= 2:
            history.append({"role": "user", "content": text})
            finals, offered_all = [], []
            try:
                for part, tools in part_plans:
                    if not tools:
                        continue
                    offered_all += [t for t in tools if t not in offered_all]
                    context = {"text": part, "history": history, "prev_text": prev_text, "when": when.parse(part),
                               "part": part if len(parts) > 1 else None}
                    context["prompt_hint"] = when.reminder_time(part) if "add_task" in tools else None
                    finals.append(_chat_loop(history, on_tool, tools, context, info))
                info.update(tools_offered=offered_all, route="model")
                return " ".join(t for t in finals if t) or FALLBACK
            except OSError:
                del history[checkpoint:]
                raise

    # Samay user ke shabdon se (code se). Prompt mein tabhi likhte hain jab reminder banane ka tool diya ho.
    context = {"text": text, "history": history, "prev_text": prev_text,
               "when": None if only_remove else when.parse(text)}
    context["prompt_hint"] = when.reminder_time(text) if "add_task" in plan["tools"] and not only_remove else None
    if context["prompt_hint"]:
        info["when"] = context["prompt_hint"]
    history.append({"role": "user", "content": text})
    try:
        return _chat_loop(history, on_tool, plan["tools"], context, info)
    except OSError:
        del history[checkpoint:]  # Ollama beech mein gir gaya: adhoori baatein hata do, warna model confuse hoga
        raise


def print_tool(name, arguments, result):
    print(f"  [tool] {name} {json.dumps(arguments, ensure_ascii=False)}")  # terminal mein dikhao model ne kya chala
    table = views.table_for(name, result)  # add/update ke baad status table seedha database se
    if table:
        print(table + "\n")


def morning_brief():
    due = planner.due_soon(hours=24)
    if not due:
        return None
    lines = ["Aaj ke kaam:"]
    for task in due:
        lines.append(f"  {'[nikal gaya] ' if task['overdue'] else ''}{task['title']}  ({replies.human_time(task['due_at'])})")
    return "\n".join(lines)


def main():
    brief = morning_brief()
    if brief:
        print(brief)
    if not warm_up():
        print("⚠️  Dhyan dein: Ollama app abhi band hai. AI model ke liye Ollama start karein.")
    print("Assistant taiyar hai. Band karne ke liye /exit likho.")
    history = []
    while True:
        try:
            text = input("Aap: ").strip()
        except (EOFError, KeyboardInterrupt):  # Ctrl+D ya Ctrl+C dabane par aaram se band
            print()
            break
        if text.lower() in {"/exit", "/quit"}:
            break
        if not text:
            continue
        info = {}
        started = time.perf_counter()
        try:
            reply = run_turn(history, text, on_tool=print_tool, info=info)
        except OSError:
            print("AI: Ollama se connect nahi ho paya. Ollama app kholo aur dobara try karo.")
            continue
        took = round((time.perf_counter() - started) * 1000)
        route = "shortcut" if info.get("route") == "shortcut" else f"{info.get('llm_calls', 0)} model call"
        print(f"AI: {reply}   ({route}, {took} ms)")


if __name__ == "__main__":
    main()
