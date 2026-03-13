"""Download blason files from Wikimedia Commons with rate limiting."""

import json
import time
import httpx
from pathlib import Path
from typing import Optional
from .config import COMMONS_API, USER_AGENT, COMMONS_BATCH_SIZE, RATE_LIMIT, CACHE_DIR


def batch_resolve_urls(
    filenames: list[str],
    batch_size: int = COMMONS_BATCH_SIZE,
    refresh: bool = False,
) -> dict[str, str]:
    """
    Given a list of filenames (e.g., "Blason ville fr Paris.svg"),
    resolve their direct download URLs from Commons API.
    Uses cached results and only queries uncached filenames unless refresh=True.
    Returns dict: filename -> URL.
    """
    cache_file = CACHE_DIR / "commons_urls.json"

    # Load existing cache
    cached_urls: dict[str, str] = {}
    if not refresh and cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_urls = json.load(f)

    # Determine which filenames still need resolving
    if refresh:
        to_resolve = filenames
    else:
        to_resolve = [f for f in filenames if f not in cached_urls]

    if to_resolve:
        print(f"  Resolving {len(to_resolve)} new URLs ({len(cached_urls)} already cached)")
    else:
        print(f"  All {len(cached_urls)} URLs loaded from cache")
        # Return only the subset we need
        return {f: cached_urls[f] for f in filenames if f in cached_urls}

    headers = {"User-Agent": USER_AGENT}
    total_batches = (len(to_resolve) + batch_size - 1) // batch_size

    for batch_idx, i in enumerate(range(0, len(to_resolve), batch_size), 1):
        batch = to_resolve[i : i + batch_size]
        titles = "|".join([f"File:{name}" for name in batch])

        params = {
            "action": "query",
            "titles": titles,
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json",
        }

        try:
            with httpx.Client(timeout=30) as client:
                response = client.get(COMMONS_API, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"  Batch {batch_idx}/{total_batches} failed: {e}, saving progress and continuing")
            continue

        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1":
                continue
            imageinfo = page.get("imageinfo", [])
            if imageinfo:
                url = imageinfo[0].get("url")
                title = page.get("title")
                if title.startswith("File:"):
                    title = title[5:]
                cached_urls[title] = url

        # Save after every batch so progress is never lost
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cached_urls, f, ensure_ascii=False)

        if batch_idx % 20 == 0 or batch_idx == total_batches:
            print(f"  Batch {batch_idx}/{total_batches} — {len(cached_urls)} URLs resolved")

        if i + batch_size < len(to_resolve):
            time.sleep(1.0 / RATE_LIMIT)

    return {f: cached_urls[f] for f in filenames if f in cached_urls}


def is_svg_content(content: bytes) -> bool:
    """Check if content is valid SVG by looking at the first few bytes."""
    start = content[:100].decode("utf-8", errors="ignore").strip().lower()
    return start.startswith("<svg") or start.startswith("<?xml")


def download_file(
    url: str,
    dest_path: Path,
    filename: str,
    timeout: int = 30
) -> tuple[bool, Optional[str]]:
    """
    Download a single file from URL to dest_path.
    Returns (success, error_message).
    """
    headers = {"User-Agent": USER_AGENT}

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            content = response.content

            if filename.lower().endswith(".svg"):
                if not is_svg_content(content):
                    return False, f"Invalid SVG content: {filename}"

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(content)

            return True, None

    except Exception as e:
        return False, str(e)
