# Blasons — French Communes Coat of Arms Downloader

Automatically downloads SVG coat of arms (blasons) for all ~35,000 French communes from Wikimedia Commons, renames them following a strict convention, and organizes them by region and department.

## Prerequisites

- Download [communes-france-2025.csv](https://www.data.gouv.fr/api/1/datasets/r/f5df602b-3800-44d7-b2df-fa40a0350325) from the dedicated page on [data.gouv.fr/](https://www.data.gouv.fr/datasets/communes-et-villes-de-france-en-csv-excel-json-parquet-et-feather)
- [**uv**](https://docs.astral.sh/uv/) (Python project manager)
- A **Wikimedia Commons access token** (for better rate limits during downloads)

### API Access Summary

| Service | Auth required | Notes |
|---|---|---|
| Wikidata SPARQL | None | Public endpoint, just needs a `User-Agent` header |
| PetScan | None | Public Wikimedia tool, no account needed |
| Wikimedia Commons API | Optional (recommended) | Works without auth, but token gives higher rate limits |

### Getting Wikimedia Commons Bot Credentials

If you don't have them yet:

1. Log in to [Wikimedia Commons](https://commons.wikimedia.org/)
2. Go to [Special:BotPasswords](https://commons.wikimedia.org/wiki/Special:BotPasswords)
3. Create a bot password with **High-volume editing** and **Basic rights** grants
4. Note the bot username (format: `YourUser@BotName`) and the generated password

## Installation

```bash
cd blasons
uv sync
```

That's it. `uv` handles Python version, virtual environment, and all dependencies automatically from `pyproject.toml`.

## Configuration

Create a `.env` file at the project root (you can use the `.env.sample` file):

```env
# Required — from Special:BotPasswords
WIKIMEDIA_BOT_USERNAME=YourUser@BotName
WIKIMEDIA_BOT_PASSWORD=your_bot_password_here

# Optional (defaults shown)
DOWNLOAD_DELAY=1.0          # seconds between downloads
OUTPUT_DIR=./               # root output directory for blason folders
USER_AGENT=BlasonBot/1.0 (your@email.com)
```

> **Important**: Your `User-Agent` must include a way to contact you (email or URL), per [Wikimedia User-Agent policy](https://meta.wikimedia.org/wiki/User-Agent_policy).

## Usage

### Full run (Simple Plan — Wikidata + PetScan)

```bash
uv run blasons
```

This will:
1. Load `communes-france-2025.csv`
2. Query Wikidata SPARQL for blasons linked to French communes, regions, and departments
3. Query PetScan for blasons in Commons categories (per department)
4. Fuzzy-match PetScan results to communes
5. Batch-resolve download URLs via Commons API
6. Download all SVGs and place them in the folder structure

### Options

```bash
uv run blasons --help

# Run only on specific department(s)
uv run blasons --departments 01 75 2A

# Force re-download existing files
uv run blasons --force

# Dry run (discover blasons, don't download)
uv run blasons --dry-run

# Set custom delay between downloads
uv run blasons --delay 2.0
```

### Full Plan (with Commons search fallback)

```bash
uv run blasons --full
```

Adds per-commune Commons API search for communes not found via Wikidata/PetScan. Slower but more thorough.

## Output Structure

```
blasons/
  AUVERGNE_RHONE_ALPES/
    _AUVERGNE_RHONE_ALPES.svg              <- region blason
    01_AIN/
      _AIN.svg                              <- department blason
      STKBL01_01400_L_ABERGEMENT_CLEMENCIAT_01.svg
      STKBL01_01000_BOURG_EN_BRESSE_01.svg
      STKBL01_01000_BOURG_EN_BRESSE_02_NON_VERIFIE.svg
      ...
  ILE_DE_FRANCE/
    _ILE_DE_FRANCE.svg
    75_PARIS/
      _PARIS.svg
      ...
```

### File naming convention

```
STKBL{DEP}_{CODE_POSTAL}_{NOM_VILLE}_{INDEX:02d}.svg
```

| Field | Description | Example |
|---|---|---|
| `DEP` | Department code (2 chars) | `01`, `75`, `2A` |
| `CODE_POSTAL` | Postal code (5 digits) | `01400` |
| `NOM_VILLE` | City name, uppercase, underscores | `BOURG_EN_BRESSE` |
| `INDEX` | Blason order number | `01`, `02` |

A `_NON_VERIFIE` suffix is appended when:
- The filename on Commons contains foreign keywords (`arms`, `wappen`, `escudo`, `herb`...)
- The fuzzy match confidence is low
- The blason appears to be for a historical entity rather than the modern commune

## Logs and Reports

After a run, check `data/`:

| File | Content |
|---|---|
| `data/download_log.csv` | Every download attempt with status (ok/error/skipped) |
| `data/communes_sans_blason.csv` | Communes where no blason was found |

## Rate Limits

The tool respects Wikimedia rate limits:
- **Wikidata SPARQL**: 1 query returns all results (no rate limit concern)
- **PetScan**: ~100 queries total (one per department), no strict limit
- **Commons API**: Batches of 50 file URLs per request
- **Downloads**: 1 file/second by default (configurable via `--delay`)

## Development

```bash
# Add a dependency
uv add some-package

# Run tests
uv run pytest

# Run a specific module
uv run python -m src.wikidata
```

## Troubleshooting

**PetScan returns empty results**
Some departments have differently named categories on Commons. Check the category name manually at `https://commons.wikimedia.org/wiki/Category:Coats_of_arms_of_communes_of_{Department}`.

**SPARQL query times out**
The Wikidata endpoint has a 60s timeout. The query is designed to stay within limits, but if it fails, the tool retries with a per-region split.

**Low match rate from PetScan**
Blason filenames on Commons are inconsistent. The fuzzy matcher uses `rapidfuzz` with a default threshold of 85. Lower it with `--match-threshold 70` for more matches (at the cost of more `_NON_VERIFIE` flags).
