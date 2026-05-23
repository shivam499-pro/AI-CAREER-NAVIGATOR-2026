import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import fitz
from core.supabase_client import supabase
from dotenv import load_dotenv

load_dotenv()

def extract_text_from_pdf(pdf_content: bytes) -> str:
    text = ""
    with fitz.open(stream=pdf_content, filetype="pdf") as doc:
        for page_num in range(len(doc)):
            page = doc[page_num]
            text += page.get_text()
    return text.strip()

def backfill():
    print("Fetching profiles with missing resume_text...")

    result = supabase.table("profiles") \
        .select("user_id, resume_url") \
        .is_("resume_text", "null") \
        .not_.is_("resume_url", "null") \
        .execute()

    profiles = result.data
    print(f"Found {len(profiles)} profiles to fix.")

    for profile in profiles:
        user_id = profile["user_id"]
        resume_url = profile["resume_url"]
        print(f"\nProcessing user: {user_id}")

        try:
            response = httpx.get(resume_url, timeout=30)
            response.raise_for_status()
            pdf_content = response.content
            print(f"  Downloaded PDF ({len(pdf_content)} bytes)")

            text = extract_text_from_pdf(pdf_content)

            if not text or len(text.strip()) == 0:
                print(f"  SKIP — PDF has no extractable text (scanned/image PDF)")
                continue

            print(f"  Extracted {len(text)} characters")

            supabase.table("profiles") \
                .update({"resume_text": text}) \
                .eq("user_id", user_id) \
                .execute()

            print(f"  FIXED — resume_text updated")

        except Exception as e:
            print(f"  ERROR — {str(e)}")

    print("\nBackfill complete.")

if __name__ == "__main__":
    backfill()