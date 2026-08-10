"""
LinkedIn Service
Parses a user's own official LinkedIn data export (Settings & Privacy ->
Data Privacy -> Get a copy of your data) into a normalized dict shape
that sits alongside github_data/leetcode_data in the analysis pipeline.

Deliberately NOT a DataProvider (services/data_providers.py).
DataProvider.fetch_data(username) live-fetches from an external API on
demand. This is the opposite: the user already has the file in hand,
uploaded once, and no network call to linkedin.com happens here or
anywhere in this module. That's the whole point -- it's how LinkedIn
data gets in without hitting the API restrictions or ToS's scraping
prohibition. See conversation history / design notes for why this
approach was chosen over OAuth (thin data: name/headline/photo only)
or scraping (explicit ToS violation).
"""
import csv
import io
import logging
import zipfile
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Safety limits -- LinkedIn exports are plain text CSVs, so these are
# generous ceilings, not tight budgets. Anything beyond this is either
# not a real LinkedIn export or a deliberately malicious upload.
MAX_ZIP_SIZE_BYTES = 20 * 1024 * 1024              # 20MB compressed
MAX_UNCOMPRESSED_SIZE_BYTES = 100 * 1024 * 1024    # 100MB uncompressed (zip-bomb guard)
MAX_MEMBER_SIZE_BYTES = 20 * 1024 * 1024           # no single CSV should be this big

# LinkedIn's own export uses these filenames. Matched case-insensitively
# and by suffix (see _find_member) since LinkedIn sometimes nests files
# in a dated subfolder inside the zip.
KNOWN_FILES = {
    "profile": "Profile.csv",
    "positions": "Positions.csv",
    "skills": "Skills.csv",
    "education": "Education.csv",
    "languages": "Languages.csv",
    "certifications": "Certifications.csv",
}


class LinkedInParseError(Exception):
    """Raised when the uploaded file isn't a usable LinkedIn export."""
    pass


def _safe_open_zip(file_content: bytes) -> zipfile.ZipFile:
    """
    Open a zip after validating size and structure up front, guarding
    against zip bombs (uncompressed-size cap) and zip-slip path
    traversal (reject any member path that isn't a plain relative
    filename).
    """
    if len(file_content) > MAX_ZIP_SIZE_BYTES:
        raise LinkedInParseError(
            f"File too large ({len(file_content)} bytes). LinkedIn exports "
            f"are text-only and should be well under {MAX_ZIP_SIZE_BYTES} bytes."
        )

    try:
        zf = zipfile.ZipFile(io.BytesIO(file_content))
    except zipfile.BadZipFile:
        raise LinkedInParseError("This doesn't look like a valid ZIP file.")

    total_uncompressed = 0
    for info in zf.infolist():
        if info.filename.startswith("/") or ".." in info.filename.split("/"):
            raise LinkedInParseError("Zip contains unsafe file paths.")
        if info.file_size > MAX_MEMBER_SIZE_BYTES:
            raise LinkedInParseError(f"'{info.filename}' is unexpectedly large.")
        total_uncompressed += info.file_size

    if total_uncompressed > MAX_UNCOMPRESSED_SIZE_BYTES:
        raise LinkedInParseError("Uncompressed contents exceed the safety limit.")

    return zf


def _find_member(zf: zipfile.ZipFile, target_filename: str) -> Optional[str]:
    """Find a member matching target_filename, case-insensitively, at
    any depth in the archive."""
    target_lower = target_filename.lower()
    for name in zf.namelist():
        if name.lower().endswith(target_lower):
            return name
    return None


def _read_csv_rows(zf: zipfile.ZipFile, member_name: str) -> list[dict]:
    """Read a CSV member into a list of dicts, tolerating LinkedIn's
    common UTF-8-with-BOM encoding."""
    raw = zf.read(member_name)
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def parse_linkedin_export(file_content: bytes) -> dict[str, Any]:
    """
    Parse a LinkedIn "Download your data" archive into a normalized dict:

    {
        "headline": str,
        "summary": str,
        "industry": str,
        "positions": [{"title", "company", "started_on", "finished_on", "description"}, ...],
        "skills": [str, ...],
        "education": [{"school", "degree_name", "start_date", "end_date"}, ...],
        "languages": [{"name", "proficiency"}, ...],
        "certifications": [{"name", "authority", "url"}, ...],
    }

    LinkedIn lets a member export specific categories only, so a missing
    file is normal, not an error -- it just means that section comes
    back empty. This only raises when the zip itself is unusable, or
    when literally none of the recognized files are present at all
    (i.e. this clearly isn't a LinkedIn export).
    """
    zf = _safe_open_zip(file_content)

    result: dict[str, Any] = {
        "headline": "",
        "summary": "",
        "industry": "",
        "positions": [],
        "skills": [],
        "education": [],
        "languages": [],
        "certifications": [],
    }

    profile_member = _find_member(zf, KNOWN_FILES["profile"])
    if profile_member:
        rows = _read_csv_rows(zf, profile_member)
        if rows:
            row = rows[0]
            result["headline"] = row.get("Headline", "") or ""
            result["summary"] = row.get("Summary", "") or ""
            result["industry"] = row.get("Industry", "") or ""

    positions_member = _find_member(zf, KNOWN_FILES["positions"])
    if positions_member:
        for row in _read_csv_rows(zf, positions_member):
            result["positions"].append({
                "title": row.get("Title", ""),
                "company": row.get("Company Name", ""),
                "started_on": row.get("Started On", ""),
                "finished_on": row.get("Finished On", ""),
                "description": row.get("Description", ""),
            })

    skills_member = _find_member(zf, KNOWN_FILES["skills"])
    if skills_member:
        for row in _read_csv_rows(zf, skills_member):
            name = (row.get("Name") or "").strip()
            if name:
                result["skills"].append(name)

    education_member = _find_member(zf, KNOWN_FILES["education"])
    if education_member:
        for row in _read_csv_rows(zf, education_member):
            result["education"].append({
                "school": row.get("School Name", ""),
                "degree_name": row.get("Degree Name", ""),
                "start_date": row.get("Start Date", ""),
                "end_date": row.get("End Date", ""),
            })

    languages_member = _find_member(zf, KNOWN_FILES["languages"])
    if languages_member:
        for row in _read_csv_rows(zf, languages_member):
            result["languages"].append({
                "name": row.get("Name", ""),
                "proficiency": row.get("Proficiency", ""),
            })

    certifications_member = _find_member(zf, KNOWN_FILES["certifications"])
    if certifications_member:
        for row in _read_csv_rows(zf, certifications_member):
            result["certifications"].append({
                "name": row.get("Name", ""),
                "authority": row.get("Authority", ""),
                "url": row.get("Url", ""),
            })

    found_anything = any([
        result["headline"], result["positions"], result["skills"],
        result["education"], result["languages"], result["certifications"],
    ])
    if not found_anything:
        raise LinkedInParseError(
            "No recognizable LinkedIn data found in this archive. Make sure "
            "you uploaded the full 'Download your data' ZIP from LinkedIn."
        )

    return result