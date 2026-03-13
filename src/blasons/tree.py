"""Directory tree creation for blasons output."""

from pathlib import Path
from typing import Dict, Any
from .communes import Commune
from .config import format_region_name, format_department_name


def create_tree(communes: Dict[str, Commune], output_root: Path) -> None:
    """
    Create the output directory structure.
    Structure:
      {output_root}/
        {REGION_NAME}/
          {DEP_CODE}_{DEP_NAME}/
    """
    output_root.mkdir(parents=True, exist_ok=True)

    # Collect unique region/department pairs
    seen: set[tuple[str, str, str]] = set()  # (region_name, dep_code, dep_name)

    for commune in communes.values():
        key = (commune.reg_nom, commune.dep_code, commune.dep_nom)
        if key not in seen:
            seen.add(key)

    # Create directories
    for region_name, dep_code, dep_name in seen:
        region_dir = output_root / format_region_name(region_name)
        region_dir.mkdir(exist_ok=True)

        dept_dir = region_dir / f"{dep_code}_{format_department_name(dep_name)}"
        dept_dir.mkdir(exist_ok=True)

    print(f"Created directory structure with {len(seen)} department folders")


def create_region_department_folders(
    regions_data: list[Dict[str, Any]],
    departments_data: list[Dict[str, Any]],
    output_root: Path
) -> None:
    """
    Create folder structure from regions and departments lists (for blasons of regions/departments themselves).
    Also creates placeholders for region and department blason files.
    regions_data: list of {'label': str, ...}
    departments_data: list of {'dep_code': str, 'label': str, ...}
    """
    output_root.mkdir(parents=True, exist_ok=True)

    for region in regions_data:
        region_name = region["label"]
        region_dir = output_root / format_region_name(region_name)
        region_dir.mkdir(exist_ok=True)

        # Region blason file path would be: region_dir / f"_{normalize_for_path(region_name)}.svg"

    for dept in departments_data:
        dep_code = dept["dep_code"]
        dep_name = dept["label"]
        # Find the region for this department from the communes data?
        # This function may need to be called after we have a mapping.
        # For now, we can skip; actual commune tree will create needed folders.
        pass


if __name__ == "__main__":
    # Quick test: create from sample data
    from .communes import Commune, load_communes
    try:
        communes = load_communes()
        create_tree(communes, Path("blasons"))
    except FileNotFoundError as e:
        print(f"CSV not found: {e}")
