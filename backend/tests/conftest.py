"""
Pytest configuration and fixtures for backend tests.
Provides shared setup and mocks for external APIs.
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set environment variables for testing BEFORE any imports
# This ensures module-level supabase clients use the correct mock URLs
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_SERVICE_KEY"] = "test-service-key-that-is-long-enough-for-supabase"
os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["GITHUB_TOKEN"] = "test-github-token"
os.environ["SERPAPI_KEY"] = "test-serpapi-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-at-least-32-characters-long"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

# Patch supabase.create_client to return a mock that won't try to connect
from unittest.mock import MagicMock

def _get_mock_supabase_client(url=None, key=None):
    """Create a mock supabase client that won't make real HTTP calls."""
    mock_client = MagicMock()
    
    # Mock table() to return a mock query builder
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    mock_client.table.return_value = mock_table
    
    # Mock auth.get_user() for token validation
    mock_user = MagicMock()
    mock_user.user = None  # Return None to trigger JWT fallback
    mock_client.auth.get_user.return_value = mock_user
    
    return mock_client

# Patch at the supabase module level before any routers import it
import supabase
supabase.create_client = _get_mock_supabase_client


# =============================================================================
# Mock Supabase Client
# =============================================================================

class MockSupabaseResponse:
    """Mock Supabase response object."""
    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class MockSupabaseTable:
    """Mock Supabase table operations."""
    def __init__(self, return_data=None):
        self._return_data = return_data or []
        self._filters = {}
    
    def select(self, *columns):
        self._columns = columns
        return self
    
    def insert(self, data):
        return self
    
    def update(self, data):
        return self
    
    def delete(self):
        return self
    
    def eq(self, field, value):
        self._filters[field] = value
        return self
    
    def execute(self):
        # Filter data based on applied filters
        result = self._return_data
        for field, value in self._filters.items():
            result = [item for item in result if item.get(field) == value]
        return MockSupabaseResponse(data=result)
    
    def order(self, field, desc=False):
        return self
    
    def range(self, start, end):
        return self


class MockSupabaseStorage:
    """Mock Supabase Storage."""
    def __init__(self):
        self._files = {}
    
    def from_(self, bucket):
        return MockStorageBucket(bucket)


class MockStorageBucket:
    """Mock Supabase Storage bucket."""
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self._files = {}
    
    def upload(self, path, file, file_options=None):
        self._files[path] = file
    
    def get_public_url(self, path):
        return f"https://test.supabase.co/storage/v1/object/public/{self.bucket_name}/{path}"


class MockSupabaseClient:
    """Mock Supabase client."""
    def __init__(self):
        self.table = MockSupabaseTable
        self.storage = MockSupabaseStorage()
        self.auth = MockSupabaseAuth()
    
    def __getitem__(self, key):
        return self


class MockSupabaseAuth:
    """Mock Supabase auth."""
    def get_user(self, token):
        # Raise exception to simulate "not our JWT" so it falls back to custom JWT
        raise Exception("Invalid JWT")


class MockUser:
    def __init__(self, user):
        self.user = user


class MockUserObject:
    """Mock authenticated user."""
    def __init__(self):
        self.id = "test-user-id-123"
        self.email = "test@example.com"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_supabase():
    """Provide a mock Supabase client."""
    return MockSupabaseClient()


@pytest.fixture
def test_user():
    """Provide test user data."""
    return {
        "id": "test-user-id-123",
        "email": "test@example.com",
        "github_username": "testuser",
        "leetcode_username": "testuser"
    }


@pytest.fixture
def test_profile():
    """Provide test profile data."""
    return {
        "user_id": "test-user-id-123",
        "email": "test@example.com",
        "github_username": "testuser",
        "leetcode_username": "testuser",
        "user_type": "student",
        "college_name": "Test University",
        "degree": "Computer Science",
        "branch": "CS",
        "graduation_year": 2025,
        "career_goal": "Full Stack Developer",
        "extra_skills": ["Python", "JavaScript"],
        "certifications": [],
    }


@pytest.fixture
def mock_github_data():
    """Provide mock GitHub data."""
    return {
        "profile": {
            "username": "testuser",
            "name": "Test User",
            "bio": "Test bio",
            "followers": 100,
            "following": 50,
            "public_repos": 30,
        },
        "top_repos": [
            {"name": "repo1", "stars": 50, "language": "Python"},
            {"name": "repo2", "stars": 30, "language": "JavaScript"},
        ],
        "language_stats": {"Python": 10, "JavaScript": 5},
        "contribution_stats": {"public_repos": 30, "followers": 100, "following": 50},
    }


@pytest.fixture
def mock_leetcode_data():
    """Provide mock LeetCode data."""
    return {
        "profile": {
            "username": "testuser",
            "real_name": "Test User",
            "total_submissions": 500,
        },
        "problems_solved": {"total": 200, "easy": 80, "medium": 100, "hard": 20},
        "contest_rating": {"rating": 1800, "top_percentage": 10, "contests_attended": 20},
        "recent_submissions": [],
    }


@pytest.fixture
def mock_gemini_response():
    """Provide mock Gemini AI response."""
    return {
        "success": True,
        "data": {
            "analysis": {
                "experience_level": "Intermediate",
                "experience_reason": "Strong foundation in Python and React",
                "strengths": ["Python", "React", "REST API"],
                "weaknesses": ["System Design", "Kubernetes"]
            },
            "career_paths": [
                {"name": "Full Stack Engineer", "match_percentage": 92, "reason": "Great fit"},
                {"name": "Backend Developer", "match_percentage": 85, "reason": "Good fit"},
            ],
            "skill_gaps": [
                {"skill": "Redis", "have": False, "priority": 1, "resources": ["Redis docs"]},
            ],
            "roadmap": {
                "target_career": "Full Stack Engineer",
                "duration_months": 6,
                "milestones": [
                    {"week": 1, "title": "Master FastAPI", "description": "Learn async", "skills": ["FastAPI"]},
                ]
            }
        }
    }


@pytest.fixture
def valid_pdf_content():
    """Provide valid PDF file content with magic bytes."""
    # Minimal valid PDF (magic bytes %PDF + basic structure)
    return b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"


@pytest.fixture
def invalid_pdf_content():
    """Provide invalid file content (not a real PDF)."""
    return b"This is not a PDF file content"


@pytest.fixture
def valid_image_jpeg():
    """Provide valid JPEG magic bytes."""
    return b"\xff\xd8\xff\xe0\x00\x10JFIF"


@pytest.fixture
def valid_image_png():
    """Provide valid PNG magic bytes."""
    return b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def sample_resume_text():
    """Provide sample resume text."""
    return """
    John Doe
    Email: john@example.com
    Phone: (555) 123-4567
    
    Education:
    - B.S. Computer Science, Test University, 2025
    
    Skills:
    - Python, JavaScript, React, Node.js, SQL
    
    Experience:
    - Software Developer Intern at Tech Corp (2023-2024)
    """


# =============================================================================
# Mock External Services
# =============================================================================

@pytest.fixture
def mock_github_service(monkeypatch):
    """Mock GitHub service to avoid real API calls."""
    async def mock_get_full_github_data(username):
        return {
            "profile": {"username": username, "name": "Test User"},
            "top_repos": [],
            "language_stats": {},
            "contribution_stats": {}
        }
    
    monkeypatch.setattr("services.github_service.get_full_github_data", mock_get_full_github_data)


@pytest.fixture
def mock_leetcode_service(monkeypatch):
    """Mock LeetCode service to avoid real API calls."""
    async def mock_get_full_leetcode_data(username):
        return {
            "profile": {"username": username},
            "problems_solved": {"total": 0, "easy": 0, "medium": 0, "hard": 0},
            "contest_rating": {},
            "recent_submissions": []
        }
    
    monkeypatch.setattr("services.leetcode_service.get_full_leetcode_data", mock_get_full_leetcode_data)


@pytest.fixture
def mock_gemini_service(monkeypatch, mock_gemini_response):
    """Mock Gemini service to avoid real API calls."""
    def mock_run_combined_analysis(github_data, leetcode_data, resume_text, user_profile):
        return mock_gemini_response
    
    monkeypatch.setattr("services.gemini_service.run_combined_analysis", mock_run_combined_analysis)
    
    def mock_sanitize(text, max_length=5000):
        return text
    
    monkeypatch.setattr("services.gemini_service.sanitize_user_input", mock_sanitize)


@pytest.fixture
def mock_gemini_rate_limit(monkeypatch):
    """Mock Gemini service to simulate rate limit error."""
    def mock_run_combined_analysis(github_data, leetcode_data, resume_text, user_profile):
        return {
            "success": False,
            "error": "Rate limit exceeded",
            "error_type": "rate_limit"
        }
    
    monkeypatch.setattr("services.gemini_service.run_combined_analysis", mock_run_combined_analysis)


@pytest.fixture
def auth_headers():
    """Provide valid authorization headers."""
    from lib.auth import create_access_token
    token = create_access_token("test-user-123", "test@example.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def expired_auth_headers():
    """Provide expired authorization headers."""
    return {"Authorization": "Bearer expired-token"}


# =============================================================================
# Test Client
# =============================================================================

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    
    # Patch the Supabase client before importing
    with patch('supabase.create_client') as mock_create:
        mock_create.return_value = MockSupabaseClient()
        
        # Import and create app
        from main import app
        return TestClient(app)