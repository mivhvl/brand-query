# Wyszukiwanie zapytań dla marek alkoholi

Projekt tworzy listę marek alkoholi, generuje dla nich zapytania według ustalonego wzorca, pobiera wyniki estymatora URL-i i buduje końcowy plik JSON na podstawie ręcznej analizy wyników. W trudniejszych przypadkach analiza może być wspierana przez Claude AI.

## Struktura

- `src/` – skrypty i wspólne funkcje Pythona.
- `data/input/` – wejściowa lista marek (`brands.json`).
- `data/queries/` – wygenerowane zapytania dla marek.
- `data/results/` – odpowiedzi estymatora.
- `data/final/` – końcowe pliki JSON, np. `mkowalski.json`.
- `docs/` – arkusz Excel z analizą zapytań i materiały źródłowe.
- `requirements.txt` – biblioteki wymagane przez projekt.

## Instalacja

Uruchom polecenia z katalogu głównego repozytorium:

```bash
python -m pip install -r requirements.txt
```

Do generowania propozycji marek potrzebny jest klucz API Groq. Skrypt `brands.py` korzysta z modelu `openai/gpt-oss-120b`, wywoływanego przez Groq. Model proponuje nazwy marek dla podanej **kategorii** i **regionu** oraz uzupełnia aliasy, informację o niejednoznaczności nazwy i przykładowe linie produktów. Nie tworzy zapytań do estymatora — te generuje deterministycznie `queries.py` na podstawie danych marek.

Wpisz klucz API w ukrytym monicie:

```bash
read -s "GROQ_API_KEY?Podaj klucz Groq: "; echo; export GROQ_API_KEY
```

## Użycie

1. Wygeneruj maksymalnie 10 marek dla każdej kategorii i regionu:

   ```bash
   python src/brands.py --brands-per-call 10 --out data/input/brands.json
   ```

   Bez `--input` skrypt pobiera propozycje przez API Groq. Z `--input plik.json` przetwarza ustaloną listę marek.

2. Wygeneruj zapytania:

   ```bash
   python src/queries.py --brands data/input/brands.json --out data/queries/queries.json
   ```

   Możesz ograniczyć generowanie do jednej marki przez `--only "Jack Daniel's"`. Tryby dopasowania ustawiają opcje `--mode_r` i `--mode_o` (`m` lub `c`), a `--threshold` określa minimalną liczbę dopasowanych słów opcjonalnych.

3. Pobierz wyniki estymatora:

   ```bash
   python src/estimator.py --queries data/queries/queries.json --out data/results/results.json
   ```

   Opcja `--only "Jack Daniel's"` uruchamia tylko zapytania dla wskazanej marki. Skrypt wymaga dostępu do usługi estymatora.

4. Zbuduj końcowy JSON z arkusza, po ręcznym wyborze najlepszych zapytań dla brandów:

   ```bash
   python src/build_final.py docs/brand_query_results.xlsx mkowalski
   ```

   Wynik zapisze się w `data/final/mkowalski.json`. Uwzględniane są tylko wiersze z dodatnią liczbą trafionych URL-i.

## Wspólne funkcje (`src/common.py`)

- `normalize_text()` – upraszcza zapis tekstu, m.in. usuwa znaki diakrytyczne.
- `make_slug()` – zamienia tekst na zapis z małych liter i myślników.
- `slug_forms()` – tworzy warianty zapisu nazwy marki.
- `select_unique()` – usuwa puste i powtarzające się elementy, zachowując kolejność.
- `TYPE_CAT` i `GENERIC_DRINK` – słowniki stałych słów kategorii i ogólnych określeń napojów.

## Prompt do generowania marek

Poniższy szablon jest wysyłany do modelu dla każdej pary kategorii i regionu. `{n}`, `{cat}`, `{region}` oraz lista pomijanych marek są wypełniane przez skrypt.

```text
Suggest a maximum of {n} real, established alcohol brands in the category '{cat}' that are most famous or sold in {region}.
If you are not sure, you can find less than {n} brands. Do not invent brands or details just to reach {n}.
Do NOT repeat these brands: {skip_brands}.

Return ONLY a valid JSON array, with no explanation or markdown. Each item must have this format:
{
  "name": "official brand name",
  "aliases": ["up to 5 established alternative names or spellings"],
  "ambiguous": true,
  "ambiguity_reason": "short reason, or an empty string if not ambiguous",
  "context": ["up to 4 distinctive product or variant keywords, WITHOUT the brand name"]
}

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
```
