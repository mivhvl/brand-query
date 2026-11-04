#!/usr/bin/env python3
"""
Generate query variants from brands.json;

Input brand fields are produced by brands.py: name, category, aliases,
ambiguous, and context. Each output entry keeps its metadata alongside the
estimator payload in the `query` field.

  python src/queries.py --brands data/input/brands.json --out data/gueries/queries.json --mode_r c --mode_o m --threshold 1
  
  python src/queries.py --only "Jack Daniel's"
"""
import argparse
import json
from pathlib import Path

from common import TYPE_CAT, GENERIC_DRINK, select_unique, make_slug, slug_forms

MAX_FORMS = 3


def brand_forms(brand):
    """Get up to MAX_FORMS brand name and alias forms."""
    forms = []
    for name in [brand["name"]] + brand.get("aliases", []):
        forms.extend(slug_forms(name))
    return select_unique(forms)[:MAX_FORMS]


def kw(keyword, mode="m"):
    """Create one estimator keyword with the selected matching mode."""
    return {"keyword": keyword, "mode": mode}


def make_query(required, optional=None, mode_r="m", mode_o="m", threshold=1):
    """Create an estimator query using the requested modes and threshold."""
    query = {"required": [kw(k, mode_r) for k in required]}
    if optional:
        query["optional"] = [kw(k, mode_o) for k in optional]
        query["optionalThreshold"] = threshold
    return query


def build(brand, mode_r="m", mode_o="m", threshold=1):
    """Build base and context query variants for one brand."""
    forms = brand_forms(brand)
    if not forms:
        return []

    category_terms = TYPE_CAT.get(brand.get("category"), GENERIC_DRINK)
    context_terms = [make_slug(term) for term in brand.get("context", [])]
    form_keys = {form.replace("-", "") for form in forms}
    context_terms = [
        term for term in context_terms
        if term and term.replace("-", "") not in form_keys
    ]
    optional_terms = select_unique(category_terms + context_terms)

    out = []
    seen = set()

    def push(option, form, query):
        """Add a unique query variant with the minimum useful metadata."""
        key = json.dumps(query, sort_keys=True)
        if key in seen:
            return
        seen.add(key)
        out.append({
            "id": brand["name"],
            "option": option,
            "form": form,
            "query": query,
            "final_eligible": not (option == "base" and brand.get("ambiguous", False)),
        })

    for form in forms:
        push("base", form, make_query([form], mode_r=mode_r))
        push(
            "ctx",
            form,
            make_query([form], optional_terms, mode_r, mode_o, threshold),
        )
    return out


def main():
    parser = argparse.ArgumentParser()
    repo_root = Path(__file__).resolve().parent.parent
    parser.add_argument("--brands", default=str(repo_root / "data/input/brands.json"))
    parser.add_argument("--out", default=str(repo_root / "data/queries/queries.json"))
    parser.add_argument("--only", help="generate queries for this exact brand name only")
    parser.add_argument("--mode_r", choices=["m", "c"], default="m")
    parser.add_argument("--mode_o", choices=["m", "c"], default="m")
    parser.add_argument("--threshold", type=int, default=1)
    args = parser.parse_args()

    if args.threshold < 1:
        parser.error("--threshold must be at least 1")

    brands_path = Path(args.brands)
    if not brands_path.is_absolute() and not brands_path.exists():
        brands_path = repo_root / brands_path
    with brands_path.open(encoding="utf-8") as f:
        brands = json.load(f)

    if args.only:
        brands = [brand for brand in brands if brand.get("name") == args.only]
        if not brands:
            parser.error(f"brand not found in {args.brands}: {args.only}")

    queries = []
    for brand in brands:
        queries.extend(build(brand, args.mode_r, args.mode_o, args.threshold))

    output_path = Path(args.out)
    if not output_path.is_absolute() and not output_path.exists():
        output_path = repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(queries, f, ensure_ascii=False, indent=2)

    per_option = {}
    for query in queries:
        per_option[query["option"]] = per_option.get(query["option"], 0) + 1
    print(f"Brands: {len(brands)}, Queries: {len(queries)} -> {output_path}")
    print("Distribution:", per_option)


if __name__ == "__main__":
    main()
