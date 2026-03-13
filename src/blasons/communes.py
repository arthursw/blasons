"""Commune data loading and manipulation."""

import polars as pl
from pathlib import Path
from typing import Optional, Dict, Any
from .config import CSV_PATH, normalize_commune_name

class Commune:
    """Represents a French commune with its metadata."""
    __slots__ = (
        "code_insee", "nom_standard", "nom_sans_accent", "nom_standard_majuscule",
        "reg_code", "reg_nom", "dep_code", "dep_nom", "code_postal", "url_wikipedia",
        "blason_filenames", "blason_source", "blason_verified", "blason_non_verifie", "wikidata_qid"
    )

    def __init__(
        self,
        code_insee: str,
        nom_standard: str,
        nom_sans_accent: str,
        nom_standard_majuscule: str,
        reg_code: str,
        reg_nom: str,
        dep_code: str,
        dep_nom: str,
        code_postal: str,
        url_wikipedia: str,
    ):
        self.code_insee = code_insee
        self.nom_standard = nom_standard
        self.nom_sans_accent = nom_sans_accent
        self.nom_standard_majuscule = nom_standard_majuscule
        self.reg_code = reg_code
        self.reg_nom = reg_nom
        self.dep_code = dep_code
        self.dep_nom = dep_nom
        self.code_postal = code_postal
        self.url_wikipedia = url_wikipedia
        # Additional fields for matching
        self.blason_filenames: list[str] = []
        self.blason_source: Optional[str] = None  # 'wikidata', 'petscan', 'commons'
        self.blason_verified: bool = False
        self.blason_non_verifie: bool = False  # Flag for low-confidence matches
        self.wikidata_qid: Optional[str] = None

    @property
    def normalized_name(self) -> str:
        """Normalized name for matching."""
        return normalize_commune_name(self.nom_sans_accent or self.nom_standard)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "code_insee": self.code_insee,
            "nom_standard": self.nom_standard,
            "nom_sans_accent": self.nom_sans_accent,
            "dep_code": self.dep_code,
            "dep_nom": self.dep_nom,
            "code_postal": self.code_postal,
            "blason_filenames": "|".join(self.blason_filenames),
            "blason_source": self.blason_source or "",
            "blason_verified": self.blason_verified,
            "blason_non_verifie": self.blason_non_verifie,
        }


def load_communes(csv_path: Optional[Path] = None) -> Dict[str, Commune]:
    """
    Load communes from CSV file into a dictionary indexed by code_insee.
    Returns dict of commune_code -> Commune object.
    """
    path = Path(csv_path) if csv_path else CSV_PATH

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    # Define required columns to read
    required_cols = [
        "code_insee", "nom_standard", "nom_sans_accent", "nom_standard_majuscule",
        "reg_code", "reg_nom", "dep_code", "dep_nom", "code_postal", "url_wikipedia",
    ]
    # Override dtypes to ensure proper string handling (preserve leading zeros)
    dtype_overrides = {
        "code_insee": pl.Utf8,
        "code_postal": pl.Utf8,
        "dep_code": pl.Utf8,
        "reg_code": pl.Utf8,
    }
    # Read only required columns to avoid parsing errors from other columns
    df = pl.read_csv(path, columns=required_cols, dtypes=dtype_overrides)



    # Validate required columns
    required_cols = {
        "code_insee", "nom_standard", "nom_sans_accent", "nom_standard_majuscule",
        "reg_code", "reg_nom", "dep_code", "dep_nom", "code_postal", "url_wikipedia"
    }
    available_cols = set(df.columns)
    missing = required_cols - available_cols
    if missing:
        raise ValueError(f"Missing required columns in CSV: {missing}")

    communes: Dict[str, Commune] = {}
    for row in df.iter_rows(named=True):
        commune = Commune(
            code_insee=row["code_insee"],
            nom_standard=row["nom_standard"],
            nom_sans_accent=row["nom_sans_accent"],
            nom_standard_majuscule=row["nom_standard_majuscule"],
            reg_code=row["reg_code"],
            reg_nom=row["reg_nom"],
            dep_code=row["dep_code"],
            dep_nom=row["dep_nom"],
            code_postal=row["code_postal"],
            url_wikipedia=row["url_wikipedia"],
        )
        communes[commune.code_insee] = commune

    return communes


def get_commune_by_insee(communes: Dict[str, Commune], code_insee: str) -> Optional[Commune]:
    """Lookup commune by INSEE code."""
    return communes.get(code_insee)


def get_communes_by_department(communes: Dict[str, Commune], dep_code: str) -> list[Commune]:
    """Get all communes in a department."""
    return [c for c in communes.values() if c.dep_code == dep_code]


def get_unmatched_communes(communes: Dict[str, Commune]) -> list[Commune]:
    """Get all communes that have not yet been matched to a blason."""
    return [c for c in communes.values() if c.blason_source is None]
