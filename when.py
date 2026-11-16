"""Hinglish/English ke samay wale shabdon ko asli tareekh-samay mein badlo.

    "kal shaam 6 baje"        -> "2026-11-08 18:00"
    "parso subah sadhe 9"     -> "2026-11-09 09:30"
    "somvar ko 11 baje"       -> agle Monday 11:00
    "2 din baad"              -> "2026-11-09"   (sirf tareekh)

Kyun: chhota model aksar tareekh galat jodta hai ("parso" ko kal bana deta hai).
Ye code wahi kaam bina model ke, hamesha ek jaisa karta hai. Samajh na aaye to None deta hai.
"""
import re
from datetime import datetime, timedelta

_DAY_OFFSETS = {"aaj": 0, "aj": 0, "today": 0, "tonight": 0, "kal": 1, "kl": 1, "tomorrow": 1,
                "parso": 2, "parson": 2, "parsoon": 2, "perso": 2, "parsho": 2, "narso": 3}
_WEEKDAYS = {
    "monday": 0, "somvar": 0, "somwar": 0, "tuesday": 1, "mangalvar": 1, "mangalwar": 1,
    "wednesday": 2, "budhvar": 2, "budhwar": 2, "thursday": 3, "guruvar": 3, "guruwar": 3, "veervar": 3,
    "friday": 4, "shukravar": 4, "shukrawar": 4, "saturday": 5, "shanivar": 5, "shaniwar": 5,
    "sunday": 6, "ravivar": 6, "raviwar": 6, "itvaar": 6, "itwar": 6,
}
_PARTS = {"subah": "morning", "savere": "morning", "sawere": "morning", "morning": "morning",
          "dopahar": "afternoon", "dopehar": "afternoon", "afternoon": "afternoon",
          "shaam": "evening", "sham": "evening", "evening": "evening", "tonight": "night",
          "raat": "night", "rat": "night", "night": "night"}
_FRACTIONS = {"sava": 15, "sawa": 15, "sadhe": 30, "saadhe": 30, "sade": 30, "saade": 30, "paune": -15}
_NUMBER_WORDS = {"ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6, "chhah": 6,
                 "che": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10, "dus": 10, "gyarah": 11, "gyaarah": 11,
                 "gyara": 11, "gyaara": 11, "barah": 12, "baarah": 12, "bara": 12, "baara": 12}
_HALF_HOURS = {"dedh": (1, 30), "dhai": (2, 30), "dhaai": (2, 30)}  # dedh baje = 1:30, dhai baje = 2:30
_COUNT_WORDS = {**{k: v for k, v in _NUMBER_WORDS.items()}, "dedh": 1.5, "dhai": 2.5, "dhaai": 2.5}

_TIME = re.compile(
    r"\b(?:(?P<frac>sava|sawa|sadhe|saadhe|sade|saade|paune)\s+)?"
    r"(?P<hour>\d{1,2}|ek|do|teen|chaa?r|paa?nch|chhe|chhah|che|saat|aath|nau|das|dus|gyaa?raa?h?|baa?raa?h?|dedh|dhaa?i)"
    r"(?:[:.](?P<minute>\d{2}))?\s*"
    r"(?P<suffix>baje|bje|bajey|bajay|baaje|am|a\.m\.|pm|p\.m\.|o'?clock)?\b"
)
_NOT_TIME = re.compile(r"\s*(?:ghante|ghanta|ghnte|hours?|hrs?|minutes?|mins?|glass|gilas|gilaas|din|days?|km|kg|baar|times?|"
                       r"rupaye|rupay|rupees?|rs|sau|hazaar|hazar|lakh|kilo|kilos|gram|grams|litre|liter|dozen|darjan|"
                       r"packet|log|bande|saal|mahine|hafte)\b")
# "30 minute baad", "2 ghante mein", "aadhe ghante baad", "in 45 minutes": abhi se itni der baad.
_COUNT = r"\d{1,3}|ek|do|teen|chaa?r|paa?nch|chhe|chhah|saat|aath|nau|das|dus|dedh|dhaa?i"
_IN_TIME = re.compile(
    rf"\b(?:(?P<num>{_COUNT})|(?P<half>aadhe|adhe|aadha|half))\s*(?P<unit>minute|minutes|min|mins|ghante|ghanta|ghnte|hours?|hrs?)"
    r"\s*(?:ke\s+)?(?:baad|bad|mein|me|later)\b|\bin\s+(?P<num2>\d{1,3})\s*(?P<unit2>minutes?|mins?|hours?|hrs?)\b")
_IN_DAYS = re.compile(rf"\b({_COUNT})\s*(?:din|days?)\s*(?:ke\s+)?(?:baad|bad|mein|me|later)\b|\bin\s+(\d{{1,2}})\s+days?\b")


def _count(text):
    return float(text) if text.isdigit() else _COUNT_WORDS.get(text)
_DATE_OF_MONTH = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:tareekh|tarikh|date)\b")
_MONTHS_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9,
    "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_MONTHS_PATTERN = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_MONTH_DAY = re.compile(
    rf"\b(?P<d1>\d{{1,2}})(?:st|nd|rd|th)?\s+(?P<m1>{_MONTHS_PATTERN})\b|\b(?P<m2>{_MONTHS_PATTERN})\s+(?P<d2>\d{{1,2}})(?:st|nd|rd|th)?\b"
)
_RECUR_DAILY = re.compile(r"\b(?:roz|rozz|daily|every\s*day|har\s*din|har\s*roz)\b")
_RECUR_WEEKDAY = re.compile(
    r"\b(?:har|every)\s+(?:hafte\s+)?(somvar|somwar|monday|mangalvar|mangalwar|tuesday|budhvar|budhwar|wednesday|"
    r"guruvar|guruwar|veervar|thursday|shukravar|shukrawar|friday|shanivar|shaniwar|saturday|ravivar|raviwar|itvaar|itwar|sunday)\b"
)
_RECUR_WEEKLY = re.compile(r"\b(?:har\s*hafte|weekly|every\s*week)\b")
_RECUR_MONTHLY = re.compile(r"\b(?:har\s*mahine|monthly|every\s*month)\b")
_RECUR_YEARLY = re.compile(r"\b(?:har\s*saal|har\s*varsh|every\s*year|yearly|saalana|salana)\b")


def parse_recurrence(text):
    """'roz', 'har somvar', 'har hafte', 'har saal', 'daily' jaise shabdon se recurrence pehchano."""
    lowered = text.lower()
    if _RECUR_DAILY.search(lowered):
        return "daily"
    match = _RECUR_WEEKDAY.search(lowered)
    if match:
        w_idx = _WEEKDAYS.get(match.group(1))
        if w_idx is not None:
            return f"weekly:{w_idx}"
    if _RECUR_WEEKLY.search(lowered):
        return "weekly"
    if _RECUR_MONTHLY.search(lowered):
        return "monthly"
    if _RECUR_YEARLY.search(lowered):
        return "yearly"
    return None


def _hour_for(hour, part, suffix):
    if suffix in ("pm", "p.m.") and hour < 12:
        return hour + 12
    if suffix in ("am", "a.m."):
        return 0 if hour == 12 else hour
    if part == "morning":
        return 0 if hour == 12 else hour
    if part in ("afternoon", "evening"):
        return hour + 12 if hour < 12 else hour  # dopahar 2 = 14:00, shaam 6 = 18:00
    if part == "night":
        if hour == 12:
            return 0
        return hour + 12 if 5 <= hour < 12 else hour  # raat 9 = 21:00, raat 2 = 02:00
    # Subah/shaam nahi bola: 1-7 baje ko aksar shaam ka matlab hota hai (koi 3 baje subah ka reminder nahi lagata).
    return hour + 12 if 1 <= hour <= 7 else hour


_PART_WORD = re.compile(r"\b(" + "|".join(sorted(_PARTS, key=len, reverse=True)) + r")\b")


def _find_time(text, has_context):
    """(hour, minute, suffix, position) ya None.
    Pehle wahi number jiske saath 'baje'/am/pm/':30' ho ("15 tareekh ko 6 baje" mein 6, 15 nahi).
    Akela number (bina baje) tabhi, jab subah/shaam jaisa shabd ho, aur aage 'kilo/sau/ghante' jaisi ginti na ho."""
    strong, weak = [], []
    for match in _TIME.finditer(text):
        hour_text, suffix, minute, frac = match.group("hour"), match.group("suffix"), match.group("minute"), match.group("frac")
        if not suffix and _NOT_TIME.match(text, match.end()):
            continue  # "7 ghante", "8 glass", "saade teen sau rupaye": ginti hai, samay nahi
        if suffix or minute:
            strong.append(match)
        elif hour_text.isdigit() or frac:
            weak.append(match)  # "shaam 6", "subah sadhe 9": sirf din ke hisse ke saath
        # shabd wala akela number ("hata do", "ek kaam") kabhi samay nahi
    for match in strong + (weak if has_context else []):
        hour_text, suffix, minute = match.group("hour"), match.group("suffix"), match.group("minute")
        if hour_text in _HALF_HOURS:
            hour, minutes = _HALF_HOURS[hour_text]
        else:
            hour = int(hour_text) if hour_text.isdigit() else _NUMBER_WORDS.get(hour_text)
            minutes = int(minute) if minute else 0
        if hour is None or hour > 23:
            continue
        frac = _FRACTIONS.get(match.group("frac") or "", 0)
        if frac < 0:  # paune 6 = 5:45
            hour, minutes = (hour - 1) % 24, 60 + frac
        elif frac:
            minutes = frac
        if minutes > 59:
            continue
        return hour, minutes, (suffix or "").lower(), match.start()
    return None


def _nearest_part(text, position):
    """Samay ke sabse paas wala subah/shaam ("kal subah gym, shaam 6 baje doodh" -> shaam)."""
    parts = [(abs(m.start() - position), _PARTS[m.group(1)]) for m in _PART_WORD.finditer(text)]
    return min(parts)[1] if parts else None


def parse(text, now=None):
    """Text mein jo samay bola gaya hai use 'YYYY-MM-DD HH:MM' (ya sirf 'YYYY-MM-DD') mein do. Na mile to None."""
    now = now or datetime.now()
    lowered = f" {text.lower()} "
    relative = _IN_TIME.search(lowered)
    if relative:  # "30 minute baad" / "2 ghante mein": abhi se itni der baad
        unit = relative.group("unit") or relative.group("unit2")
        in_hours = unit.startswith(("gh", "h"))
        if relative.group("half"):
            minutes = 30 if in_hours else 0  # "aadhe ghante" = 30 min
        else:
            number = _count(relative.group("num") or relative.group("num2")) or 0
            minutes = round(number * 60) if in_hours else round(number)
        if minutes:
            return (now + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")
    # "tomorrow at 7" / "at 7:30": 'at' ke baad ka akela number bhi samay hai.
    lowered = re.sub(r"\bat\s+(\d{1,2})(?::(\d{2}))?\b", lambda m: f"{m.group(1)}:{m.group(2) or '00'} baje", lowered)
    words = re.findall(r"[a-z]+", lowered)
    part = next((_PARTS[w] for w in words if w in _PARTS), None)
    next_month = re.search(r"\bagle\s+mah[ei]ne\b|\bnext\s+month\b", lowered)
    next_year = re.search(r"\bagle\s+saal\b|\bnext\s+year\b", lowered)

    day = None
    offset = next((_DAY_OFFSETS[w] for w in words if w in _DAY_OFFSETS), None)
    if offset is not None:
        day = now.date() + timedelta(days=offset)
    weekday = next((_WEEKDAYS[w] for w in words if w in _WEEKDAYS), None)
    if day is None and weekday is not None:
        ahead = (weekday - now.weekday()) % 7 or 7
        day = now.date() + timedelta(days=ahead)
    in_days = _IN_DAYS.search(lowered)
    if day is None and in_days:
        day = now.date() + timedelta(days=int(_count(in_days.group(1) or in_days.group(2)) or 0))
    if day is None and re.search(r"\bagle\s+hafte\b|\bnext\s+week\b", lowered):
        day = now.date() + timedelta(days=7)

    # "15 tareekh" ya "5 Dec"
    if day is None:
        m_day = _MONTH_DAY.search(lowered)
        if m_day:
            day_num = int(m_day.group("d1") or m_day.group("d2"))
            m_str = (m_day.group("m1") or m_day.group("m2")).lower()
            if m_str in _MONTHS_MAP and 1 <= day_num <= 31:
                month_num = _MONTHS_MAP[m_str]
                year = now.year if (month_num > now.month or (month_num == now.month and day_num >= now.day)) else now.year + 1
                try:
                    day = datetime(year, month_num, day_num).date()
                except ValueError:
                    pass
        elif _DATE_OF_MONTH.search(lowered):
            target_num = int(_DATE_OF_MONTH.search(lowered).group(1))
            if 1 <= target_num <= 31:
                year = now.year
                if next_month:  # "agle mahine 20 tareekh" = agla mahina hi, chahe 20 abhi aana baaki ho
                    month = (now.month % 12) + 1
                    year += 1 if now.month == 12 else 0
                else:
                    month = now.month if target_num >= now.day else (now.month % 12) + 1
                    if month == 1 and target_num < now.day:
                        year += 1
                try:
                    day = datetime(year, month, target_num).date()
                except ValueError:
                    pass
        else:
            # Sirf mahine ka naam ("june tak", "agle saal march mein"): us mahine ki 1 tareekh.
            # "may" English ka aam shabd bhi hai, isliye use yahan nahi ginte.
            m_only = re.search(rf"\b({_MONTHS_PATTERN})\b", lowered)
            if m_only and m_only.group(1) != "may":
                month_num = _MONTHS_MAP[m_only.group(1)]
                year = now.year + (1 if (next_year or month_num < now.month) else 0)
                if next_year and year <= now.year:
                    year = now.year + 1
                day = datetime(year, month_num, 1).date()
    if day is None and next_month:  # "agle mahine rent dena" (tareekh nahi boli): agle mahine ki 1 tareekh
        day = datetime(now.year + (1 if now.month == 12 else 0), (now.month % 12) + 1, 1).date()

    # Din wale number ("2 din baad") ko time mat samjho.
    time_text = _MONTH_DAY.sub(" ", _DATE_OF_MONTH.sub(" ", _IN_DAYS.sub(" ", lowered)))
    found = _find_time(time_text, has_context=part is not None)
    if found is None:
        return day.isoformat() if day else None
    hour, minute, suffix, position = found
    part = _nearest_part(time_text, position) or part
    hour = _hour_for(hour, part, suffix)
    if day is None and part is None and suffix not in ("am", "a.m.", "pm", "p.m."):
        # Bina subah/shaam ka ghanta = AGLA aane wala wahi ghanta:
        if 13 <= hour <= 19 and (hour, minute) <= (now.hour, now.minute):
            hour -= 12   # raat 10 baje "7 baje" bola = kal subah 7 (shaam ka 7 nikal chuka)
        elif hour < 12 and (hour, minute) <= (now.hour, now.minute) and (hour + 12, minute) > (now.hour, now.minute):
            hour += 12   # subah 9:44 par "8 baje" = aaj raat 8, kal subah 8 nahi
    if day is None:  # sirf time bola: aaj, aur nikal chuka ho to kal
        day = now.date()
        if (hour, minute) <= (now.hour, now.minute):
            day += timedelta(days=1)
    elif part == "night" and hour < 5:
        day += timedelta(days=1)  # "aaj raat 12 baje" / "raat 2 baje" = aadhi raat ke baad, yaani agla din
    return f"{day.isoformat()} {hour:02d}:{minute:02d}"


_PART_DEFAULTS = {"morning": "09:00", "afternoon": "14:00", "evening": "18:00", "night": "21:00"}


def reminder_time(text, now=None):
    """Sirf REMINDER banate waqt: 'kal subah doodh lena' jaise bina-ghante waale text mein din ke hisse ka
    default samay jodo (subah 9, dopahar 2, shaam 6, raat 9). Baaki sab parse() jaisa.
    Health/baaki jagah parse() hi use hota hai, taaki 'kal raat 7 ghante soya' date-only hi rahe."""
    result = parse(text, now)
    if not result or len(result) > 10:
        return result
    part = next((_PARTS[w] for w in re.findall(r"[a-z]+", text.lower()) if w in _PARTS), None)
    if part:
        return f"{result} {_PART_DEFAULTS[part]}"
    return result


def past_day(text, now=None):
    """Beete hue kaam (check-in, health log) ka din: "kal" = beeta kal, "parso" = do din pehle.
    Koi din nahi bola to None (yaani aaj). "kal raat soya" ki neend aaj ke din mein ginte hain."""
    now = now or datetime.now()
    lowered = text.lower()
    explicit = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", lowered)
    if explicit:
        return explicit.group(1)
    words = set(re.findall(r"[a-z]+", lowered))
    if words & {"kal", "kl", "yesterday"} and not words & {"raat", "rat", "night"}:
        return (now.date() - timedelta(days=1)).isoformat()
    if words & {"parso", "parson", "perso"}:
        return (now.date() - timedelta(days=2)).isoformat()
    return None
