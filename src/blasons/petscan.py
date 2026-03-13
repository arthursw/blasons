"""PetScan queries for Commons categories and filename parsing."""

import httpx
import json
import urllib.parse
from pathlib import Path
from typing import Optional, Any
from .config import PETSCAN_URL, USER_AGENT, FOREIGN_KEYWORDS, CACHE_DIR

# Single broad category that covers all French commune coats of arms
CATEGORY = "Coats_of_arms_of_communes_of_France"

# Common filename prefixes to strip for extracting commune names
# Longer prefixes should come first for correct matching.
FILENAME_PREFIXES = [
    "Blasons des communes de l'",
    "Blasons des communes de ",
    "Armoiries des communes de l'",
    "Armoiries des communes de ",
    "Blason de l'",
    "Blason de ",
    "Armoiries de l'",
    "Armoiries de ",
    "Blason ville fr ",
    "Blason ",
    "Armoiries ",
    "Coats of arms of ",
    "Coat of arms of ",
]

def query_petscan(refresh: bool = False, timeout: int = 60) -> list[str]:
    """
    Query PetScan for all files in the broad category for French commune coats of arms.
    Uses cached results unless refresh=True.
    Returns list of filenames.
    """
    cache_file = CACHE_DIR / "petscan_files.json"
    if not refresh and cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            cached = json.load(f)
        print(f"  Loaded {len(cached)} files from cache")
        return cached

    # Build query parameters as dict for encoding
    params_dict = {
        "categories": CATEGORY,
        "language": "commons",
        "project": "commons",
        "depth": "1",
        "format": "json",
        "doit": "1",
    }
    # Encode each key=value, but keep ns[6] literal
    query_parts = []
    for k, v in params_dict.items():
        query_parts.append(f"{urllib.parse.quote(k)}={urllib.parse.quote(str(v))}")
    query_parts.append("ns[6]=1")  # literal brackets for File namespace
    query_string = "&".join(query_parts)
    url = f"{PETSCAN_URL}?{query_string}"

    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    filenames_set: set[str] = set()
    sources = data.get("*", [])
    for source in sources:
        pages = source.get("a", {}).get("*", [])
        for page in pages:
            title = page.get("title", "")
            if title:
                filenames_set.add(title)

    result = list(filenames_set)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result

def extract_commune_name_from_filename(filename: str) -> Optional[str]:
    """
    Attempt to extract the commune name from a blason filename.
    Strips known prefixes and file extension.
    Returns the candidate commune name or None if not parseable.
    """
    # Remove extensions
    name = filename
    for ext in [".svg", ".png", ".jpg", ".jpeg", ".tif", ".tiff"]:
        if name.lower().endswith(ext):
            name = name[: -len(ext)]

    # Strip "File:" prefix if still present
    if name.startswith("File:"):
        name = name[5:]

    # Try stripping common prefixes (longest first for correctness)
    for prefix in FILENAME_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break

    # Clean up: replace underscores with spaces, trim
    name = name.replace("_", " ").strip()

    if not name:
        return None

    return name

def is_foreign_keyword(filename: str) -> bool:
    """Check if filename contains foreign keywords indicating non-French blason."""
    lower = filename.lower()
    return any(keyword in lower for keyword in FOREIGN_KEYWORDS)

if __name__ == "__main__":
    # Quick test
    test_files = [
        "File:Blason ville fr L'Abergement-Clémenciat.svg",
        "Blason de Paris.svg",
        "Blason Lyon.svg",
        "Coats of arms of communes of Ain 01.svg",
        "Armoiries Marseille.png",
    ]
    for f in test_files:
        extracted = extract_commune_name_from_filename(f)
        foreign = is_foreign_keyword(f)
        print(f"{f} -> {extracted} (foreign={foreign})")
