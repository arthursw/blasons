"""Filename generation and path construction for blasons."""

from pathlib import Path
from typing import Optional
from .communes import Commune
from .config import format_region_name, format_department_name


def normalize_for_path(s: str) -> str:
    """Normalize string for filesystem path: uppercase, spaces/hyphens to underscore."""
    return s.upper().replace(" ", "_").replace("-", "_")


def get_region_dir(region_name: str) -> str:
    """Get the region directory name."""
    return format_region_name(region_name)


def get_department_dir(dep_code: str, dep_name: str) -> str:
    """Get the department directory name: {DEP_CODE}_{DEP_NAME_NORMALIZED}."""
    dep_norm = format_department_name(dep_name)
    return f"{dep_code}_{dep_norm}"


def generate_region_filename(region_name: str, output_root: Path) -> Path:
    """
    Generate path for region blason.
    Example: blasons/AUVERGNE_RHONE_ALPES/_AUVERGNE_RHONE_ALPES.svg
    """
    region_dir = get_region_dir(region_name)
    filename = f"_{normalize_for_path(region_name)}.svg"
    return output_root / region_dir / filename


def generate_department_filename(dep_code: str, dep_name: str, output_root: Path) -> Path:
    """
    Generate path for department blason.
    Example: blasons/AUVERGNE_RHONE_ALPES/01_AIN/_AIN.svg
    """
    region_dir = None  # Need commune context; will be filled by caller
    dept_dir = get_department_dir(dep_code, dep_name)
    filename = f"_{normalize_for_path(dep_name)}.svg"
    # We return a partial path; the caller must prepend region dir
    # Instead, we return relative path from output root: region_dir / dept_dir / filename
    # So we'll provide both region and dept names.
    # Actually: generate_xxx returns Path object relative to output_root.
    # Let's design: generate_xxx(..., region_name) returns full path.
    # We'll overload generate_department_filename to take region_name as well.
    pass  # We'll restructure in final __main__, but provide helper:

def generate_commune_filename(
    commune: Commune,
    original_filename: str,
    index: int,
    non_verifie: bool = False,
    is_raster: bool = False,
    raster_ext: Optional[str] = None,
    output_root: Path = Path("blasons")
) -> Path:
    """
    Generate the STKBL filename and full path for a commune blason.

    Args:
        commune: Commune object
        original_filename: Original filename from source
        index: Sequential number for this commune (starting at 1)
        non_verifie: If True, add _NON_VERIFIE marker
        is_raster: If True, generate raster filename with suffix
        raster_ext: Extension for raster (e.g., 'png', 'jpg')
        output_root: Base output directory

    Returns:
        Full Path object for the file.
    """
    dep_code = commune.dep_code
    code_postal = commune.code_postal or "00000"
    # Normalize nom_sans_accent (or nom_standard) to uppercase with underscores
    nom_raw = commune.nom_sans_accent or commune.nom_standard
    nom_norm = normalize_for_path(nom_raw)

    # Base filename without extension
    base = f"STKBL{dep_code}_{code_postal}_{nom_norm}_{index:02d}"

    # Add markers
    if non_verifie:
        base += "_NON_VERIFIE"

    # Determine extension
    if is_raster and raster_ext:
        ext = raster_ext.lower()
        base += f"_{raster_ext.upper()}"
        filename = f"{base}.{ext}"
    else:
        filename = f"{base}.svg"

    # Build directory tree
    region_dir = get_region_dir(commune.reg_nom)
    dept_dir = get_department_dir(commune.dep_code, commune.dep_nom)

    return output_root / region_dir / dept_dir / filename


# Convenience functions for region and department with full path
def generate_region_path(region_name: str, output_root: Path) -> Path:
    region_dir = get_region_dir(region_name)
    filename = f"_{normalize_for_path(region_name)}.svg"
    return output_root / region_dir / filename


def generate_department_path(dep_code: str, dep_name: str, region_name: str, output_root: Path) -> Path:
    region_dir = get_region_dir(region_name)
    dept_dir = get_department_dir(dep_code, dep_name)
    filename = f"_{normalize_for_path(dep_name)}.svg"
    return output_root / region_dir / dept_dir / filename


if __name__ == "__main__":
    # Quick test
    from .communes import Commune
    c = Commune(
        code_insee="01001",
        nom_standard="L'Abergement-Clémenciat",
        nom_sans_accent="L'Abergement-Clémenciat",
        nom_standard_majuscule="L'ABERGEMENT-CLEMENCIAT",
        reg_code="84",
        reg_nom="Auvergne-Rhône-Alpes",
        dep_code="01",
        dep_nom="Ain",
        code_postal="01400",
        url_wikipedia="https://fr.wikipedia.org/wiki/L%27Abergement-Cl%C3%A9menciat",
    )
    path = generate_commune_filename(c, "Blason ville fr L'Abergement-Clémenciat.svg", 1, non_verifie=False, output_root=Path("blasons"))
    print(path)
