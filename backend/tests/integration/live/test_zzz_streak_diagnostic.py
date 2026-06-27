"""
TEMPORARY diagnostic — calls POST /streaks/update, then immediately
queries the user_streaks table DIRECTLY via the service_role client
(bypassing the API/GET endpoint entirely) to see exactly what's in
the database. This tells us definitively whether the insert wrote
a row at all, and if so, what it actually contains.

Run:
    pytest tests/integration/live/test_zzz_streak_diagnostic.py -v -s

Delete after diagnosis.
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.integration
def test_diagnose_streak_insert(live_test_user, live_auth_headers, live_supabase):
    print("\n\n========== STREAK INSERT DIAGNOSTIC ==========")
    print("Test user id:", live_test_user["id"])

    response = client.post(
        "/api/v1/streaks/update", json={}, headers=live_auth_headers
    )
    print("POST /streaks/update status:", response.status_code)
    print("POST /streaks/update body:", response.json())

    # Query the table DIRECTLY with the admin client, bypassing the API
    direct_rows = (
        live_supabase.table("user_streaks")
        .select("*")
        .eq("user_id", live_test_user["id"])
        .execute()
    )
    print("\nDirect DB query for this user_id:")
    print("  row count:", len(direct_rows.data))
    print("  rows:", direct_rows.data)

    # Also try querying with NO filter at all, just to see table shape
    # (only first 3 rows, to avoid dumping huge output)
    sample_rows = live_supabase.table("user_streaks").select("*").limit(3).execute()
    print("\nSample of up to 3 rows in user_streaks table (any user):")
    print(" ", sample_rows.data)

    print("========== END DIAGNOSTIC ==========\n")