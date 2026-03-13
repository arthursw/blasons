# Implementation Plan — French Communes Coat of Arms (Blasons) Downloader

## Input Data

- `communes-france-2025.csv` — ~35,000 communes with columns including: `code_insee`, `nom_standard`, `nom_sans_accent`, `nom_standard_majuscule`, `reg_code`, `reg_nom`, `dep_code`, `dep_nom`, `code_postal`, `url_wikipedia`.

---

Two bulk data sources, no per-commune scraping.

---

## Phase 1 — Bulk Blason Discovery via Wikidata SPARQL

### 1.1 Query Wikidata for commune blasons

Use the Wikidata SPARQL endpoint (`https://query.wikidata.org/sparql`) to fetch all French communes that have a coat of arms image (property `P94`).

```sparql
SELECT ?commune ?communeLabel ?image ?codeInsee WHERE {
  ?commune wdt:P31/wdt:P279* wd:Q484170 .  # instance of commune of France
  ?commune wdt:P94 ?image .                  # coat of arms image
  ?commune wdt:P374 ?codeInsee .             # INSEE code
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr" }
}
```

- Returns: commune Wikidata ID, label, SVG filename on Commons, INSEE code.
- Match results to CSV rows using `code_insee`.
- One single HTTP request, thousands of results.

### 1.2 Query Wikidata for region and department blasons

```sparql
# Regions
SELECT ?region ?regionLabel ?image WHERE {
  ?region wdt:P31 wd:Q36784 .    # French region
  ?region wdt:P94 ?image .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr" }
}

# Departments
SELECT ?dep ?depLabel ?image ?depCode WHERE {
  ?dep wdt:P31 wd:Q6465 .        # French department
  ?dep wdt:P94 ?image .
  ?dep wdt:P2586 ?depCode .      # department code
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr" }
}
```

---

## Phase 2 — Bulk Blason Discovery via PetScan

For communes not matched in Phase 1, use PetScan to enumerate Commons categories.

### 2.1 Query PetScan per department

PetScan (`https://petscan.wmflabs.org/`) can list all files within a Commons category tree. For each department, query categories like:

- `Coats of arms of communes of Ain`
- `Coats of arms of communes of Aisne`
- etc.

Parameters:
- `language=commons`, `project=wikimedia`
- `categories=Coats of arms of communes of {department}`
- `depth=3` (to catch subcategories)
- `ns[6]=1` (File namespace)
- `output_compatability=catscan` / `format=json`

This returns a list of filenames like `Blason ville fr L'Abergement-Clémenciat.svg`.

### 2.2 Match PetScan results to communes

- Parse filenames to extract commune names (strip `Blason ville fr `, `Blason de `, etc.)
- Fuzzy-match against `nom_standard` / `nom_sans_accent` from CSV
- Flag as `_NON_VERIFIE` if:
  - Filename contains foreign keywords: `arms`, `wappen`, `coat of arms of`, `escudo`, `herb`, `blazono`
  - Match is loose / low confidence (fuzzy score below threshold)

---

## Phase 3 — Download SVGs from Wikimedia Commons

### 3.1 Resolve download URLs

Use the Commons API in **batches of 50 titles** per request:

```
https://commons.wikimedia.org/w/api.php?action=query&titles=File:Blason1.svg|File:Blason2.svg|...&prop=imageinfo&iiprop=url&format=json
```

This returns direct download URLs for up to 50 files at once.

### 3.2 Download files

- Sequential downloads with a polite delay (1 request/second) to respect Wikimedia rate limits.
- Set a proper `User-Agent` header identifying the project.
- Validate each downloaded file is valid SVG (starts with `<svg` or `<?xml`).
- Skip non-SVG files (PNG, JPG, etc.).

### 3.3 Naming convention

For each downloaded file, apply the naming rule:

```
STKBL{DEP}_{CODE_POSTAL}_{NOM_VILLE}_{INDEX:02d}.svg
```

- `DEP` = `dep_code` from CSV (2 chars)
- `CODE_POSTAL` = `code_postal` from CSV (5 digits)
- `NOM_VILLE` = `nom_sans_accent` from CSV → UPPERCASE, spaces/hyphens → `_`
- `INDEX` = sequential number starting at `01` (multiple blasons per commune possible)
- Append `_NON_VERIFIE` before `.svg` if flagged foreign or low-confidence match

### 3.4 Directory structure

```
blasons/
  AUVERGNE_RHONE_ALPES/
    _AUVERGNE_RHONE_ALPES.svg
    01_AIN/
      _AIN.svg
      STKBL01_01400_L_ABERGEMENT_CLEMENCIAT_01.svg
      ...
  ...
```

- Region folder: `reg_nom` → UPPERCASE, spaces/hyphens → `_`
- Department folder: `{dep_code}_{dep_nom}` → UPPERCASE, spaces/hyphens → `_`
- Region blason: `_{REGION}.svg`
- Department blason: `_{DEPARTMENT}.svg`

---

## Phase 4 — Logging and Resume

### 4.1 Download log

Save `data/download_log.csv` with columns:
- `code_insee`, `commune`, `source` (wikidata/petscan), `commons_filename`, `local_filename`, `status` (ok/error/skipped), `timestamp`

### 4.2 Missing blasons report

Save `data/communes_sans_blason.csv` — all communes where no blason was found.

### 4.3 Incremental mode

- Before downloading, check if the target file already exists on disk.
- Skip existing files by default. Add a `--force` flag to re-download.

---

## Phase 5 — Technical Stack

### 5.1 Project management — uv

The project uses [uv](https://docs.astral.sh/uv/) for dependency and environment management. All config lives in `pyproject.toml`.

### 5.2 Dependencies

- `polars` — fast CSV loading and manipulation
- `httpx` — modern HTTP client (sync mode, for rate-limit compliance)
- `unidecode` — accent removal / transliteration
- `rapidfuzz` — fuzzy string matching (PetScan filenames → commune names)
- `tqdm` — progress bars
- `python-dotenv` — load `.env` config

### 5.3 Project structure

```
blasons/
  pyproject.toml              — project metadata, dependencies, scripts (managed by uv)
  uv.lock                     — lockfile (auto-generated)
  .env                        — secrets and config (not committed)
  .python-version             — pinned Python version
  specs.md
  plan.md
  README.md
  communes-france-2025.csv
  data/
    download_log.csv
    communes_sans_blason.csv
  src/
    blasons/
      __init__.py
      __main__.py      — CLI entry point
      config.py        — paths, constants, rate-limit settings, User-Agent
      communes.py      — load CSV with polars, normalize names
      wikidata.py      — SPARQL queries for communes/regions/departments
      petscan.py       — PetScan category enumeration + filename parsing
      matcher.py       — match discovered blasons to communes (exact + fuzzy)
      downloader.py    — batch URL resolution + sequential SVG download
      namer.py         — STKBL filename generation
      tree.py          — directory structure creation
```

### 5.3 Pipeline execution order

```
1. Load CSV (communes.py)
2. Create directory tree (tree.py)
3. Query Wikidata SPARQL for communes + regions + departments (wikidata.py)
4. Match Wikidata results to CSV by code_insee (matcher.py)
5. For unmatched communes: query PetScan per department (petscan.py)
6. Match PetScan filenames to remaining communes via fuzzy match (matcher.py)
7. Batch-resolve Commons download URLs (downloader.py)
8. Download SVGs sequentially with delay (downloader.py)
9. Rename and place files (namer.py + tree.py)
10. Generate logs and reports (main.py)
```
