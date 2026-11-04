import re
import unicodedata

TYPE_CAT = {
    "whisky":  ["whisky", "whiskey", "bourbon", "scotch", "single-malt", "blended"],
    "vodka":   ["wodka", "wodki", "vodka"],
    "rum":     ["rum", "rumu", "mojito", "cuba-libre", "daiquiri"],
    "gin":     ["gin", "ginu", "gin-tonic", "tonic", "london-dry"],
    "beer":    ["piwo", "piwa", "beer", "lager", "ipa", "stout", "pilsner"]
}
GENERIC_DRINK = ["alkohol", "alkoholu", "koktajl", "koktajlu", "alcohol", "spirits", "cocktail", "cocktails"]

MAP = str.maketrans({"ł": "l", "ø": "o", "đ": "d", "ß": "ss", "æ": "ae", "œ": "oe", "’": "'", "`": "'"})

def normalize_text(text: str) -> str:
    """Normalize text: small letters, map to basic chars"""
    text = text.lower().translate(MAP)
    return ''.join(c for c in unicodedata.normalize("NFKD", text) 
                   if not unicodedata.combining(c))

def make_slug(text: str) -> str:
    """Generate a basic slug"""
    return re.sub(r"[^a-z0-9]+", "-", normalize_text(text)).strip("-")

def select_unique(seq):
    out = []
    for x in seq:
        if x and x not in out:
            out.append(x)
    return out

def slug_forms(text: str):
    """Generate 2 possible forms of slugs: a) jack-daniels, b) jack-daniel-s"""
    n = normalize_text(text)
    return select_unique([make_slug(n.replace("'", "")),make_slug(n.replace("'", " "))])

