"""Har message ke liye sirf kaam ke tools chuno.

Kyun: 18 tools ek saath dene par chhota model (llama3.2 3B) aksar galat tool chunta hai, aur har tool ka
description prompt ko lamba (dheema) karta hai. Yahan seedhe niyam se topic pehchaante hain:
  1. Database mein jo naam pehle se hain (habit "walking", cheez "passport", contact "mummy") sabse pakka ishara hain.
  2. Phir topic ke shabd: paani/neend = health, joote/kitab = things, yaad dilao = tasks...
  3. Sawal hai ("kahan", "dikhao") ya bayan ("rack mein hain") -> dhundhne wala tool ya save karne wala tool.
Kuch samajh na aaye to saare tools de dete hain (pehle jaisa), taaki koi kaam atke nahi.
"""
import re

import planner
from db import connect

# Har topic: sawal par kaunse tools, bayan (save/update) par kaunse.
GROUPS = {
    "habits": {"question": ["habit_status"], "statement": ["add_habit", "check_in_habit"]},
    "tasks": {"question": ["list_tasks"], "statement": ["add_task", "complete_task"]},
    "goals": {"question": ["list_goals"], "statement": ["add_goal"]},
    "health": {"question": ["health_summary"], "statement": ["log_health"]},
    "things": {"question": ["find_things"], "statement": ["add_thing", "update_thing"]},
    "items": {"question": ["find_item"], "statement": ["remember_item"]},
    "contacts": {"question": ["call_contact"], "statement": ["call_contact"]},
    "notes": {"question": ["search_notes"], "statement": ["search_notes"]},
}

# Pakke shabd (topic ka naam hi hai). "*" = shabd isse shuru ho. Do shabd = poora phrase.
STRONG = {
    "habits": ["habit*", "habbit*", "aadat*", "aadaton", "streak*", "check in", "checkin"],
    "tasks": ["task*", "todo*", "to do", "reminder*", "remind*", "yaad di*", "yaad karana", "appointment*",
              "meeting*", "deadline*", "kaam", "kaamon"],
    "goals": ["goal*", "lakshya"],
    "health": ["paani", "pani", "water", "glass", "gilas", "gilaas", "neend", "nind", "sleep*", "soya", "soyi",
               "so gaya", "so gayi", "ghante", "workout*", "exercise*", "training", "gym", "mobility", "stretch*",
               "energy", "health", "hydration"],
    "things": ["book*", "kitab*", "kitaab*", "novel*", "joot*", "jute", "juta", "shoe*", "sneaker*", "chappal*",
               "sandal*", "shirt*", "tshirt*", "t shirt", "dress*", "kapd*", "jeans", "jacket*", "kurta*", "saree*",
               "shelf", "rack", "wardrobe"],
    "items": ["passport", "chabi", "chaabi", "key", "keys", "charger*", "wallet", "purse", "umbrella", "chhata",
              "chhatri", "earphone*", "headphone*", "airpods", "laptop", "document*", "aadhaar", "aadhar",
              "pan card", "ring", "watch", "ghadi", "chashma", "specs", "locker", "drawer", "almirah", "almari",
              "cupboard"],
    "contacts": ["call", "contact*", "number"],
    "notes": ["ka naam", "ki naam", "naam kya", "name kya", "hometown", "birthday", "bday", "janam*", "janm*", "paida", "date of birth", "dob", "born", "umar", "age", "mera naam", "parents", "family", "father",
              "mother", "job", "naukri", "company", "salary", "career", "kaam karta", "kaam karti", "kaam karte",
              "designation", "experience", "skills", "about me", "mere bare", "mere baare", "kaun hoon", "kaun hu",
              "rehta hoon", "rahta hoon", "rehti hoon", "rahti hoon", "rehta hu", "rahta hu", "ghar kahan",
              "college", "school", "education", "hobby", "hobbies", "routine", "diet", "vegetarian", "ambition*",
              "dream*", "pasand"],
}
# Kamzor ishare: tabhi gine jaate hain jab koi pakka shabd na mile.
WEAK = {
    "habits": ["ho gayi", "ho gaya", "ho gai", "ho gya", "ho gyi", "hogayi", "hogaya", "kar li", "kar liya",
               "kar lia", "kr li", "done", "ho chuka", "ho chuki", "roz", "daily"],
    "tasks": ["ho gaya", "ho gayi", "done", "baje", "yaad", "bharna"],
    "items": ["kahan", "kaha", "kahaan", "kidhar", "rakha", "rakhi", "rakhe", "rakh", "mein hai", "me hai",
              "pe hai", "par hai", "phone", "bag", "gaadi", "car"],
    "things": ["khatam", "finished", "lent", "udhaar", "padh*", "reading", "color", "colour", "brand", "size"],
    # Rishte ke shabd: saved contact ho to database wala naam pakda jata hai; warna ye sirf kamzor ishara hain.
    "contacts": ["phone", "mummy", "mumi", "mummi", "maa", "papa", "bhai", "didi", "behen"],
    "notes": ["naam", "mummy", "maa", "papa", "bhai", "didi", "behen"],
}
QUESTION_WORDS = {"kahan", "kaha", "kahaan", "kidhar", "kya", "kaun", "kaunsa", "kaunsi", "kaunse", "kitna",
                  "kitne", "kitni", "kab", "kaise", "kyun", "kyon", "dikhao", "dikha", "dikhaao", "batao", "bata",
                  "btao", "list", "show", "status", "summary", "where", "what", "which", "how", "when"}
# "Hata do / delete / cancel" = hatane ka irada. Tab sirf us topic ka remove_* tool milta hai, jo khud kuch nahi
# hatata, sirf user se "pakka?" poochhta hai.
REMOVE_WORDS = {"hata", "hataa", "hatao", "hataao", "hatado", "hatana", "hatane", "hatayein", "hatadein", "hataiye",
                "hataie", "hatwa", "hatwao", "delete", "remove", "mitao", "mitaa", "mitado", "mitaiye", "cancel", "erase"}
# "Cancel karna yaad dilao" = naya reminder banana hai, purana hatana nahi.
CREATE_PHRASE = re.compile(r"\byaad\s+(?:di|kara)\w*|\bremind\s+(?:me|karna|kar\w*)\b|\breminder\s+(?:laga|set|bana)\w*")
# "ye hata do", "isko delete karo": topic nahi bola, par hatana hi hai (pichhli baat ki cheez).
PRONOUNS = {"ye", "yeh", "isko", "isse", "iska", "usko", "use", "wo", "woh", "vo", "pichhla", "pichla", "last"}
REMOVE_TOOLS = {"tasks": "remove_task", "items": "remove_item", "things": "remove_thing", "habits": "remove_habit",
                "goals": "remove_goal", "contacts": "remove_contact"}

# "mera/main" + sawal = user apne baare mein poochh raha hai: jawab notes mein hoga, model ke andaze mein nahi.
SELF_WORDS = {"mera", "meri", "mere", "main", "mujhe", "mujhko", "maine", "my", "i", "me", "am"}
ACTION_WORDS = {"save", "add", "yaad", "rakh", "rakho", "likho", "likh", "note", "track", "log", "karo", "kar",
                "do", "dalo", "daalo", "jodo", "update", "badlo", "mark", "karna", "karni", "karne", "lena", "jana"}
ALL_TOOLS = ["remember_item", "find_item", "add_contact", "call_contact", "add_task", "list_tasks", "complete_task",
             "add_goal", "list_goals", "log_health", "health_summary", "add_habit", "check_in_habit",
             "habit_status", "add_thing", "find_things", "update_thing", "search_notes"]
ORDER = ALL_TOOLS + list(REMOVE_TOOLS.values())


def _pattern(keyword):
    prefix = keyword.endswith("*")
    words = keyword.rstrip("*").split()
    body = r"\s+".join(re.escape(word) for word in words)
    return re.compile(r"\b" + body + (r"\w*" if prefix else r"\b"))


def _compile(table):
    # Lambe phrase pehle, taaki "kaam karta" (notes) pehle pakda jaye aur "kaam" (tasks) na bane.
    pairs = [(group, keyword) for group, keywords in table.items() for keyword in keywords]
    pairs.sort(key=lambda pair: -len(pair[1]))
    return [(group, _pattern(keyword)) for group, keyword in pairs]


_STRONG = _compile(STRONG)
_WEAK = _compile(WEAK)


def normalize(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _known_names():
    """Database mein pehle se saved naam: (naam, group). Har baar taaza padhte hain (tables chhoti hain)."""
    with connect() as conn:
        rows = [(r["name"], "habits") for r in conn.execute("SELECT name FROM habits")]
        rows += [(r["name"], "items") for r in conn.execute("SELECT name FROM items")]
        rows += [(r["name"], "things") for r in conn.execute("SELECT name FROM things")]
        rows += [(r["alias"], "contacts") for r in conn.execute("SELECT alias FROM aliases")]
    return [(normalize(name), group) for name, group in rows if normalize(name)]


_STOP_TRACKING = {"habit", "habits", "aadat", "aadatein", "reminder", "reminders", "goal", "goals", "alarm",
                  "tracking", "track", "entry"}


def _wants_remove(clean, words):
    """Hatana hai ya naya banana? Jo kriya AAKHIR mein aaye wahi irada hai:
    "Netflix cancel karna yaad dilao" = banana (yaad dilao baad mein), "yaad dilane wala reminder hata do" = hatana."""
    tokens = clean.split()
    # "hataadu", "hatwa do", "mita do" jaise roop bhi (awaaz se aksar aise likha aata hai)
    removing = [i for i, w in enumerate(tokens) if w in REMOVE_WORDS or w.startswith(("hata", "hatwa", "mita"))]
    # "reading habit band kar do" = habit/reminder/goal ke saath "band" bhi hatana hai
    removing += [i for i, w in enumerate(tokens) if w == "band" and words & _STOP_TRACKING]
    if not removing:
        return False
    last_remove = max(removing)
    creates = [m.start() for m in CREATE_PHRASE.finditer(clean)]
    if not creates:
        return True
    last_create_token = len(clean[:max(creates)].split())
    return last_remove > last_create_token


def _near(word, name):
    """'walk'/'walked' ~ 'walking': shuru ka hissa kam se kam 4 akshar aur chhote shabd ka 60% mile.
    ('contract' ~ 'contact' nahi: common 'cont' = 4 < 0.6 * 7.)"""
    if len(word) < 4 or len(name) < 4:
        return False
    common = 0
    for a, b in zip(word, name):
        if a != b:
            break
        common += 1
    return common >= 4 and common >= 0.6 * min(len(word), len(name))


def _scan(text, compiled, hits):
    """Mile hue shabd hata do (taaki ek shabd do topic na gine) aur group ginti badhao."""
    for group, pattern in compiled:
        if pattern.search(text):
            hits[group] = hits.get(group, 0) + 1
            text = pattern.sub(" # ", text)
    return text


# "ho gaya / kar diya / bhar diya": kaam poora hone ki baat. "miss/nahi" ke saath nahi.
_DONE_VERB = re.compile(r"\b(?:ho\s+ga?y[ai]|ho\s+gai|hogay[ai]|ho\s+chuk[aei]|kar\s+(?:diya|di|liya|li|lia)|"
                        r"kr\s+(?:diya|li)|bhar\s+(?:diya|di)|de\s+(?:diya|di)|jama\s+kar\s+(?:diya|di)|"
                        r"le\s+aay[ai]|karwa\s+(?:diya|di)|done|completed?)\b")
_NEGATION = re.compile(r"\b(?:miss|chhut|chhoot|skip|nahi|nahin|mat)\b")
# Tasks ka asli signal (akela "kaam" shabd chit-chat bhi ho sakta hai: "aaj kaam bahut tha").
_TASK_SIGNAL = re.compile(r"\b(?:task\w*|todo\w*|reminder\w*|remind\w*|yaad|appointment\w*|meeting\w*|deadline\w*)\b")


def _open_task_overlap(clean):
    """Message ke shabd kisi pending kaam ke title se milte hain? (Jaise "bill bhar diya" ~ "bijli ka bill bharna".)"""
    words = {w for w in clean.split() if len(w) >= 3 and w not in planner._TASK_FILLER}
    if not words:
        return None
    for task in planner.list_tasks():
        title_words = set(re.findall(r"[a-z0-9]+", task["title"].lower()))
        if words & title_words:
            return task
    return None


def _route_single(text, context_text=""):
    """Ek single clause ke liye tools chuno. context_text: pichhle message ka text (sirf "wo/usko" jaise
    pronoun wale message mein us baat ki cheez/topic pehchanne ke liye)."""
    clean = normalize(text)
    words = set(clean.split())
    question = bool(words & QUESTION_WORDS) or text.strip().endswith("?")
    strong, weak, names, known = {}, {}, [], set()
    masked = f" {clean} "
    for name, group in sorted(_known_names(), key=lambda pair: -len(pair[0])):
        pattern = rf"\b{re.escape(name)}\b"
        if not re.search(pattern, masked) and " " not in name:
            # Adhoora naam bhi chalega: "walk" = "walking", "chabiyan" = "chabi" (kam se kam 4 akshar mile).
            near = [w for w in masked.split() if _near(w, name)]
            pattern = rf"\b{re.escape(near[0])}\b" if near else None
        if pattern and re.search(pattern, masked):
            strong[group] = strong.get(group, 0) + 2
            names.append(name)
            known.add(group)
            masked = re.sub(pattern, " # ", masked)
    masked = _scan(masked, _STRONG, strong)
    _scan(masked, _WEAK, weak)
    if re.search(r"\d{10}", clean):  # 10 ank ka number = phone number
        strong["contacts"] = strong.get("contacts", 0) + 2
    if context_text and words & PRONOUNS:
        # "wo khatam ho gayi": pichhle message mein jis saved cheez ka naam tha, wahi topic hai.
        previous = f" {normalize(context_text)} "
        for name, group in _known_names():
            if re.search(rf"\b{re.escape(name)}\b", previous):
                strong.setdefault(group, 1)
                known.add(group)

    done_said = bool(_DONE_VERB.search(clean)) and not _NEGATION.search(clean)
    if strong.get("tasks") and not question and not _TASK_SIGNAL.search(clean) and not done_said \
            and not CREATE_PHRASE.search(clean) and not _open_task_overlap(clean):
        strong.pop("tasks")  # "aaj office mein kaam bahut tha": kaam ki baat hai, koi task action nahi

    groups = list(strong) or list(weak)
    removable = [g for g in groups if g in REMOVE_TOOLS]
    if _wants_remove(clean, words) and (removable or words & PRONOUNS or not groups):
        tools = [REMOVE_TOOLS[g] for g in removable] or list(REMOVE_TOOLS.values())
        ordered = [name for name in ORDER if name in tools]
        reason = (", ".join(removable) or "pichhli baat ki cheez") + " (hatana: pehle poochhenge)"
        return {"tools": ordered, "groups": groups, "question": False, "remove": True, "reason": reason}
    if done_said and not question:
        task = _open_task_overlap(clean)
        if task:
            # "bill bhar diya", "gas cylinder book kar diya": saved kaam poora hua. add_task/add_thing nahi.
            tools = ["complete_task"] + (["check_in_habit"] if "habits" in known else [])
            ordered = [name for name in ORDER if name in tools]
            return {"tools": ordered, "groups": groups or ["tasks"], "question": False,
                    "reason": f"pending kaam '{task['title']}' + poora hone ki kriya"}
    if "notes" in groups and "contacts" in groups and not words & {"call", "number", "phone", "contact", "lagao"}:
        groups.remove("contacts")  # "mummy ka naam kya hai" = notes ka sawal, phone ka nahi
    if not groups and question and words & SELF_WORDS:
        groups = ["notes"]
    if not groups:
        if words & ACTION_WORDS:
            return {"tools": ALL_TOOLS, "groups": [], "question": question, "reason": "topic nahi mila: saare tools"}
        return {"tools": [], "groups": [], "question": question, "reason": "baat-cheet: koi tool nahi"}

    tools = []
    for group in groups:
        for name in GROUPS[group]["question" if question else "statement"]:
            if group == "contacts" and not question and re.search(r"\d{10}", clean):
                name = "add_contact"
            if name == "update_thing" and "things" not in known:
                continue  # koi saved cheez ka naam nahi aaya: ye nayi cheez hai, update nahi
            if name == "add_thing" and "things" in known:
                continue  # saved cheez ka naam aaya ("Nike Pegasus laundry mein"): nayi entry nahi, update
            if name not in tools:
                tools.append(name)
    ordered = [name for name in ORDER if name in tools]
    reason = ", ".join(groups) + (" (sawal)" if question else " (bayan)") + (f"; pehchane naam: {', '.join(names)}" if names else "")
    return {"tools": ordered, "groups": groups, "question": question, "reason": reason}


def split_parts(text):
    """Multi-intent message ke hisse: "X aur Y", "X, Y". Chhote tukde (<= 3 akshar) gin mein nahi."""
    return [p.strip() for p in re.split(r"\b(?:aur|and|phir|then)\b|[,;]", text) if len(p.strip()) > 3]


def route(text, context_text=""):
    """{'tools': [...], 'groups': [...], 'question': bool, 'reason': '...'} deta hai.
    Multi-intent: agar message mein 'aur', 'and', 'phir' se do alag baatein kahi gayi hon to dono ke tools chuno."""
    parts = split_parts(text)
    if len(parts) > 1:
        all_tools, all_groups, reasons = [], [], []
        any_q, any_rm = False, False
        for part in parts:
            res = _route_single(part, context_text)
            if not res["tools"] and not res["groups"]:
                continue
            for t in res["tools"]:
                if t not in all_tools:
                    all_tools.append(t)
            for g in res["groups"]:
                if g not in all_groups:
                    all_groups.append(g)
            any_q = any_q or res.get("question", False)
            any_rm = any_rm or res.get("remove", False)
            reasons.append(res["reason"])
        if all_tools:
            ordered = [name for name in ORDER if name in all_tools]
            return {"tools": ordered, "groups": all_groups, "question": any_q, "remove": any_rm, "reason": " + ".join(reasons)}
    return _route_single(text, context_text)
