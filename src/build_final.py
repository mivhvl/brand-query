#!/usr/bin/env python3
"""
Build the final results JSON from the manually selected Excel rows.

python src/build_final.py docs/brand_query_results.xlsx mkowalski    

Only rows with more than 0 matched URLs are included.

Requires openpyxl: python -m pip install openpyxl
"""
import json
import sys
from pathlib import Path

from openpyxl import load_workbook


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python build_final.py <table.xlsx> <name>")

    xlsx_path = Path(sys.argv[1])
    if not xlsx_path.is_absolute() and not xlsx_path.exists():
        xlsx_path = Path(__file__).resolve().parent.parent / xlsx_path
    if not xlsx_path.is_file():
        raise SystemExit(f"Excel file not found: {xlsx_path}")
    name = sys.argv[2].strip()
    if not name:
        raise SystemExit("Name cannot be empty.")

    sheet = load_workbook(xlsx_path, read_only=True, data_only=True).active

    headers = None
    results = []
    selected_brands = set()
    skipped = 0

    for row_number, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        values = list(row)

        # Find the header row by column names, even if the sheet has a title above it.
        if headers is None and "ID brandu" in values and "Query JSON" in values:
            headers = {str(value).strip(): i for i, value in enumerate(values) if value is not None}
            required_headers = {"ID brandu", "Query JSON", "Trafione unikalne URL-e"}
            missing = required_headers - headers.keys()
            if missing:
                raise SystemExit(f"Missing Excel columns: {', '.join(sorted(missing))}")
            continue

        if headers is None:
            continue

        brand = values[headers["ID brandu"]] if headers["ID brandu"] < len(values) else None
        query_cell = values[headers["Query JSON"]] if headers["Query JSON"] < len(values) else None
        count_cell = values[headers["Trafione unikalne URL-e"]] if headers["Trafione unikalne URL-e"] < len(values) else None

        if brand is None or not str(brand).strip():
            continue

        try:
            count = float(count_cell)
        except (TypeError, ValueError):
            skipped += 1 
            continue

        if count <= 0:
            skipped += 1
            continue

        brand = str(brand).strip()
        if brand in selected_brands:
            raise SystemExit(
                "Keep only the single best query for that brand in the Excel table."
            )

        try:
            query = json.loads(str(query_cell))
        except (TypeError, json.JSONDecodeError) as error:
            raise SystemExit(f"Invalid Query JSON for {brand!r} at row {row_number}: {error}")

        if not isinstance(query, dict) or not isinstance(query.get("required"), list):
            raise SystemExit(f"Query for {brand!r} at row {row_number} must contain a required list.")

        selected_brands.add(brand)
        results.append({"id": brand, **query})

    if headers is None:
        raise SystemExit("Could not find the header row in the Excel sheet.")
    if not results:
        raise SystemExit("No rows with positive URL counts.")

    output_path = Path("data") / "final" / f"{name}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"results": results}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved {len(results)} brands to {output_path}.")


if __name__ == "__main__":
    main()
