"""Configuration constants and paths for the blasons project."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# Project root (parent of src/blasons)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# Paths
CSV_PATH = Path(os.getenv("CSV_PATH", PROJECT_ROOT / "communes-france-2025.csv"))
OUTPUT_ROOT = Path(os.getenv("OUTPUT_ROOT", PROJECT_ROOT / "blasons"))
DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
DOWNLOAD_LOG = DATA_DIR / "download_log.csv"
MISSING_COMMUNES = DATA_DIR / "communes_sans_blason.csv"
RASTER_LOG = DATA_DIR / "raster_blasons.csv"

# Cache directory for query results
CACHE_DIR = DATA_DIR / "cache"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Rate limiting (requests per second)
RATE_LIMIT = float(os.getenv("RATE_LIMIT", "1.0"))
COMMONS_BATCH_SIZE = int(os.getenv("COMMONS_BATCH_SIZE", "50"))

# HTTP User-Agent
USER_AGENT = os.getenv(
    "USER_AGENT",
    "BlasonsDownloader/0.1.0 (https://github.com/example/blasons; contact@example.com)"
)

# Wikidata SPARQL endpoint
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

# Commons API
COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# PetScan base URL
PETSCAN_URL = "https://petscan.wmcloud.org/"

# Fuzzy matching threshold (0-100)
FUZZY_THRESHOLD = int(os.getenv("FUZZY_THRESHOLD", "85"))

# Foreign keywords to flag as non-verified
FOREIGN_KEYWORDS = {
    "arms", "wappen", "coat of arms of", "escudo", "herb", "blazono", "stemma", "brasão"
}

# Naming conventions
def normalize_commune_name(name: str) -> str:
    """Normalize commune name: lowercase, remove accents, replace spaces/hyphens with underscores."""
    from unidecode import unidecode
    normalized = unidecode(name).lower()
    normalized = normalized.replace(" ", "_").replace("-", "_")
    # Remove any characters that are not alphanumeric or underscore
    normalized = "".join(c if c.isalnum() or c == "_" else "_" for c in normalized)
    return normalized.upper()

def format_region_name(region: str) -> str:
    """Format region name for directory: uppercase with underscores."""
    return region.upper().replace(" ", "_").replace("-", "_")

def format_department_name(dept: str) -> str:
    """Format department name for directory: uppercase with underscores."""
    return dept.upper().replace(" ", "_").replace("-", "_")
