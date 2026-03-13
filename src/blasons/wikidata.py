"""Wikidata SPARQL queries for communes, regions, and departments."""

import httpx
import json
import time
from pathlib import Path
from urllib.parse import unquote
from typing import Any
from .config import WIKIDATA_SPARQL, USER_AGENT, CACHE_DIR


# SPARQL queries
QUERY_COMMUNES = """
SELECT ?commune ?communeLabel ?image ?codeInsee WHERE {
  ?commune wdt:P31/wdt:P279* wd:Q484170 .
  ?commune wdt:P94 ?image .
  ?commune wdt:P374 ?codeInsee .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr" }
}
"""

QUERY_REGIONS = """
SELECT ?region ?regionLabel ?image WHERE {
  ?region wdt:P31 wd:Q36784 .
  ?region wdt:P94 ?image .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr" }
}
"""

QUERY_DEPARTMENTS = """
SELECT ?dep ?depLabel ?image ?depCode WHERE {
  ?dep wdt:P31 wd:Q6465 .
  ?dep wdt:P94 ?image .
  ?dep wdt:P2586 ?depCode .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr" }
}
"""


def _load_cache(cache_file: Path) -> list[dict[str, Any]] | None:
    """Load cached results from JSON file. Returns None if cache doesn't exist."""
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_cache(cache_file: Path, data: list[dict[str, Any]]) -> None:
    """Save results to JSON cache file."""
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def query_wikidata(sparql: str, timeout: int = 120, retries: int = 3) -> dict[str, Any]:
    """
    Execute a SPARQL query against the Wikidata endpoint with retries.
    Returns the JSON response.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/sparql-results+json",
    }
    data = {
        "query": sparql,
        "format": "json",
    }
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(WIKIDATA_SPARQL, headers=headers, data=data)
                response.raise_for_status()
                return response.json()
        except (httpx.RequestError, httpx.HTTPStatusError):
            if attempt == retries - 1:
                raise
            backoff = 2 ** attempt
            print(f"Wikidata query failed (attempt {attempt+1}/{retries}), retrying in {backoff}s...")
            time.sleep(backoff)
        except json.JSONDecodeError:
            if attempt == retries - 1:
                raise
            print(f"JSON decode error from Wikidata, retrying in 2s...")
            time.sleep(2)
    return {}  # unreachable, but satisfies type checker


def fetch_communes(refresh: bool = False) -> list[dict[str, Any]]:
    """
    Fetch all French communes that have a coat of arms image.
    Uses cached results unless refresh=True.
    """
    cache_file = CACHE_DIR / "wikidata_communes.json"
    if not refresh:
        cached = _load_cache(cache_file)
        if cached is not None:
            print(f"  Loaded {len(cached)} communes from cache")
            return cached

    data = query_wikidata(QUERY_COMMUNES)
    results = []
    for binding in data["results"]["bindings"]:
        results.append({
            "qid": binding["commune"]["value"].split("/")[-1],
            "label": binding["communeLabel"]["value"],
            "image": unquote(binding["image"]["value"].split("/")[-1]),
            "code_insee": binding["codeInsee"]["value"],
        })

    _save_cache(cache_file, results)
    return results


def fetch_regions(refresh: bool = False) -> list[dict[str, Any]]:
    """
    Fetch all French regions that have a coat of arms image.
    Uses cached results unless refresh=True.
    """
    cache_file = CACHE_DIR / "wikidata_regions.json"
    if not refresh:
        cached = _load_cache(cache_file)
        if cached is not None:
            print(f"  Loaded {len(cached)} regions from cache")
            return cached

    data = query_wikidata(QUERY_REGIONS)
    results = []
    for binding in data["results"]["bindings"]:
        results.append({
            "qid": binding["region"]["value"].split("/")[-1],
            "label": binding["regionLabel"]["value"],
            "image": unquote(binding["image"]["value"].split("/")[-1]),
        })

    _save_cache(cache_file, results)
    return results


def fetch_departments(refresh: bool = False) -> list[dict[str, Any]]:
    """
    Fetch all French departments that have a coat of arms image.
    Uses cached results unless refresh=True.
    """
    cache_file = CACHE_DIR / "wikidata_departments.json"
    if not refresh:
        cached = _load_cache(cache_file)
        if cached is not None:
            print(f"  Loaded {len(cached)} departments from cache")
            return cached

    data = query_wikidata(QUERY_DEPARTMENTS)
    results = []
    for binding in data["results"]["bindings"]:
        results.append({
            "qid": binding["dep"]["value"].split("/")[-1],
            "label": binding["depLabel"]["value"],
            "image": unquote(binding["image"]["value"].split("/")[-1]),
            "dep_code": binding["depCode"]["value"],
        })

    _save_cache(cache_file, results)
    return results
