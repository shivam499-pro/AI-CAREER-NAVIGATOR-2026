"""
Shared fixtures for integration tests — CORRECTED VERSION.

KEY FIX: All routers import get_current_user from core.middleware,
NOT from lib.auth. The dependency_overrides must target the exact
function object imported in core.middleware.
"""
import os
import time
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from main import app

# ─── Test User Constants ────────────────────────────────────────────────────
TEST_USER_ID = "test-user-integration-001"
TEST_USER_EMAIL = "integration-test@careernav.test"
TEST_JWT_TOKEN = "test-integration-jwt-token"

# ─── Mock Supabase Response Builder ─────────────────────────────────────────
def make_supabase_response(data: list, count: int = None):
    mock = MagicMock()
    mock.data = data
    mock.count = count
    return mock

# ─── Auth Override — THE CRITICAL FIX ───────────────────────────────────────
@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {TEST_JWT_TOKEN}"}

@pytest.fixture
def mock_auth():
    """
    Override the REAL dependency used by routers: core.middleware.get_current_user
    This bypasses JWTVerifier entirely — no network calls, no Supabase auth API.
    """
    from core.middleware import get_current_user, AuthenticatedUser

    test_user = AuthenticatedUser(
        user_id=TEST_USER_ID,
        email=TEST_USER_EMAIL,
        role="user",
        permissions=[
            "read:profile", "write:profile",
            "read:analysis", "write:analysis",
            "read:interview", "write:interview",
            "read:resume", "write:resume",
            "read:documents", "write:documents",
            "read:jobs", "write:jobs",
        ],
    )

    app.dependency_overrides[get_current_user] = lambda: test_user
    yield test_user
    app.dependency_overrides.clear()

# ─── TestClient ──────────────────────────────────────────────────────────────
@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)

@pytest.fixture
def authed_client(client, mock_auth):
    """TestClient with auth dependency already bypassed."""
    return client

# ─── Supabase Mock ───────────────────────────────────────────────────────────
@pytest.fixture
def mock_supabase():
    """
    Patch the centralized Supabase client used by services/repositories.
    NOTE: routers/badges.py creates its OWN supabase client via create_client()
    at module level — that one needs a SEPARATE patch (see test_badges_contract.py).
    """
    from core.supabase_client import SupabaseClient
    SupabaseClient._instance = None  # reset singleton to ensure patching works

    with patch("core.supabase_client.SupabaseClient.get_client") as mock_get_client:
        supabase_mock = MagicMock()

        table_mock = MagicMock()
        table_mock.select.return_value = table_mock
        table_mock.insert.return_value = table_mock
        table_mock.update.return_value = table_mock
        table_mock.upsert.return_value = table_mock
        table_mock.delete.return_value = table_mock
        table_mock.eq.return_value = table_mock
        table_mock.single.return_value = table_mock
        table_mock.order.return_value = table_mock
        table_mock.limit.return_value = table_mock
        table_mock.execute.return_value = make_supabase_response([])

        supabase_mock.table.return_value = table_mock
        mock_get_client.return_value = supabase_mock

        yield supabase_mock

    SupabaseClient._instance = None  # reset singleton after test

# ─── Gemini Mock — CORRECTED CLASS NAME ─────────────────────────────────────
@pytest.fixture
def mock_gemini():
    """
    Patch AsyncGeminiTransport (NOT 'GeminiTransport' — that class doesn't exist).
    The real class is core.gemini_transport.AsyncGeminiTransport,
    instantiated via AsyncGeminiTransport.create().
    """
    with patch("core.gemini_transport.AsyncGeminiTransport.create") as mock_create:
        mock_transport = MagicMock()
        mock_transport.generate = MagicMock(return_value='{"result": "mocked"}')
        mock_create.return_value = mock_transport
        yield mock_transport

# ─── Standard Analysis Data ──────────────────────────────────────────────────
@pytest.fixture
def mock_analysis_record():
    return {
        "user_id": TEST_USER_ID,
        "career_paths": [
            {"name": "Full Stack Developer", "match_percentage": 85},
            {"name": "Backend Engineer", "match_percentage": 72},
        ],
        "skill_gaps": ["Docker", "Kubernetes", "System Design"],
        "experience_level": "Mid",
        "resume_score": {"overall": 78},
    }

# ─── Safety: register the 'integration' marker ──────────────────────────────
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require a real Supabase test project connection"
    )


# ─── Load .env.test once per session ─────────────────────────────────────────
@pytest.fixture(scope="session", autouse=False)
def _load_test_env():
    """
    Loads .env.test AND resets the already-constructed jwt_verifier
    singleton in core.middleware, since it reads SUPABASE_URL once at
    import time (before this fixture ever runs) and never again.
    """
    import os
    from dotenv import load_dotenv
    load_dotenv(".env.test", override=True)

    # Force the existing singleton to pick up the test project's values.
    from core.middleware import jwt_verifier
    jwt_verifier.supabase_url = os.getenv("SUPABASE_URL")
    jwt_verifier.supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    from core.supabase_client import SupabaseClient
    SupabaseClient._instance = None
    SupabaseClient.get_client()

# ─── Real Supabase client — SAFETY CHECKS ENFORCED ───────────────────────────
@pytest.fixture(scope="session")
def live_supabase(_load_test_env):
    """
    Real Supabase client for live integration tests.

    SAFETY: refuses to run unless the URL clearly points to a test project.
    This is intentional friction — it prevents a mistake from ever touching
    production data when running 'pytest -m integration'.
    """
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")

    if not url or not key:
        pytest.skip(
            "SUPABASE_URL / SUPABASE_SERVICE_KEY not set. "
            "Create backend/.env.test with your Supabase TEST project credentials."
        )

    PRODUCTION_URL = "https://bjweqlkhotjvmgocsdzw.supabase.co"
    if url.rstrip("/") == PRODUCTION_URL.rstrip("/"):
        pytest.fail(
            f"REFUSING TO RUN: SUPABASE_URL ('{url}') matches the PRODUCTION project. "
            "Live integration tests must NEVER run against production. "
            "Check that backend/.env.test (not .env) is being loaded."
        )

    os.environ["SUPABASE_URL"] = url
    os.environ["SUPABASE_SERVICE_KEY"] = key
    
    from core.supabase_client import SupabaseClient
    SupabaseClient._instance = None
    SupabaseClient.get_client()
    # tests/conftest.py does `supabase.create_client = mock_fn`, which only
    # overwrites the top-level re-export. The original function still lives
    # untouched in supabase.client -- that's what we use here.
    from supabase.client import create_client as _real_create_client
    return _real_create_client(url, key)


# ─── Test user factory — REAL Supabase Auth user + real session token ───────
@pytest.fixture
def live_test_user(live_supabase):
    """
    Creates a REAL user in Supabase Auth (not a fabricated JWT).

    WHY: core/middleware.py's get_current_user calls Supabase's
    /auth/v1/user endpoint to verify tokens — it has NO custom JWT
    fallback. A token signed by lib.auth.create_access_token will be
    REJECTED by the real middleware (confirmed during contract testing).
    The only way to get a token the middleware accepts is to create a
    real Supabase user and sign in as them.

    Cleans up the auth user AND all table rows after the test, pass or fail.
    """
    import uuid
    unique_email = f"integration-{uuid.uuid4().hex[:12]}@careernav-test.local"
    password = "Integration-Test-Pw-" + uuid.uuid4().hex[:8]

    # Create the real auth user via the admin API (service role required)
    created = live_supabase.auth.admin.create_user({
        "email": unique_email,
        "password": password,
        "email_confirm": True,  # skip email verification for test users
    })
    user_id = created.user.id

    # Seed initial profile row to satisfy foreign key relationships & profile queries
    try:
        live_supabase.table("profiles").upsert({
            "user_id": user_id,
            "career_goal": "Full Stack Developer",
            "extra_skills": ["Python", "React"],
        }).execute()
    except Exception as e:
        print(f"[live_test_user profile seed warning]: {e}")

    user = {
        "id": user_id,
        "email": unique_email,
        "password": password,
    }

    yield user

    # ── Cleanup: delete table rows first, then the auth user itself ─────────
    tables = [
        "profiles", "analyses", "interview_sessions", "user_streaks",
        "user_ranks", "user_badges", "user_career_memory", "user_documents",
        "saved_jobs", "job_applications", "challenge_attempts",
        "analysis_jobs",
    ]
    for table in tables:
        try:
            live_supabase.table(table).delete().eq("user_id", user_id).execute()
        except Exception as e:
            print(f"[cleanup warning] {table}: {e}")

    try:
        live_supabase.auth.admin.delete_user(user_id)
    except Exception as e:
        print(f"[cleanup warning] auth user {user_id}: {e}")


@pytest.fixture
def live_auth_headers(live_test_user):
    """
    Signs in as the real test user to get a genuine Supabase access_token.
 
    IMPORTANT: uses a SEPARATE client instance for sign-in, NOT the
    shared `live_supabase` admin client. Calling sign_in_with_password()
    on the admin client would overwrite its in-memory session state
    (supabase-py persists sessions by default), causing subsequent
    admin calls on that same client — like live_test_user's teardown
    calling auth.admin.delete_user() — to fail with 403 "User not
    allowed" because the client would then be acting as the regular
    test user instead of service_role.
    """
    import os
    from supabase.client import create_client as _real_create_client
 
    url = os.getenv("SUPABASE_URL")
    # Sign-in only needs a valid anon/public-facing key, not service_role.
    # Falling back to service_role here is fine too -- the POINT is using
    # a DIFFERENT client instance, not a different key.
    anon_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
 
    signin_client = _real_create_client(url, anon_key)
 
    session = signin_client.auth.sign_in_with_password({
        "email": live_test_user["email"],
        "password": live_test_user["password"],
    })
    token = session.session.access_token
    return {"Authorization": f"Bearer {token}"}
 