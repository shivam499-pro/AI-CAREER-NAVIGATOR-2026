"""
TEMPORARY diagnostic — calls the exact same insert that
routers/streaks.py performs, but THIS TIME we capture and print
whatever Supabase actually returns (or raises), instead of letting
the application code silently discard it.

Run:
    pytest tests/integration/live/test_zzz_insert_diagnostic.py -v -s

Delete after diagnosis.
"""
import pytest
from datetime import date


@pytest.mark.integration
def test_diagnose_raw_insert_response(live_test_user, live_supabase):
    print("\n\n========== RAW INSERT DIAGNOSTIC ==========")
    print("Test user id:", live_test_user["id"])

    today = date.today()

    try:
        result = live_supabase.table("user_streaks").insert({
            "user_id": live_test_user["id"],
            "current_streak": 1,
            "longest_streak": 1,
            "last_practice_date": today.isoformat(),
            "total_sessions": 1
        }).execute()

        print("\nInsert call completed WITHOUT raising an exception.")
        print("result.data:", result.data)
        print("result.count:", getattr(result, "count", "N/A"))
        print("Full result repr:", repr(result))

    except Exception as e:
        print("\nInsert call RAISED an exception:")
        print("Exception type:", type(e).__name__)
        print("Exception repr:", repr(e))
        for attr in ("message", "code", "details", "hint", "args"):
            if hasattr(e, attr):
                print(f"  .{attr} =", getattr(e, attr))

    # Now check directly whether a 'profiles' row exists for this user,
    # to test the foreign-key-dependency theory directly.
    profile_check = (
        live_supabase.table("profiles")
        .select("*")
        .eq("user_id", live_test_user["id"])
        .execute()
    )
    print("\nDoes a 'profiles' row exist for this user_id?")
    print("  row count:", len(profile_check.data))
    print("  rows:", profile_check.data)

    print("========== END DIAGNOSTIC ==========\n")