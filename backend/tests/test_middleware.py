import pytest
from fastapi.testclient import TestClient
from main import app

# Two clients — one raises exceptions, one returns 500 responses
client = TestClient(app, raise_server_exceptions=False)
raising_client = TestClient(app, raise_server_exceptions=True)

# --- Test routes registered on the app ---

@app.get("/test")
def ping_route():
    return {"ok": True}   # simple, no internal HTTP calls

@app.get("/error")
def error_route():
    raise RuntimeError("boom")

# --- Tests ---

def test_full_middleware_chain():
    response = client.get("/test")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

def test_request_lifecycle():
    response = client.get("/test")
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] is not None

def test_auth_header_presence_effect():
    r1 = client.get("/test")
    r2 = client.get("/test", headers={"authorization": "Bearer dummy.token.value"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert "X-Request-ID" in r1.headers
    assert "X-Request-ID" in r2.headers

def test_full_exception_flow():
    # raise_server_exceptions=False → returns 500 instead of re-raising
    response = client.get("/error")
    assert response.status_code == 500

def test_exception_handling():
    # raise_server_exceptions=True → re-raises the exception
    with pytest.raises(RuntimeError):
        raising_client.get("/error")

def test_excluded_paths_bypass():
    response = client.get("/health")
    assert response.status_code in (200, 404)

def test_options_preflight():
    response = client.options(
        "/test",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.status_code in (200, 204)