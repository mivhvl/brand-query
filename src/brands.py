#!/usr/bin/env python3
"""
Generate a brand list with aliases and ambiguity flags.

pip install groq

read -s "GROQ_API_KEY?Podaj klucz Groq: "; echo; export GROQ_API_KEY (need GROQ_API_KEY)

python src/brands.py --out data/input/brands.json --brands-per-call 1
"""
import argparse
import json
import re
from pathlib import Path

from common import make_slug

MODEL = "openai/gpt-oss-120b"
CATEGORIES = ["whisky", "vodka", "rum", "gin", "beer"]
REGIONS = ["Poland", "USA"]


def create_prompt(cat, region, n, skip_brands):
    return f"""Suggest a maximum of {n} real, established alcohol brands in the category '{cat}' that are most famous or sold in {region}.
        If you are not sure, you can find less than {n} brands. Do not invent brands or details just to reach {n}.
        Do NOT repeat these brands: {', '.join(skip_brands[-150:]) or '(none)'}.

        Return ONLY a valid JSON array, with no explanation or markdown. Each item must have this format:
        {{
        "name": "official brand name",
        "aliases": ["up to 5 established alternative names or spellings"],
        "ambiguous": true,
        "ambiguity_reason": "short reason, or an empty string if not ambiguous",
        "context": ["up to 4 distinctive product or variant keywords, WITHOUT the brand name"]
        }}

        RULES FOR "aliases":
        - Include ONLY established, widely used stand-in names, colloquial shortcuts, or acronyms for the ENTIRE brand (e.g., "Bud", "JW").
        - Do NOT add category names to the brand (e.g., "Budweiser Beer").
        - Do NOT include product variants, flavors, or lines (e.g., "Bison Grass") — put them in "context".
        - Do NOT include spelling/diacritic variations (removing accents, spaces, or hyphens).
        - Do NOT include parent companies, manufacturers, or sister brands.
        - Do NOT invent names. If no reliable alias exists, use [].

        RULES "ambiguous":
        - Set true if the full brand name is also commonly used for an person, place, company, event, or other topic.
        - If ambiguous is true, give a short reason. Otherwise use an empty string for "ambiguity_reason".
        - When you are unsure whether the full name has another common meaning, choose true.
        
        RULES FOR "context":
        - Include ONLY real product lines or named variants of this brand, converted to lowercase kebab-case (e.g., "carta-blanca", "old-no-7").
        - Return ONLY the variant name WITHOUT the brand name or its aliases (e.g., use "original-spiced", NOT "captain-morgan-spiced").
        - NEVER include standalone generic terms, categories, or single colors (e.g., NO "beer", "vodka", "light", "dry", "premium", "black", "red").
        - Colors or descriptors are allowed ONLY when combined into a full variant name.
        - Return up to 6 unique variants. If none exist or unsure, use [].
        """

def parse_json(text):
    m = re.search(r"\[.*\]", text, re.S)
    return json.loads(m.group(0)) if m else []

def add_brand(brands, item, cat, region):
    # Get official brand name
    name = (item.get("name") or "").strip()
    if not name:
        return
    # Get unique aliases
    aliases = []
    for alias in item.get("aliases") or []:
        alias = alias.strip()
        if alias and alias not in aliases:
            aliases.append(alias)
    # Get normalized brand slug (key)
    key = make_slug(name).replace("-", "")
    if not key:
        return
    # Update info if brand exists, than end function
    if key in brands:
        this_brand = brands[key]
        if region not in this_brand["regions"]:
            this_brand["regions"].append(region) # Add new region
        for alias in aliases:
            if alias not in this_brand["aliases"]:
                this_brand["aliases"].append(alias) # Add new aliases
        if item.get("ambiguous"):
            this_brand["ambiguous"] = True # Set True if ambiguous
            reason = (item.get("ambiguity_reason") or "").strip()
            if reason and not this_brand.get("ambiguity_reason"):
                this_brand["ambiguity_reason"] = reason  # Add an ambiguity reason, only if the previous reason not exists
        return
    # Get context terms
    context = []
    for term in item.get("context") or []:
        term = term.strip().lower()
        if term and term not in context:
            context.append(term)

    brands[key] = {
        "name": name,
        "category": cat, # item.get("category") ????
        "regions": [region],
        "aliases": aliases,
        "ambiguous": bool(item.get("ambiguous")),
        "ambiguity_reason": (item.get("ambiguity_reason") or "").strip(),
        "context": context[:6],
    }

def main():
    # Define Script
    ap = argparse.ArgumentParser()
    repo_root = Path(__file__).resolve().parent.parent
    ap.add_argument("--input")
    ap.add_argument("--out", default=str(repo_root / "data/input/brands.json"))
    ap.add_argument("--brands-per-call", type=int, default=10)
    a = ap.parse_args()

    brands = {}
    if a.input:
        input_path = Path(a.input)
        if not input_path.is_absolute() and not input_path.exists():
            input_path = repo_root / input_path
        with input_path.open(encoding="utf-8") as input_file:
            input_items = json.load(input_file)
        for it in input_items:
            add_brand(brands, it, it.get("category", "other"), it.get("region", "unknown"))
    else:
        from groq import Groq
        client = Groq()
        for cat in CATEGORIES:
            for region in REGIONS:
                skip_brands = [brand["name"] for brand in brands.values() if brand["category"] == cat] # Avoid brands duplicates
                try:
                    response = client.chat.completions.create(model=MODEL,
                                                              messages=[{"role": "user","content": create_prompt(cat, region, a.brands_per_call, skip_brands)}],)
                    answer = response.choices[0].message.content or ""
                    items = parse_json(answer)
                except Exception as e:
                    print(f"! {cat}/{region}: {e}")
                    continue
                before = len(brands)
                for item in items:
                    add_brand(brands, item, cat, region)
                print(f"{cat:8} {region:38} +{len(brands) - before}")

    out = sorted(brands.values(), key=lambda b: (b["category"], b["name"].lower()))
    output_path = Path(a.out)
    if not output_path.is_absolute() and not output_path.exists():
        output_path = repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(out, output_file, ensure_ascii=False, indent=1)
    amb = sum(b["ambiguous"] for b in out)
    print(f"\nSaved {len(out)} brands in {output_path} (ambiguous: {amb})")

if __name__ == "__main__":
    main()
