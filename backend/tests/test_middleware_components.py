"""
Granular unit tests for core/middleware.py.

tests/test_middleware.py already covers the full middleware STACK wired
through the real app (main.app) — CORS, ordering, request IDs end to end.
This file complements it with isolated, unit-level tests for the pieces
that end-to-end smoke tests don't exercise: JWTVerifier's branches,
AuthenticatedUser/APIResponse, the require_* dependency factories,
the require_auth decorator, and the two dispatch() middlewares tested
against minimal standalone apps (so they don't depend on main.py's
full router graph).
"""
import asyncio
import time
import base64
import json as json_module
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from core.middleware import (
    UserRole,
    Permission,
    AuthenticatedUser,
    APIResponse,
    JWTVerifier,
    jwt_verifier,
    get_current_user,
    require_permission,
    require_any_permission,
    require_role,
    format_response,
    require_auth,
    get_current_user_sync,
    verify_token_sync,
    log_request,
    StructuredLoggingMiddleware,
    AuthMiddleware,
)


def make_jwt(payload: dict) -> str:
    """Build an unsigned-but-structurally-valid 3-part JWT for local decode tests."""
    def b64(obj):
        raw = json_module.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{b64({'alg': 'HS256'})}.{b64(payload)}.fakesignature"


# =============================================================================
# AuthenticatedUser
# =============================================================================

class TestAuthenticatedUser:
    def test_defaults_permissions_to_empty_list(self):
        user = AuthenticatedUser(user_id="u1", email="u1@example.com")
        assert user.permissions == []
        assert user.role == "user"

    def test_has_permission_admin_bypasses_check(self):
        user = AuthenticatedUser("u1", "u1@x.com", role="admin", permissions=[])
        assert user.has_permission("write:anything") is True

    def test_has_permission_checks_membership(self):
        user = AuthenticatedUser("u1", "u1@x.com", permissions=["read:profile"])
        assert user.has_permission("read:profile") is True
        assert user.has_permission("write:profile") is False

    def test_has_any_permission_admin_bypasses_check(self):
        user = AuthenticatedUser("u1", "u1@x.com", role="admin", permissions=[])
        assert user.has_any_permission(["anything"]) is True

    def test_has_any_permission_true_if_one_matches(self):
        user = AuthenticatedUser("u1", "u1@x.com", permissions=["read:jobs"])
        assert user.has_any_permission(["read:jobs", "write:jobs"]) is True

    def test_has_any_permission_false_if_none_match(self):
        user = AuthenticatedUser("u1", "u1@x.com", permissions=["read:jobs"])
        assert user.has_any_permission(["write:jobs", "admin:access"]) is False

    def test_to_dict(self):
        user = AuthenticatedUser("u1", "u1@x.com", role="premium", permissions=["read:jobs"])
        assert user.to_dict() == {
            "user_id": "u1",
            "email": "u1@x.com",
            "role": "premium",
            "permissions": ["read:jobs"],
        }


# =============================================================================
# APIResponse
# =============================================================================

class TestAPIResponse:
    def test_to_dict_without_meta(self):
        resp = APIResponse(success=True, data={"x": 1})
        d = resp.to_dict()
        assert d == {"success": True, "data": {"x": 1}, "error": None}

    def test_to_dict_with_meta(self):
        resp = APIResponse(success=False, error="oops", meta={"error_code": "X"})
        d = resp.to_dict()
        assert d["meta"] == {"error_code": "X"}

    def test_success_response_without_message(self):
        result = APIResponse.success_response(data={"a": 1})
        assert result["success"] is True
        assert result["data"] == {"a": 1}
        assert result["error"] is None
        assert "timestamp" in result["meta"]
        assert "message" not in result["meta"]

    def test_success_response_with_message(self):
        result = APIResponse.success_response(data={"a": 1}, message="done")
        assert result["meta"]["message"] == "done"

    def test_error_response_minimal(self):
        result = APIResponse.error_response("bad thing")
        assert result["success"] is False
        assert result["data"] is None
        assert result["error"] == "bad thing"
        assert "error_code" not in result["meta"]
        assert "details" not in result["meta"]

    def test_error_response_with_code_and_details(self):
        result = APIResponse.error_response(
            "bad thing", code="BAD_CODE", details={"field": "x"}
        )
        assert result["meta"]["error_code"] == "BAD_CODE"
        assert result["meta"]["details"] == {"field": "x"}


# =============================================================================
# JWTVerifier._decode_jwt_payload
# =============================================================================

class TestDecodeJwtPayload:
    def test_valid_token_decodes_payload(self):
        verifier = JWTVerifier()
        token = make_jwt({"sub": "user-1", "email": "a@b.com"})

        payload = verifier._decode_jwt_payload(token)

        assert payload["sub"] == "user-1"
        assert payload["email"] == "a@b.com"

    def test_malformed_token_wrong_part_count_returns_none(self):
        verifier = JWTVerifier()
        assert verifier._decode_jwt_payload("not.a.valid.jwt.at.all") is None
        assert verifier._decode_jwt_payload("onlyonepart") is None

    def test_invalid_base64_returns_none(self):
        verifier = JWTVerifier()
        assert verifier._decode_jwt_payload("abc.!!!not-base64!!!.sig") is None


# =============================================================================
# JWTVerifier._get_role_permissions
# =============================================================================

class TestGetRolePermissions:
    def test_admin_gets_admin_access(self):
        verifier = JWTVerifier()
        perms = verifier._get_role_permissions("admin")
        assert Permission.ADMIN_ACCESS.value in perms
        assert Permission.WRITE_DOCUMENTS.value in perms

    def test_premium_excludes_admin_access(self):
        verifier = JWTVerifier()
        perms = verifier._get_role_permissions("premium")
        assert Permission.ADMIN_ACCESS.value not in perms
        assert Permission.WRITE_INTERVIEW.value in perms

    def test_user_is_mostly_read_only(self):
        verifier = JWTVerifier()
        perms = verifier._get_role_permissions("user")
        assert Permission.READ_PROFILE.value in perms
        assert Permission.WRITE_PROFILE.value in perms
        assert Permission.WRITE_ANALYSIS.value not in perms

    def test_guest_is_minimal(self):
        verifier = JWTVerifier()
        perms = verifier._get_role_permissions("guest")
        assert perms == [Permission.READ_ANALYSIS.value, Permission.READ_JOBS.value]

    def test_unknown_role_falls_back_to_guest(self):
        verifier = JWTVerifier()
        assert verifier._get_role_permissions("some-made-up-role") == \
            verifier._get_role_permissions("guest")


# =============================================================================
# JWTVerifier.verify_token
# =============================================================================

class TestVerifyToken:
    async def test_no_authorization_header_raises_401(self):
        verifier = JWTVerifier()
        with pytest.raises(HTTPException) as exc_info:
            await verifier.verify_token(None)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["meta"]["error_code"] == "NO_AUTH_HEADER"

    async def test_no_authorization_header_empty_string_raises_401(self):
        verifier = JWTVerifier()
        with pytest.raises(HTTPException) as exc_info:
            await verifier.verify_token("")
        assert exc_info.value.status_code == 401

    async def test_cached_user_short_circuits_network_call(self, monkeypatch):
        verifier = JWTVerifier()
        token = make_jwt({"sub": "user-42"})
        expected_key = verifier._token_cache_key(token)

        cached_data = {
            "user_id": "user-42", "email": "cached@x.com",
            "role": "user", "permissions": ["read:profile"],
        }
        monkeypatch.setattr(
            "core.middleware.cache.get",
            lambda key: cached_data if key == expected_key else None,
        )

        mock_verify_supabase = AsyncMock()
        monkeypatch.setattr(verifier, "_verify_supabase_token", mock_verify_supabase)

        result = await verifier.verify_token(f"Bearer {token}")

        assert result.user_id == "user-42"
        assert result.email == "cached@x.com"
        mock_verify_supabase.assert_not_called()

    async def test_cache_miss_calls_supabase_and_caches_result(self, monkeypatch):
        verifier = JWTVerifier()
        token = make_jwt({"sub": "user-42"})

        monkeypatch.setattr("core.middleware.cache.get", lambda key: None)
        set_calls = []
        monkeypatch.setattr(
            "core.middleware.cache.set",
            lambda key, value, ttl: set_calls.append((key, value, ttl)),
        )

        fresh_user = AuthenticatedUser("user-42", "fresh@x.com")
        mock_verify_supabase = AsyncMock(return_value=fresh_user)
        monkeypatch.setattr(verifier, "_verify_supabase_token", mock_verify_supabase)

        result = await verifier.verify_token(f"Bearer {token}")

        assert result is fresh_user
        mock_verify_supabase.assert_called_once_with(token)
        assert len(set_calls) == 1
        # Cache key must be derived from the token itself, not from the
        # (unverified) "sub" claim inside it.
        assert set_calls[0][0] == verifier._token_cache_key(token)
        assert set_calls[0][0] != "jwt:user:user-42"

    async def test_forged_token_with_victim_sub_does_not_hit_victim_cache_entry(self, monkeypatch):
        """
        Regression test for a fixed auth-bypass: caching must never be keyed
        by an unverified claim. A token that merely *claims* to belong to a
        user who has a valid cache entry must NOT be able to ride on that
        entry - it has to pass real Supabase verification on its own.
        """
        verifier = JWTVerifier()

        victim_token = make_jwt({"sub": "victim-1"})
        victim_cache_key = verifier._token_cache_key(victim_token)
        victim_cached_data = {
            "user_id": "victim-1", "email": "victim@x.com",
            "role": "user", "permissions": ["read:profile"],
        }

        # Simulate a cache that only has the victim's *real, previously
        # verified* token cached - nothing keyed by "victim-1" alone.
        fake_cache_store = {victim_cache_key: victim_cached_data}
        monkeypatch.setattr(
            "core.middleware.cache.get", lambda key: fake_cache_store.get(key)
        )
        monkeypatch.setattr("core.middleware.cache.set", lambda *a, **k: None)

        # Attacker crafts a different token that merely claims the same sub.
        forged_token = make_jwt({"sub": "victim-1", "email": "attacker-controlled"})
        assert forged_token != victim_token

        mock_verify_supabase = AsyncMock(
            side_effect=HTTPException(status_code=401, detail="invalid signature")
        )
        monkeypatch.setattr(verifier, "_verify_supabase_token", mock_verify_supabase)

        with pytest.raises(HTTPException):
            await verifier.verify_token(f"Bearer {forged_token}")

        # The forged token must have been sent to real verification, not
        # short-circuited via the victim's cache entry.
        mock_verify_supabase.assert_called_once_with(forged_token)

    async def test_undecodable_payload_still_calls_supabase(self, monkeypatch):
        verifier = JWTVerifier()

        fresh_user = AuthenticatedUser("user-99", "x@x.com")
        mock_verify_supabase = AsyncMock(return_value=fresh_user)
        monkeypatch.setattr(verifier, "_verify_supabase_token", mock_verify_supabase)
        monkeypatch.setattr("core.middleware.cache.set", lambda *a, **k: None)

        result = await verifier.verify_token("Bearer not-a-real-jwt")

        assert result is fresh_user
        mock_verify_supabase.assert_called_once()

    async def test_strips_bearer_prefix(self, monkeypatch):
        verifier = JWTVerifier()
        captured = {}

        async def fake_verify(token):
            captured["token"] = token
            return AuthenticatedUser("u", "e@x.com")

        monkeypatch.setattr(verifier, "_verify_supabase_token", fake_verify)
        monkeypatch.setattr("core.middleware.cache.set", lambda *a, **k: None)

        await verifier.verify_token("Bearer raw-token-value")

        assert captured["token"] == "raw-token-value"

    async def test_no_bearer_prefix_uses_raw_value(self, monkeypatch):
        verifier = JWTVerifier()
        captured = {}

        async def fake_verify(token):
            captured["token"] = token
            return AuthenticatedUser("u", "e@x.com")

        monkeypatch.setattr(verifier, "_verify_supabase_token", fake_verify)
        monkeypatch.setattr("core.middleware.cache.set", lambda *a, **k: None)

        await verifier.verify_token("raw-token-no-prefix")

        assert captured["token"] == "raw-token-no-prefix"


# =============================================================================
# JWTVerifier._verify_supabase_token
# =============================================================================

class TestVerifySupabaseToken:
    async def test_missing_config_raises_500(self):
        verifier = JWTVerifier()
        verifier.supabase_url = ""
        verifier.supabase_key = ""

        with pytest.raises(HTTPException) as exc_info:
            await verifier._verify_supabase_token("some-token")

        assert exc_info.value.status_code == 500

    async def test_successful_verification_returns_user_with_role_permissions(self):
        verifier = JWTVerifier()
        verifier.supabase_url = "https://test.supabase.co"
        verifier.supabase_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "user-1",
            "email": "a@b.com",
            "user_metadata": {"role": "premium"},
        }

        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.middleware.httpx.AsyncClient", return_value=mock_async_client):
            user = await verifier._verify_supabase_token("some-token")

        assert user.user_id == "user-1"
        assert user.email == "a@b.com"
        assert user.role == "premium"
        assert Permission.WRITE_INTERVIEW.value in user.permissions

    async def test_defaults_role_to_user_when_metadata_missing(self):
        verifier = JWTVerifier()
        verifier.supabase_url = "https://test.supabase.co"
        verifier.supabase_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "user-1", "email": "a@b.com"}

        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.middleware.httpx.AsyncClient", return_value=mock_async_client):
            user = await verifier._verify_supabase_token("some-token")

        assert user.role == "user"

    async def test_non_200_response_raises_401_invalid_token(self):
        verifier = JWTVerifier()
        verifier.supabase_url = "https://test.supabase.co"
        verifier.supabase_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.middleware.httpx.AsyncClient", return_value=mock_async_client):
            with pytest.raises(HTTPException) as exc_info:
                await verifier._verify_supabase_token("bad-token")

        assert exc_info.value.status_code == 401

    async def test_missing_user_id_raises_401_invalid_payload(self):
        verifier = JWTVerifier()
        verifier.supabase_url = "https://test.supabase.co"
        verifier.supabase_key = "test-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "a@b.com"}  # no "id"

        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(return_value=mock_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.middleware.httpx.AsyncClient", return_value=mock_async_client):
            with pytest.raises(HTTPException) as exc_info:
                await verifier._verify_supabase_token("some-token")

        assert exc_info.value.status_code == 401

    async def test_network_exception_raises_401_auth_failed(self):
        verifier = JWTVerifier()
        verifier.supabase_url = "https://test.supabase.co"
        verifier.supabase_key = "test-key"

        mock_async_client = AsyncMock()
        mock_async_client.get = AsyncMock(side_effect=Exception("connection reset"))
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)

        with patch("core.middleware.httpx.AsyncClient", return_value=mock_async_client):
            with pytest.raises(HTTPException) as exc_info:
                await verifier._verify_supabase_token("some-token")

        assert exc_info.value.status_code == 401


# =============================================================================
# JWTVerifier.invalidate_user_cache
# =============================================================================

class TestInvalidateUserCache:
    def test_deletes_correct_cache_key(self, monkeypatch):
        verifier = JWTVerifier()
        deleted = []
        monkeypatch.setattr("core.middleware.cache.delete", lambda key: deleted.append(key))

        verifier.invalidate_user_cache("user-7")

        assert deleted == ["jwt:user:user-7"]


# =============================================================================
# get_current_user dependency
# =============================================================================

class TestGetCurrentUserDependency:
    async def test_delegates_to_jwt_verifier(self, monkeypatch):
        expected = AuthenticatedUser("u1", "u1@x.com")

        async def fake_verify(auth):
            return expected

        monkeypatch.setattr(jwt_verifier, "verify_token", fake_verify)

        result = await get_current_user("Bearer whatever")

        assert result is expected


# =============================================================================
# require_permission / require_any_permission / require_role
# =============================================================================

class TestRequirePermission:
    async def test_raises_403_when_permission_missing(self):
        user = AuthenticatedUser("u1", "u1@x.com", permissions=["read:jobs"])
        dependency = require_permission(Permission.WRITE_JOBS)

        with pytest.raises(HTTPException) as exc_info:
            await dependency(user=user)

        assert exc_info.value.status_code == 403

    async def test_returns_user_when_permission_present(self):
        user = AuthenticatedUser("u1", "u1@x.com", permissions=["write:jobs"])
        dependency = require_permission(Permission.WRITE_JOBS)

        result = await dependency(user=user)

        assert result is user

    async def test_admin_always_passes(self):
        user = AuthenticatedUser("u1", "u1@x.com", role="admin", permissions=[])
        dependency = require_permission(Permission.ADMIN_ACCESS)

        result = await dependency(user=user)

        assert result is user


class TestRequireAnyPermission:
    async def test_raises_403_when_none_match(self):
        user = AuthenticatedUser("u1", "u1@x.com", permissions=["read:jobs"])
        dependency = require_any_permission([Permission.WRITE_JOBS, Permission.ADMIN_ACCESS])

        with pytest.raises(HTTPException) as exc_info:
            await dependency(user=user)

        assert exc_info.value.status_code == 403

    async def test_passes_when_one_matches(self):
        user = AuthenticatedUser("u1", "u1@x.com", permissions=["read:jobs"])
        dependency = require_any_permission([Permission.READ_JOBS, Permission.ADMIN_ACCESS])

        result = await dependency(user=user)

        assert result is user


class TestRequireRole:
    async def test_matching_role_passes(self):
        user = AuthenticatedUser("u1", "u1@x.com", role="premium")
        dependency = require_role(UserRole.PREMIUM)

        result = await dependency(user=user)

        assert result is user

    async def test_admin_bypasses_role_check(self):
        user = AuthenticatedUser("u1", "u1@x.com", role="admin")
        dependency = require_role(UserRole.PREMIUM)

        result = await dependency(user=user)

        assert result is user

    async def test_mismatched_role_raises_403(self):
        user = AuthenticatedUser("u1", "u1@x.com", role="user")
        dependency = require_role(UserRole.PREMIUM)

        with pytest.raises(HTTPException) as exc_info:
            await dependency(user=user)

        assert exc_info.value.status_code == 403

# =============================================================================
# format_response
# =============================================================================

class TestFormatResponse:
    def test_minimal_success(self):
        result = format_response(success=True, data={"a": 1})
        assert result["success"] is True
        assert result["data"] == {"a": 1}
        assert result["error"] is None
        assert "request_id" not in result["meta"]
        assert "message" not in result["meta"]

    def test_includes_request_id_and_message_when_given(self):
        result = format_response(
            success=False, error="bad", message="explain", request_id="req-1"
        )
        assert result["meta"]["request_id"] == "req-1"
        assert result["meta"]["message"] == "explain"
        assert result["error"] == "bad"


# =============================================================================
# require_auth decorator
# =============================================================================

class TestRequireAuthDecorator:
    async def test_missing_auth_header_returns_401_json_response(self):
        @require_auth
        async def protected(request):
            return {"should": "not reach here"}

        fake_request = SimpleNamespace(headers={}, state=SimpleNamespace())

        response = await protected(fake_request)

        assert response.status_code == 401

    async def test_valid_token_attaches_user_and_calls_wrapped_func(self, monkeypatch):
        expected_user = AuthenticatedUser("u1", "u1@x.com", role="user")

        async def fake_verify(auth_header):
            return expected_user

        monkeypatch.setattr(jwt_verifier, "verify_token", fake_verify)

        @require_auth
        async def protected(request):
            return {
                "user_id": request.state.user_id,
                "email": request.state.user_email,
                "role": request.state.user_role,
            }

        fake_request = SimpleNamespace(
            headers={"authorization": "Bearer sometoken"}, state=SimpleNamespace()
        )

        result = await protected(fake_request)

        assert result == {"user_id": "u1", "email": "u1@x.com", "role": "user"}

    async def test_verify_token_http_exception_returns_matching_status(self, monkeypatch):
        async def fake_verify(auth_header):
            raise HTTPException(status_code=403, detail="forbidden")

        monkeypatch.setattr(jwt_verifier, "verify_token", fake_verify)

        @require_auth
        async def protected(request):
            return {"should": "not reach here"}

        fake_request = SimpleNamespace(
            headers={"authorization": "Bearer sometoken"}, state=SimpleNamespace()
        )

        response = await protected(fake_request)

        assert response.status_code == 403


# =============================================================================
# log_request
# =============================================================================

class TestLogRequest:
    def test_info_level(self, caplog):
        with caplog.at_level("INFO"):
            log_request("info", {"endpoint": "/x"})
        assert any("[REQUEST]" in r.message for r in caplog.records)

    def test_warning_level(self, caplog):
        with caplog.at_level("WARNING"):
            log_request("warning", {"endpoint": "/x"})
        assert any(r.levelname == "WARNING" for r in caplog.records)

    def test_error_level_for_unknown_level_string(self, caplog):
        with caplog.at_level("ERROR"):
            log_request("catastrophic", {"endpoint": "/x"})
        assert any(r.levelname == "ERROR" for r in caplog.records)


# =============================================================================
# StructuredLoggingMiddleware — isolated app, doesn't need main.py
# =============================================================================

@pytest.fixture
def logging_app():
    app = FastAPI()
    app.add_middleware(StructuredLoggingMiddleware)

    @app.get("/ok")
    def ok_route():
        return {"ok": True}

    @app.get("/client-error")
    def client_error_route():
        from fastapi import Response
        return Response(status_code=404)

    @app.get("/server-error")
    def server_error_route():
        from fastapi import Response
        return Response(status_code=500)

    @app.get("/boom")
    def boom_route():
        raise RuntimeError("kaboom")

    @app.get("/health")
    def health_route():
        return {"status": "healthy"}

    return app


class TestStructuredLoggingMiddleware:
    def test_adds_request_id_header_on_normal_path(self, logging_app):
        client = TestClient(logging_app)
        response = client.get("/ok")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_excluded_path_skips_request_id_header(self, logging_app):
        client = TestClient(logging_app)
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-Request-ID" not in response.headers

    def test_logs_info_for_2xx(self, logging_app, caplog):
        client = TestClient(logging_app)
        with caplog.at_level("INFO"):
            client.get("/ok")
        assert any('"status": 200' in r.message for r in caplog.records)

    def test_logs_warning_for_4xx(self, logging_app, caplog):
        client = TestClient(logging_app)
        with caplog.at_level("WARNING"):
            client.get("/client-error")
        assert any(r.levelname == "WARNING" for r in caplog.records)

    def test_logs_error_for_5xx(self, logging_app, caplog):
        client = TestClient(logging_app)
        with caplog.at_level("ERROR"):
            client.get("/server-error")
        assert any(r.levelname == "ERROR" for r in caplog.records)

    def test_unhandled_exception_is_logged_and_reraised(self, logging_app, caplog):
        client = TestClient(logging_app, raise_server_exceptions=True)
        with caplog.at_level("ERROR"):
            with pytest.raises(RuntimeError):
                client.get("/boom")
        assert any("kaboom" in r.message for r in caplog.records)

    def test_authenticated_marker_when_auth_header_present(self, logging_app):
        client = TestClient(logging_app)
        response = client.get("/ok", headers={"authorization": "Bearer x"})
        assert response.status_code == 200  # request_id path still succeeds


# =============================================================================
# AuthMiddleware — isolated app
# =============================================================================

@pytest.fixture
def auth_middleware_app():
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/")
    def root():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/api/protected")
    def protected():
        return {"ok": True}

    return app


class TestAuthMiddleware:
    def test_public_path_root_passes_through(self, auth_middleware_app):
        client = TestClient(auth_middleware_app)
        response = client.get("/")
        assert response.status_code == 200

    def test_public_path_health_passes_through(self, auth_middleware_app):
        client = TestClient(auth_middleware_app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_non_public_path_still_reaches_endpoint(self, auth_middleware_app):
        # AuthMiddleware itself doesn't block — actual auth is enforced at the
        # endpoint-dependency level (get_current_user). It just tags the request.
        client = TestClient(auth_middleware_app)
        response = client.get("/api/protected")
        assert response.status_code == 200

# =============================================================================
# get_current_user_sync / verify_token_sync
# =============================================================================

class TestSyncHelpers:
    @pytest.fixture(autouse=True)
    def isolated_event_loop(self):
        """
        get_current_user_sync manages its own event loop via
        asyncio.get_event_loop()/new_event_loop() and closes it when done.
        Give each test in this class a fresh, unclosed loop up front so
        behavior doesn't depend on what a previous test (in this file or
        pytest-asyncio itself) left behind, and restore a usable loop
        afterwards so later tests aren't affected.
        """
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        yield new_loop
        if not new_loop.is_closed():
            new_loop.close()
        asyncio.set_event_loop(asyncio.new_event_loop())

    def test_returns_user_when_verification_succeeds(self, monkeypatch):
        expected_user = AuthenticatedUser("u1", "u1@x.com")

        async def fake_verify(token):
            return expected_user

        monkeypatch.setattr(jwt_verifier, "verify_token", fake_verify)

        result = get_current_user_sync("some-token")

        assert result is expected_user

    def test_returns_none_when_called_from_running_loop(self):
        # Simulate being invoked from inside an already-running event loop.
        async def run_it():
            return get_current_user_sync("some-token")

        result = asyncio.new_event_loop().run_until_complete(run_it())
        assert result is None

    def test_creates_new_loop_when_get_event_loop_raises_runtime_error(self, monkeypatch):
        # Covers the except RuntimeError branch: fires in contexts with no
        # event loop set for the thread. This sandbox's main-thread Python
        # 3.12 doesn't trigger it naturally (it warns and auto-creates one
        # instead), so the RuntimeError path is forced explicitly here.
        expected_user = AuthenticatedUser("u1", "u1@x.com")

        async def fake_verify(token):
            return expected_user

        monkeypatch.setattr(jwt_verifier, "verify_token", fake_verify)
        monkeypatch.setattr(
            "asyncio.get_event_loop",
            MagicMock(side_effect=RuntimeError("no current event loop")),
        )

        result = get_current_user_sync("some-token")

        assert result is expected_user

    def test_verify_token_sync_true_when_user_found(self, monkeypatch):
        monkeypatch.setattr(
            "core.middleware.get_current_user_sync",
            lambda token: AuthenticatedUser("u1", "u1@x.com"),
        )
        assert verify_token_sync("token") is True

    def test_verify_token_sync_false_when_none(self, monkeypatch):
        monkeypatch.setattr("core.middleware.get_current_user_sync", lambda token: None)
        assert verify_token_sync("token") is False