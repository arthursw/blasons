"""Matching logic for discovered blasons to communes."""

from rapidfuzz import fuzz
from typing import Optional, Any, Dict
from .communes import Commune
from .config import FUZZY_THRESHOLD, FOREIGN_KEYWORDS


def normalize_match_string(s: str) -> str:
    """Normalize a string for matching: lowercase, strip accents already done, remove extra spaces."""
    return s.lower().strip()


def exact_match_by_insee(
    communes: Dict[str, Commune],
    wikidata_results: list[Dict[str, Any]]
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    """
    Match Wikidata commune results to communes by code_insee (exact match).
    Returns (matched, unmatched) lists of wikidata result dicts.
    """
    matched = []
    unmatched = []

    for wd in wikidata_results:
        code_insee = wd.get("code_insee")
        if code_insee and code_insee in communes:
            matched.append(wd)
        else:
            unmatched.append(wd)

    return matched, unmatched


def apply_wikidata_match(
    communes: Dict[str, Commune],
    wikidata_results: list[Dict[str, Any]]
) -> None:
    """
    Apply Wikidata matches to the communes dict in-place.
    Assumes the wikidata_results are already matched (e.g., via exact_match_by_insee).
    """
    for wd in wikidata_results:
        code_insee = wd.get("code_insee")
        if not code_insee:
            continue
        commune = communes.get(code_insee)
        if commune:
            commune.blason_source = "wikidata"
            commune.blason_verified = True
            # Store the full filename (could be used later to download)
            if wd.get("image"):
                commune.blason_filenames.append(wd["image"])


def fuzzy_match_filename(
    filename: str,
    commune: Commune,
    threshold: int = FUZZY_THRESHOLD
) -> tuple[bool, int]:
    """
    Try to match a filename (extracted commune name) to a commune using fuzzy matching.
    Returns (is_match, score).
    """
    # Use both nom_sans_accent and nom_standard
    target_names = [commune.nom_sans_accent, commune.nom_standard, commune.nom_standard_majuscule]
    target_names = [n for n in target_names if n]

    candidate = normalize_match_string(filename)

    best_score = 0
    for target in target_names:
        norm_target = normalize_match_string(target)
        # Use ratio for exact string similarity
        score = fuzz.ratio(candidate, norm_target)
        if score > best_score:
            best_score = score

    return best_score >= threshold, best_score


def match_petscan_filenames(
    communes: Dict[str, Commune],
    filenames: list[str],
    unmatched_communes: Optional[list[Commune]] = None,
    threshold: int = FUZZY_THRESHOLD
) -> tuple[list[tuple[str, str, int]], list[str]]:
    """
    Match PetScan filenames to communes via fuzzy matching.
    If unmatched_communes is provided, only match against that subset.
    Returns (matches, unmatched_filenames) where matches is list of (filename, code_insee, score).
    """
    if unmatched_communes is None:
        unmatched_communes = list(communes.values())

    matches: list[tuple[str, str, int]] = []
    unmatched_filenames: list[str] = []

    for filename in filenames:
        candidate_name = filename
        best_match: Optional[Commune] = None
        best_score = 0

        for commune in unmatched_communes:
            is_match, score = fuzzy_match_filename(candidate_name, commune, threshold=0)  # get raw score
            if score > best_score:
                best_score = score
                best_match = commune

        if best_match and best_score >= threshold:
            matches.append((filename, best_match.code_insee, best_score))
            best_match.blason_filenames.append(filename)
            best_match.blason_source = "petscan"
            best_match.blason_verified = True
            # Flag as non-verifie if score < 100 or foreign keyword present
            if best_score < 100 or any(keyword in filename.lower() for keyword in FOREIGN_KEYWORDS):
                best_match.blason_non_verifie = True
        else:
            unmatched_filenames.append(filename)


    return matches, unmatched_filenames


def flag_non_verifie(communes: Dict[str, Commune]) -> None:
    """
    Mark communes as non-verified based on various criteria:
    - Foreign keywords in filename
    - Low fuzzy match score (already set during fuzzy_match_filename)
    - Multiple candidates (ambiguous)
    - Historical entity (hard to detect, will be manual review)
    """
    for commune in communes.values():
        # Already flagged during fuzzy match if score < 100
        pass  # This can be extended later


if __name__ == "__main__":
    # Quick test
    from rapidfuzz import fuzz
    test_cases = [
        ("Blason ville fr Paris", "Paris", 100),
        ("Blason de Lyon", "Lyon", 100),
        ("Blason ville fr L'Abergement-Clémenciat", "L'Abergement-Clémenciat", 100),
        ("Blason Marseille", "Marseille", 100),
        ("Coats of arms of communes of Ain", "Ain", None),  # should be skipped
    ]

    for filename, target, expected in test_cases:
        # Simple test
        score = fuzz.ratio(filename.lower(), target.lower())
        print(f"{filename} vs {target}: {score}")
