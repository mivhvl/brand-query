#!/usr/bin/env python3
"""Send queries.json entries to the URL keyword estimator.

  python src/estimator.py --queries data/queries/queries.json --out data/results/results.json
  python src/estimator.py --only "Jack Daniel's"
"""
import argparse
import json
import subprocess
from pathlib import Path

URL = "https://urlkeywords.ctpl.dev/keywordURLs"


def main():
    parser = argparse.ArgumentParser()
    repo_root = Path(__file__).resolve().parent.parent
    parser.add_argument("--queries", default=str(repo_root / "data/queries/queries.json"))
    parser.add_argument("--out", default=str(repo_root / "data/results/results.json"))
    parser.add_argument("--only", help="run only queries for this brand in the list")
    args = parser.parse_args()

    queries_path = Path(args.queries)
    if not queries_path.is_absolute() and not queries_path.exists():
        queries_path = repo_root / queries_path
    with queries_path.open(encoding="utf-8") as f:
        queries = json.load(f)

    if args.only:
        queries = [q for q in queries if q["id"] == args.only]
        if not queries:
            print(f"Brand not found: {args.only}")
            return

    results = []
    output_path = Path(args.out)
    if not output_path.is_absolute() and not output_path.exists():
        output_path = repo_root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for i, item in enumerate(queries, 1):
        payload = json.dumps(item["query"], ensure_ascii=False)

        response = subprocess.run(
            ["curl", "--silent", "--show-error", "--data", payload, URL],
            capture_output=True,
            text=True,
        )

        try:
            response_data = json.loads(response.stdout)
        except json.JSONDecodeError:
            response_data = response.stdout

        result = {
            "id": item.get("id"),
            "option": item.get("option"),
            "form": item.get("form"),
            "final_eligible": item.get("final_eligible"),
            "query": item["query"],
            "response": response_data,
        }
        if response.returncode != 0:
            result["error"] = response.stderr.strip()
        results.append(result)

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"[{i}/{len(queries)}] {item.get('id')} / {item.get('option')} / {item.get('form')}")

    print(f"Saved {len(results)} results to {output_path}")


if __name__ == "__main__":
    main()
