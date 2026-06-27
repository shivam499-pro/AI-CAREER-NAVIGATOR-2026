import fitz


def extract_text_from_pdf(
    pdf_bytes: bytes
) -> str:
    """
    Extract text from PDF document.
    """

    if not pdf_bytes:
        return ""

    text = ""

    try:
        document = fitz.open(
            stream=pdf_bytes,
            filetype="pdf"
        )

        for page in document:
            text += page.get_text()

        return text.strip()

    except Exception:
        return ""