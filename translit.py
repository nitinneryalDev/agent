"""Devanagari (Hindi lipi) ko Roman Hinglish mein badalna: "मेरा छाता कहाँ है" -> "mera chhata kahan hai".

Kyun: chhota model aur notes ka search Roman Hinglish zyada achha samajhte hain. Hindi mic ya Whisper
Devanagari mein likhte hain, isliye model ko bhejne se pehle yahan badal dete hain.
Koi library nahi: seedha akshar-dar-akshar map, aur Hindi ka 'a' chhodne ka (schwa deletion) chhota niyam.
"""
import re

_VOWELS = {"अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri",
           "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ऑ": "o", "ऍ": "e"}
_MATRAS = {"ा": "aa", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo", "ृ": "ri",
           "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॉ": "o", "ॅ": "e"}
_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "f", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    "क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z", "ड़": "d", "ढ़": "dh", "फ़": "f", "य़": "y",
}
_NUKTA_FORMS = {"क": "q", "ख": "kh", "ग": "g", "ज": "z", "ड": "d", "ढ": "dh", "फ": "f", "य": "y"}
_VIRAMA, _ANUSVARA, _CHANDRABINDU, _VISARGA, _NUKTA = "्", "ं", "ँ", "ः", "़"
_DIGITS = str.maketrans("०१२३४५६७८९।॥", "0123456789..")
_DEVANAGARI_RUN = re.compile(r"[ऀ-ॿ]+")
_LABIALS = ("p", "b", "m")

# Aam shabd jo seedhe niyam se ajeeb bante hain, aur English shabd jo Hindi lipi mein likhe jaate hain
# (Whisper aur Hindi mic aksar aisa likhte hain: "कॉल करो", "पासपोर्ट").
_WORDS = {
    "में": "mein", "नहीं": "nahi", "नही": "nahi", "हाँ": "haan", "हां": "haan", "क्यों": "kyon", "ठीक": "theek",
    "वाला": "wala", "वाली": "wali", "वाले": "wale", "मम्मी": "mummy", "पापा": "papa",
    "कॉल": "call", "फोन": "phone", "फ़ोन": "phone", "नंबर": "number", "नम्बर": "number", "सेव": "save",
    "मोबाइल": "mobile", "ऑफिस": "office", "ऑफ़िस": "office", "लॉकर": "locker", "पासपोर्ट": "passport",
    "चार्जर": "charger", "लैपटॉप": "laptop", "बैग": "bag", "वॉलेट": "wallet", "अम्ब्रेला": "umbrella",
    "ड्रॉअर": "drawer", "ड्रॉर": "drawer", "बेडरूम": "bedroom", "किचन": "kitchen", "शेल्फ": "shelf", "रैक": "rack",
    "बुक": "book", "बुक्स": "books", "शूज़": "shoes", "शूज": "shoes", "शू": "shoe", "शर्ट": "shirt", "ड्रेस": "dress",
    "टास्क": "task", "रिमाइंडर": "reminder", "मीटिंग": "meeting", "अपॉइंटमेंट": "appointment",
    "हैबिट": "habit", "हैबिट्स": "habits", "गोल": "goal", "गोल्स": "goals", "हेल्थ": "health", "समरी": "summary",
    "वॉकिंग": "walking", "रनिंग": "running", "रीडिंग": "reading", "मेडिटेशन": "meditation", "योगा": "yoga",
    "जिम": "gym", "वर्कआउट": "workout", "ट्रेनिंग": "training", "स्लीप": "sleep", "वॉटर": "water", "ग्लास": "glass",
    "डेंटिस्ट": "dentist", "डॉक्टर": "doctor", "स्ट्रीक": "streak", "स्टेटस": "status", "लिस्ट": "list",
    "डिलीट": "delete", "डिलिट": "delete", "कैंसिल": "cancel", "कैंसल": "cancel", "कैन्सल": "cancel", "रिमूव": "remove",
    "हटाइए": "hataiye", "हटाइये": "hataiye", "हटा": "hata", "हटाओ": "hatao", "हटाना": "hatana", "मिटाओ": "mitao",
    "छाता": "chhata", "छतरी": "chhatri", "चाबी": "chabi", "चाभी": "chabi", "जूते": "joote", "किताब": "kitab",
    "कपड़े": "kapde", "दवाई": "dawai", "दवा": "dawa", "गिलास": "glass", "घंटे": "ghante",
}


def has_devanagari(text):
    return bool(_DEVANAGARI_RUN.search(text or ""))


def _syllables(word):
    """Shabd ko [consonant, vowel, kind] ke tukdon mein todo. kind: 'inherent', 'matra', 'none', 'vowel'."""
    units, i = [], 0
    while i < len(word):
        ch = word[i]
        if ch in _CONSONANTS:
            roman = _CONSONANTS[ch]
            if i + 1 < len(word) and word[i + 1] == _NUKTA:
                roman = _NUKTA_FORMS.get(ch, roman)
                i += 1
            units.append([roman, "a", "inherent"])
        elif ch in _MATRAS and units and units[-1][2] == "inherent":
            units[-1][1], units[-1][2] = _MATRAS[ch], "matra"
        elif ch == _VIRAMA and units and units[-1][2] == "inherent":
            units[-1][1], units[-1][2] = "", "none"
        elif ch in (_ANUSVARA, _CHANDRABINDU):
            if units:
                units[-1].append("n")  # baad mein naak wali 'n' jodenge
        elif ch == _VISARGA:
            if units:
                units[-1].append("h")
        elif ch in _VOWELS:
            units.append(["", _VOWELS[ch], "vowel"])
        elif ch != _NUKTA:
            units.append([ch, "", "none"])
        i += 1
    return units


def _has_vowel(unit):
    return unit[2] in ("inherent", "matra", "vowel")


def _word(word):
    if word in _WORDS:
        return _WORDS[word]
    units = _syllables(word)
    if not units:
        return word
    # Hindi ka niyam: shabd ke aakhri akshar ka 'a' nahi bola jata (kal, kaam, yaad).
    if len(units) > 1 and units[-1][2] == "inherent":
        units[-1][1], units[-1][2] = "", "none"
    # Beech ka 'a' bhi gir jata hai jab dono taraf swar ho: ra-ha-taa -> rahtaa, sa-ma-jha-naa -> samajhnaa.
    for k in range(len(units) - 2, 0, -1):
        prev, cur, nxt = units[k - 1], units[k], units[k + 1]
        if cur[2] == "inherent" and len(cur) == 3 and _has_vowel(prev) and nxt[0] and _has_vowel(nxt):
            cur[1], cur[2] = "", "none"
    out = []
    for index, unit in enumerate(units):
        consonant, vowel, extras = unit[0], unit[1], unit[3:]
        piece = consonant + vowel
        for extra in extras:
            if extra == "n":
                following = units[index + 1][0] if index + 1 < len(units) else ""
                piece += "m" if following.startswith(_LABIALS) and following else "n"
            else:
                piece += extra
        out.append(piece)
    roman = "".join(out)
    # Hinglish mein aam taur par aise likhte hain: meraa -> mera, kahaan -> kahan, paanee -> paani, dilaao -> dilao.
    roman = re.sub(r"aa(?=[aeiou])", "a", roman)
    roman = re.sub(r"aa$", "a", roman)
    roman = re.sub(r"aan$", "an", roman)
    roman = re.sub(r"ee$", "i", roman)
    roman = re.sub(r"een$", "in", roman)
    roman = re.sub(r"oo$", "u", roman)
    return roman


def to_roman(text):
    """Text mein jahan Devanagari ho use Roman Hinglish bana do. Baaki text waisa hi rehta hai."""
    if not has_devanagari(text):
        return text
    converted = _DEVANAGARI_RUN.sub(lambda match: _word(match.group(0)), text)
    return converted.translate(_DIGITS)
