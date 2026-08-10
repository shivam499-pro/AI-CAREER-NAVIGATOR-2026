"""
Tests for services/linkedin_service.py -- parsing a user's official
LinkedIn "Download your data" export into a normalized dict.
"""
import io
import zipfile
import pytest

from services.linkedin_service import parse_linkedin_export, LinkedInParseError


def build_zip(files: dict[str, str]) -> bytes:
    """files: {member_name: text_content}"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


FULL_EXPORT_FILES = {
    "Profile.csv": (
        "\ufeff"
        "First Name,Last Name,Headline,Summary,Industry\n"
        "Fox,Example,Principal Engineer,\"Builds AI tools, loves testing\",Software Development\n"
    ),
    "Positions.csv": (
        "Company Name,Title,Description,Location,Started On,Finished On\n"
        "Career Navigator,Principal Engineer,\"Led backend work\",Remote,Jan 2024,\n"
        "PrevCo,Senior Developer,\"Built internal tools\",Remote,Jan 2020,Dec 2023\n"
    ),
    "Skills.csv": "Name\nPython\nFastAPI\nSystem Design\n",
    "Education.csv": (
        "School Name,Degree Name,Start Date,End Date\n"
        "MIT,B.S. Computer Science,2016,2020\n"
    ),
    "Languages.csv": "Name,Proficiency\nEnglish,Native or bilingual\n",
    "Certifications.csv": (
        "Name,Authority,Started On,Finished On,License Number,Url\n"
        "AWS Certified Developer,Amazon Web Services,Jan 2023,,ABC123,https://example.com/cert\n"
    ),
}


class TestHappyPath:
    def test_full_export_parses_every_section(self):
        result = parse_linkedin_export(build_zip(FULL_EXPORT_FILES))

        assert result["headline"] == "Principal Engineer"
        assert result["summary"] == "Builds AI tools, loves testing"
        assert result["industry"] == "Software Development"
        assert len(result["positions"]) == 2
        assert result["positions"][0]["title"] == "Principal Engineer"
        assert result["positions"][0]["company"] == "Career Navigator"
        assert result["skills"] == ["Python", "FastAPI", "System Design"]
        assert result["education"][0]["school"] == "MIT"
        assert result["languages"][0]["name"] == "English"
        assert result["certifications"][0]["name"] == "AWS Certified Developer"

    def test_utf8_bom_is_handled_cleanly(self):
        result = parse_linkedin_export(build_zip(FULL_EXPORT_FILES))
        # If the BOM leaked into the value, this would show up as a
        # stray character prefix on "Principal Engineer".
        assert result["headline"] == "Principal Engineer"

    def test_quoted_fields_with_embedded_commas_parse_correctly(self):
        result = parse_linkedin_export(build_zip(FULL_EXPORT_FILES))
        assert result["summary"] == "Builds AI tools, loves testing"
        assert result["positions"][0]["description"] == "Led backend work"


class TestPartialExports:
    def test_missing_files_degrade_to_empty_not_error(self):
        partial = {"Profile.csv": FULL_EXPORT_FILES["Profile.csv"]}
        result = parse_linkedin_export(build_zip(partial))

        assert result["headline"] == "Principal Engineer"
        assert result["positions"] == []
        assert result["skills"] == []
        assert result["education"] == []
        assert result["languages"] == []
        assert result["certifications"] == []

    def test_skills_only_export(self):
        partial = {"Skills.csv": FULL_EXPORT_FILES["Skills.csv"]}
        result = parse_linkedin_export(build_zip(partial))

        assert result["skills"] == ["Python", "FastAPI", "System Design"]
        assert result["headline"] == ""

    def test_blank_skill_rows_are_skipped(self):
        partial = {"Skills.csv": "Name\nPython\n\n   \nFastAPI\n"}
        result = parse_linkedin_export(build_zip(partial))
        assert result["skills"] == ["Python", "FastAPI"]

    def test_nested_subfolder_is_still_found(self):
        """LinkedIn sometimes wraps the export in a dated subfolder."""
        nested = {
            f"Basic_LinkedInDataExport_01-01-2026/{name}": content
            for name, content in FULL_EXPORT_FILES.items()
        }
        result = parse_linkedin_export(build_zip(nested))
        assert result["headline"] == "Principal Engineer"
        assert result["skills"] == ["Python", "FastAPI", "System Design"]

    def test_profile_csv_with_no_data_rows(self):
        partial = {"Profile.csv": "First Name,Last Name,Headline,Summary,Industry\n"}
        # No other recognizable data either -> should raise, since an
        # empty Profile.csv with nothing else present isn't a usable export
        with pytest.raises(LinkedInParseError):
            parse_linkedin_export(build_zip(partial))


class TestRejections:
    def test_not_a_zip_at_all(self):
        with pytest.raises(LinkedInParseError, match="valid ZIP"):
            parse_linkedin_export(b"definitely not a zip file")

    def test_empty_bytes(self):
        with pytest.raises(LinkedInParseError):
            parse_linkedin_export(b"")

    def test_valid_zip_but_no_recognizable_linkedin_files(self):
        unrelated = build_zip({"random.txt": "nothing to see here"})
        with pytest.raises(LinkedInParseError, match="No recognizable LinkedIn data"):
            parse_linkedin_export(unrelated)

    def test_oversized_file_rejected_before_unzipping(self):
        oversized = b"x" * (21 * 1024 * 1024)
        with pytest.raises(LinkedInParseError, match="too large"):
            parse_linkedin_export(oversized)

    def test_path_traversal_leading_slash_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zi = zipfile.ZipInfo("/etc/passwd")
            zf.writestr(zi, "malicious")
        with pytest.raises(LinkedInParseError, match="unsafe file paths"):
            parse_linkedin_export(buf.getvalue())

    def test_path_traversal_dotdot_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../../../etc/passwd", "malicious")
        with pytest.raises(LinkedInParseError, match="unsafe file paths"):
            parse_linkedin_export(buf.getvalue())

    def test_oversized_member_inside_valid_zip_rejected(self):
        buf = io.BytesIO()
        # ZIP_DEFLATED so the highly-repetitive payload compresses down
        # small enough to pass the outer file-size check, while its
        # *uncompressed* size (info.file_size) still exceeds the
        # per-member cap -- otherwise this test would just re-trip the
        # outer "file too large" guard instead of the member-size one.
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("Skills.csv", "Name\n" + ("A" * (21 * 1024 * 1024)))
        assert len(buf.getvalue()) < 20 * 1024 * 1024  # sanity: outer cap not the trigger
        with pytest.raises(LinkedInParseError, match="unexpectedly large"):
            parse_linkedin_export(buf.getvalue())

    def test_cumulative_uncompressed_size_across_members_rejected(self):
        # Distinct guard from the per-member cap above: six members each
        # individually UNDER the 20MB per-member limit, but summing to
        # over the 100MB total-uncompressed zip-bomb ceiling. Highly
        # repetitive content keeps the compressed archive itself well
        # under the outer 20MB file-size cap, so this test actually
        # exercises the cumulative-size branch and not either of the
        # other two size guards.
        buf = io.BytesIO()
        member_uncompressed_size = 18 * 1024 * 1024  # under MAX_MEMBER_SIZE_BYTES (20MB)
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for i in range(6):  # 6 x 18MB = 108MB > MAX_UNCOMPRESSED_SIZE_BYTES (100MB)
                zf.writestr(f"Skills{i}.csv", "Name\n" + ("A" * member_uncompressed_size))
        assert len(buf.getvalue()) < 20 * 1024 * 1024  # sanity: outer cap not the trigger
        with pytest.raises(LinkedInParseError, match="Uncompressed contents exceed"):
            parse_linkedin_export(buf.getvalue())