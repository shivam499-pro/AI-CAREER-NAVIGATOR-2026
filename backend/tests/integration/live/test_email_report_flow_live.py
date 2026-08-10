"""
Live tests for routers/email_report.py — real Supabase, no real emails sent.

@pytest.mark.integration required (see tests/conftest.py's autouse
mock_supabase_singleton). GET /report-preview is fully live-tested since
it only reads real data and builds HTML. POST /send-report's auth boundary
is live-tested, but its success path is NOT — that would send a real email
on every test run, which an automated suite shouldn't do routinely.
"""
import pytest
from main import app
from fastapi.testclient import TestClient
pytestmark = pytest.mark.live
client = TestClient(app)


@pytest.mark.integration
class TestEmailReportFlowLive:

    def test_send_report_rejects_request_with_no_token(self):
        response = client.post("/api/v1/email/send-report", json={"email": "someone@example.com"})
        assert response.status_code == 401

    def test_report_preview_rejects_request_with_no_token(self):
        response = client.get("/api/v1/email/report-preview")
        assert response.status_code == 401

    def test_report_preview_succeeds_for_brand_new_user(self, live_auth_headers):
        response = client.get("/api/v1/email/report-preview", headers=live_auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert "html" in body
        assert "<!DOCTYPE html>" in body["html"]
        # Brand-new user, no sessions yet.
        assert "No practice sessions this week" in body["html"]
        assert "🌱 Fresher" in body["html"]