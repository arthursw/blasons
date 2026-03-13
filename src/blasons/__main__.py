"""Main CLI for blasons downloader."""

import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tqdm import tqdm

from . import config
from .communes import (
    load_communes,
    get_unmatched_communes,
    Commune,
)
from .wikidata import fetch_communes, fetch_regions, fetch_departments
from .matcher import (
    exact_match_by_insee,
    apply_wikidata_match,
    match_petscan_filenames,
)
from .petscan import query_petscan, is_foreign_keyword
from .downloader import batch_resolve_urls, download_file
from .namer import (
    generate_commune_filename,
    generate_region_path,
    generate_department_path,
)
from .tree import create_tree


def build_download_tasks(
    communes: dict[str, Commune],
    regions_data: list[dict],
    departments_data: list[dict],
    filename_to_url: dict[str, str],
    output_root: Path,
) -> list[dict[str, Any]]:
    """
    Construct a list of download tasks (dicts) for all blasons:
    commune blasons, region blasons, department blasons.
    """
    tasks = []

    # Build dep_code -> (dep_name, reg_name) mapping from communes
    dep_to_region: dict[str, tuple[str, str]] = {}
    for c in communes.values():
        if c.dep_code not in dep_to_region:
            dep_to_region[c.dep_code] = (c.dep_nom, c.reg_nom)

    # Region tasks
    for region in regions_data:
        filename = region["image"]
        if filename not in filename_to_url:
            continue
        url = filename_to_url[filename]
        dest_path = generate_region_path(region["label"], output_root)
        tasks.append({
            "type": "region",
            "filename": filename,
            "url": url,
            "commune": None,
            "index": None,
            "non_verifie": False,
            "is_raster": not filename.lower().endswith(".svg"),
            "dest_path": dest_path,
            "name": region["label"],
        })

    # Department tasks
    for dept in departments_data:
        filename = dept["image"]
        if filename not in filename_to_url:
            continue
        url = filename_to_url[filename]
        dep_code = dept["dep_code"]
        dep_name = dept["label"]
        region_info = dep_to_region.get(dep_code)
        if region_info:
            _, reg_name = region_info
        else:
            print(f"Warning: department {dep_code} not mapped to any region, skipping blason")
            continue
        dest_path = generate_department_path(dep_code, dep_name, reg_name, output_root)
        tasks.append({
            "type": "department",
            "filename": filename,
            "url": url,
            "commune": None,
            "index": None,
            "non_verifie": False,
            "is_raster": not filename.lower().endswith(".svg"),
            "dest_path": dest_path,
            "name": dept["label"],
        })

    # Commune tasks
    for code_insee, commune in communes.items():
        if not commune.blason_filenames:
            continue
        # Deduplicate filenames but preserve order
        seen = set()
        unique_filenames = []
        for fname in commune.blason_filenames:
            if fname not in seen:
                seen.add(fname)
                unique_filenames.append(fname)

        for idx, filename in enumerate(unique_filenames, 1):
            if filename not in filename_to_url:
                continue
            url = filename_to_url[filename]
            is_raster = not filename.lower().endswith(".svg")
            ext = filename.lower().split(".")[-1] if "." in filename else "svg"
            non_verifie = commune.blason_non_verifie or is_foreign_keyword(filename)

            dest_path = generate_commune_filename(
                commune,
                filename,
                idx,
                non_verifie=non_verifie,
                is_raster=is_raster,
                raster_ext=ext if is_raster else None,
                output_root=output_root,
            )
            tasks.append({
                "type": "commune",
                "filename": filename,
                "url": url,
                "commune": commune,
                "index": idx,
                "non_verifie": non_verifie,
                "is_raster": is_raster,
                "dest_path": dest_path,
            })

    return tasks


def write_log(logfile: Path, entries: list[dict[str, Any]]) -> None:
    """Write a CSV log."""
    if not entries:
        headers = ["code_insee", "commune", "source", "commons_filename", "local_filename", "status", "error", "timestamp"]
        with open(logfile, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
        return

    with open(logfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=entries[0].keys())
        writer.writeheader()
        for entry in entries:
            writer.writerow(entry)


def main():
    parser = argparse.ArgumentParser(description="Download French communes' blasons.")
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    parser.add_argument("--refresh", action="store_true", help="Re-fetch Wikidata/PetScan/Commons data (ignore cache)")
    parser.add_argument("--limit", type=int, help="Limit number of communes to process (testing)")
    args = parser.parse_args()

    output_root = Path(config.OUTPUT_ROOT)
    data_dir = Path(config.DATA_DIR)

    print("Loading communes from CSV...")
    all_communes = load_communes()
    if args.limit:
        all_communes = dict(list(all_communes.items())[:args.limit])
    print(f"Loaded {len(all_communes)} communes")

    print("Creating directory tree...")
    create_tree(all_communes, output_root)

    # Phase 1: Wikidata
    print("\n=== Phase 1: Wikidata ===")
    print("Fetching communes from Wikidata...")
    wd_communes = fetch_communes(refresh=args.refresh)
    matched_wd, unmatched_wd = exact_match_by_insee(all_communes, wd_communes)
    apply_wikidata_match(all_communes, matched_wd)
    print(f"Matched {len(matched_wd)} communes via Wikidata")

    regions_data = fetch_regions(refresh=args.refresh)
    departments_data = fetch_departments(refresh=args.refresh)
    print(f"Fetched {len(regions_data)} regions and {len(departments_data)} departments from Wikidata")

    # Phase 2: PetScan for unmatched communes
    print("\n=== Phase 2: PetScan ===")
    unmatched_communes = get_unmatched_communes(all_communes)
    print(f"{len(unmatched_communes)} communes need further matching")

    all_petscan_files = query_petscan(refresh=args.refresh)
    print(f"Total files from PetScan: {len(all_petscan_files)}")

    petscan_matches, remaining_files = match_petscan_filenames(
        all_communes, all_petscan_files, unmatched_communes
    )
    print(f"PetScan fuzzy matching found {len(petscan_matches)} matches")

    # Prepare downloads
    print("\n=== Preparing downloads ===")
    region_filenames = [r["image"] for r in regions_data]
    dept_filenames = [d["image"] for d in departments_data]
    commune_filenames = []
    for c in all_communes.values():
        if c.blason_filenames:
            commune_filenames.extend(c.blason_filenames)

    all_filenames = list(set(region_filenames + dept_filenames + commune_filenames))
    print(f"Total unique files to download: {len(all_filenames)}")

    print("Resolving download URLs...")
    filename_to_url = batch_resolve_urls(all_filenames, refresh=args.refresh)

    tasks = build_download_tasks(all_communes, regions_data, departments_data, filename_to_url, output_root)
    print(f"Built {len(tasks)} download tasks")

    # Download with rate limiting
    print("\n=== Downloading files ===")
    download_entries = []
    skipped = 0
    errors = 0
    downloaded = 0

    for task in tqdm(tasks, desc="Downloading", unit="file"):
        dest = task["dest_path"]
        if dest.exists() and not args.force:
            status = "skipped"
            error = ""
            skipped += 1
        else:
            success, error = download_file(task["url"], dest, task["filename"])
            status = "ok" if success else "error"
            if success:
                downloaded += 1
            else:
                errors += 1
            time.sleep(1.0 / config.RATE_LIMIT)

        entry = {
            "code_insee": task["commune"].code_insee if task.get("commune") else "",
            "commune": task["commune"].nom_standard if task.get("commune") else task.get("name", ""),
            "source": task["commune"].blason_source if task.get("commune") else "wikidata",
            "commons_filename": task["filename"],
            "local_filename": str(dest.relative_to(output_root)),
            "status": status,
            "error": error or "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        download_entries.append(entry)

    print(f"\nDownloaded: {downloaded}, Skipped: {skipped}, Errors: {errors}")

    # Write logs
    print("Writing logs...")
    write_log(data_dir / "download_log.csv", download_entries)

    # Generate communes sans blason report
    missing = [c for c in all_communes.values() if not c.blason_filenames]
    missing_data = []
    for c in missing:
        missing_data.append({
            "code_insee": c.code_insee,
            "nom_standard": c.nom_standard,
            "nom_sans_accent": c.nom_sans_accent,
            "dep_code": c.dep_code,
            "dep_nom": c.dep_nom,
            "reg_nom": c.reg_nom,
            "url_wikipedia": c.url_wikipedia,
        })
    write_log(data_dir / "communes_sans_blason.csv", missing_data)
    print(f"Report: {len(missing)} communes without blasons")

    raster_tasks = [t for t in tasks if t["is_raster"]]
    if raster_tasks:
        raster_data = []
        for t in raster_tasks:
            raster_data.append({
                "code_insee": t["commune"].code_insee if t.get("commune") else "",
                "commune": t["commune"].nom_standard if t.get("commune") else "",
                "commons_filename": t["filename"],
                "local_filename": str(t["dest_path"].relative_to(output_root)),
            })
        write_log(data_dir / "raster_blasons.csv", raster_data)
        print(f"Raster blasons: {len(raster_tasks)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
