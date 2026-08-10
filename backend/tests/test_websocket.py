"""
Tests for core/websocket.py — ConnectionManager, notification helpers,
and the websocket_endpoint handler.

Two layers of testing here:
1. Direct unit tests against ConnectionManager methods using AsyncMock
   websocket doubles — fast, precise control over client_state/exceptions.
2. Real end-to-end tests through FastAPI's TestClient.websocket_connect,
   using an isolated app with just ws_router mounted (no main.py needed),
   for the parts where going through real ASGI websocket plumbing is more
   faithful than mocking (the welcome message, heartbeat round-trip, etc).
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketState

from core.websocket import (
    ConnectionManager,
    MessageType,
    websocket_endpoint,
    notify_job_status,
    notify_analysis_complete,
    notify_error,
    broadcast_market_update,
    send_recommendation,
    ws_router,
)


def make_mock_ws(state=WebSocketState.CONNECTED):
    ws = MagicMock()
    ws.client_state = state
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


# =============================================================================
# ConnectionManager.connect / disconnect
# =============================================================================

class TestConnect:
    async def test_connect_accepts_and_registers_globally(self):
        manager = ConnectionManager()
        ws = make_mock_ws()

        await manager.connect(ws)

        ws.accept.assert_awaited_once()
        assert ws in manager._all_connections
        assert manager._connections == {}

    async def test_connect_with_user_id_registers_per_user(self):
        manager = ConnectionManager()
        ws = make_mock_ws()

        await manager.connect(ws, user_id="u1")

        assert ws in manager._all_connections
        assert ws in manager._connections["u1"]

    async def test_multiple_connections_same_user(self):
        manager = ConnectionManager()
        ws1, ws2 = make_mock_ws(), make_mock_ws()

        await manager.connect(ws1, user_id="u1")
        await manager.connect(ws2, user_id="u1")

        assert manager._connections["u1"] == {ws1, ws2}


class TestDisconnect:
    async def test_disconnect_removes_from_all_and_user_connections(self):
        manager = ConnectionManager()
        ws = make_mock_ws()
        await manager.connect(ws, user_id="u1")

        await manager.disconnect(ws, user_id="u1")

        assert ws not in manager._all_connections
        assert "u1" not in manager._connections  # empty set is pruned

    async def test_disconnect_keeps_user_entry_if_other_sockets_remain(self):
        manager = ConnectionManager()
        ws1, ws2 = make_mock_ws(), make_mock_ws()
        await manager.connect(ws1, user_id="u1")
        await manager.connect(ws2, user_id="u1")

        await manager.disconnect(ws1, user_id="u1")

        assert "u1" in manager._connections
        assert manager._connections["u1"] == {ws2}

    async def test_disconnect_removes_from_all_rooms(self):
        manager = ConnectionManager()
        ws = make_mock_ws()
        await manager.connect(ws)
        await manager.join_room(ws, "room-a")
        await manager.join_room(ws, "room-b")

        await manager.disconnect(ws)

        assert "room-a" not in manager._rooms  # emptied, so pruned
        assert "room-b" not in manager._rooms

    async def test_disconnect_without_user_id_does_not_error(self):
        manager = ConnectionManager()
        ws = make_mock_ws()
        await manager.connect(ws)

        await manager.disconnect(ws)  # no user_id passed

        assert ws not in manager._all_connections

    async def test_disconnect_unknown_user_id_does_not_raise(self):
        manager = ConnectionManager()
        ws = make_mock_ws()
        await manager.connect(ws)

        await manager.disconnect(ws, user_id="never-connected")  # should be a no-op, no KeyError


# =============================================================================
# join_room / leave_room
# =============================================================================

class TestRooms:
    async def test_join_room_creates_room_if_missing(self):
        manager = ConnectionManager()
        ws = make_mock_ws()

        await manager.join_room(ws, "room-1")

        assert ws in manager._rooms["room-1"]

    async def test_leave_room_prunes_empty_room(self):
        manager = ConnectionManager()
        ws = make_mock_ws()
        await manager.join_room(ws, "room-1")

        await manager.leave_room(ws, "room-1")

        assert "room-1" not in manager._rooms

    async def test_leave_room_keeps_room_with_remaining_members(self):
        manager = ConnectionManager()
        ws1, ws2 = make_mock_ws(), make_mock_ws()
        await manager.join_room(ws1, "room-1")
        await manager.join_room(ws2, "room-1")

        await manager.leave_room(ws1, "room-1")

        assert manager._rooms["room-1"] == {ws2}

    async def test_leave_nonexistent_room_is_a_no_op(self):
        manager = ConnectionManager()
        ws = make_mock_ws()

        await manager.leave_room(ws, "never-joined")  # should not raise


# =============================================================================
# send_personal_message
# =============================================================================

class TestSendPersonalMessage:
    async def test_sends_to_connected_socket_and_stamps_timestamp(self):
        manager = ConnectionManager()
        ws = make_mock_ws(state=WebSocketState.CONNECTED)
        await manager.connect(ws, user_id="u1")

        await manager.send_personal_message({"type": "hello"}, "u1")

        ws.send_json.assert_awaited_once()
        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "hello"
        assert "timestamp" in sent

    async def test_unknown_user_id_is_a_no_op(self):
        manager = ConnectionManager()
        # Should not raise even though "ghost" was never connected
        await manager.send_personal_message({"type": "hello"}, "ghost")

    async def test_non_connected_socket_is_cleaned_up_without_sending(self):
        manager = ConnectionManager()
        ws = make_mock_ws(state=WebSocketState.DISCONNECTED)
        await manager.connect(ws, user_id="u1")

        await manager.send_personal_message({"type": "hello"}, "u1")

        ws.send_json.assert_not_called()
        assert ws not in manager._connections.get("u1", set())

    async def test_send_exception_marks_socket_disconnected_and_cleans_up(self):
        manager = ConnectionManager()
        ws = make_mock_ws(state=WebSocketState.CONNECTED)
        ws.send_json = AsyncMock(side_effect=RuntimeError("connection reset"))
        await manager.connect(ws, user_id="u1")

        await manager.send_personal_message({"type": "hello"}, "u1")

        assert ws not in manager._connections.get("u1", set())


# =============================================================================
# broadcast_to_room
# =============================================================================

class TestBroadcastToRoom:
    async def test_missing_room_stamps_timestamp_but_sends_nothing(self):
        manager = ConnectionManager()
        message = {"type": "update"}

        await manager.broadcast_to_room(message, "no-such-room")

        # Documents actual behavior: the message dict is mutated with a
        # timestamp *before* the room-existence check runs, even though
        # nothing is actually sent anywhere.
        assert "timestamp" in message

    async def test_sends_to_all_connected_members(self):
        manager = ConnectionManager()
        ws1 = make_mock_ws(state=WebSocketState.CONNECTED)
        ws2 = make_mock_ws(state=WebSocketState.CONNECTED)
        await manager.join_room(ws1, "room-1")
        await manager.join_room(ws2, "room-1")

        await manager.broadcast_to_room({"type": "update"}, "room-1")

        ws1.send_json.assert_awaited_once()
        ws2.send_json.assert_awaited_once()

    async def test_disconnected_member_is_pruned_from_room(self):
        manager = ConnectionManager()
        ws1 = make_mock_ws(state=WebSocketState.CONNECTED)
        ws2 = make_mock_ws(state=WebSocketState.DISCONNECTED)
        await manager.join_room(ws1, "room-1")
        await manager.join_room(ws2, "room-1")

        await manager.broadcast_to_room({"type": "update"}, "room-1")

        assert manager._rooms["room-1"] == {ws1}

    async def test_send_exception_prunes_member_from_room(self):
        manager = ConnectionManager()
        ws1 = make_mock_ws(state=WebSocketState.CONNECTED)
        ws2 = make_mock_ws(state=WebSocketState.CONNECTED)
        ws2.send_json = AsyncMock(side_effect=RuntimeError("connection reset"))
        await manager.join_room(ws1, "room-1")
        await manager.join_room(ws2, "room-1")

        await manager.broadcast_to_room({"type": "update"}, "room-1")

        assert manager._rooms["room-1"] == {ws1}


# =============================================================================
# broadcast
# =============================================================================

class TestBroadcast:
    async def test_sends_to_all_active_connections(self):
        manager = ConnectionManager()
        ws1 = make_mock_ws(state=WebSocketState.CONNECTED)
        ws2 = make_mock_ws(state=WebSocketState.CONNECTED)
        await manager.connect(ws1)
        await manager.connect(ws2)

        await manager.broadcast({"type": "market_update"})

        ws1.send_json.assert_awaited_once()
        ws2.send_json.assert_awaited_once()

    async def test_broadcast_exception_prunes_socket(self):
        manager = ConnectionManager()
        ws = make_mock_ws(state=WebSocketState.CONNECTED)
        ws.send_json = AsyncMock(side_effect=RuntimeError("boom"))
        await manager.connect(ws)

        await manager.broadcast({"type": "market_update"})

        assert ws not in manager._all_connections

    async def test_broadcast_skips_and_prunes_non_connected_socket(self):
        manager = ConnectionManager()
        ws = make_mock_ws(state=WebSocketState.DISCONNECTED)
        await manager.connect(ws)

        await manager.broadcast({"type": "market_update"})

        ws.send_json.assert_not_called()
        assert ws not in manager._all_connections


# =============================================================================
# get_connected_users / get_connection_count
# =============================================================================

class TestConnectionIntrospection:
    async def test_get_connected_users(self):
        manager = ConnectionManager()
        await manager.connect(make_mock_ws(), user_id="u1")
        await manager.connect(make_mock_ws(), user_id="u2")

        assert sorted(manager.get_connected_users()) == ["u1", "u2"]

    async def test_get_connection_count_for_specific_user(self):
        manager = ConnectionManager()
        await manager.connect(make_mock_ws(), user_id="u1")
        await manager.connect(make_mock_ws(), user_id="u1")

        assert manager.get_connection_count("u1") == 2

    async def test_get_connection_count_for_unknown_user_is_zero(self):
        manager = ConnectionManager()
        assert manager.get_connection_count("ghost") == 0

    async def test_get_connection_count_total(self):
        manager = ConnectionManager()
        await manager.connect(make_mock_ws())
        await manager.connect(make_mock_ws())

        assert manager.get_connection_count() == 2


# =============================================================================
# Module-level notification helpers
# =============================================================================

class TestNotificationHelpers:
    async def test_notify_job_status_builds_correct_message(self, monkeypatch):
        mock_send = AsyncMock()
        monkeypatch.setattr("core.websocket.manager.send_personal_message", mock_send)

        await notify_job_status("u1", "job-1", "running", progress=50)

        mock_send.assert_awaited_once_with(
            {
                "type": MessageType.JOB_STATUS.value,
                "job_id": "job-1",
                "status": "running",
                "progress": 50,
            },
            "u1",
        )

    async def test_notify_analysis_complete_builds_correct_message(self, monkeypatch):
        mock_send = AsyncMock()
        monkeypatch.setattr("core.websocket.manager.send_personal_message", mock_send)

        await notify_analysis_complete("u1", "job-2", {"score": 90})

        mock_send.assert_awaited_once_with(
            {
                "type": MessageType.JOB_STATUS.value,
                "job_id": "job-2",
                "status": "completed",
                "result": {"score": 90},
            },
            "u1",
        )

    async def test_notify_error_builds_correct_message(self, monkeypatch):
        mock_send = AsyncMock()
        monkeypatch.setattr("core.websocket.manager.send_personal_message", mock_send)

        await notify_error("u1", "something broke", code="ERR_1")

        mock_send.assert_awaited_once_with(
            {"type": MessageType.ERROR.value, "error": "something broke", "code": "ERR_1"},
            "u1",
        )

    async def test_broadcast_market_update_builds_correct_message(self, monkeypatch):
        mock_broadcast = AsyncMock()
        monkeypatch.setattr("core.websocket.manager.broadcast", mock_broadcast)

        await broadcast_market_update({"index": 123})

        mock_broadcast.assert_awaited_once_with(
            {"type": MessageType.MARKET_UPDATE.value, "data": {"index": 123}}
        )

    async def test_send_recommendation_builds_correct_message(self, monkeypatch):
        mock_send = AsyncMock()
        monkeypatch.setattr("core.websocket.manager.send_personal_message", mock_send)

        await send_recommendation("u1", {"title": "Backend Engineer"})

        mock_send.assert_awaited_once_with(
            {
                "type": MessageType.RECOMMENDATION.value,
                "recommendation": {"title": "Backend Engineer"},
            },
            "u1",
        )


# =============================================================================
# websocket_endpoint — direct unit tests with a mocked WebSocket
# =============================================================================

def make_endpoint_ws(receive_side_effects, user_id_query=""):
    """Build a mock WebSocket whose receive_text() yields the given
    sequence of values/exceptions, terminating the endpoint's while loop."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.query_params = {"user_id": user_id_query} if user_id_query else {}
    ws.receive_text = AsyncMock(side_effect=receive_side_effects)
    return ws


class TestWebsocketEndpoint:
    async def test_sends_welcome_message_with_resolved_user_id(self, monkeypatch):
        mock_manager = MagicMock()
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        monkeypatch.setattr("core.websocket.manager", mock_manager)

        ws = make_endpoint_ws([WebSocketDisconnect()])

        await websocket_endpoint(ws, user_id="u1")

        welcome_call = ws.send_json.call_args_list[0][0][0]
        assert welcome_call["type"] == MessageType.NOTIFICATION.value
        assert welcome_call["user_id"] == "u1"
        mock_manager.connect.assert_awaited_once_with(ws, "u1")
        mock_manager.disconnect.assert_awaited_once_with(ws, "u1")

    async def test_falls_back_to_query_param_user_id(self, monkeypatch):
        mock_manager = MagicMock()
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        monkeypatch.setattr("core.websocket.manager", mock_manager)

        ws = make_endpoint_ws([WebSocketDisconnect()], user_id_query="from-query")

        await websocket_endpoint(ws, user_id=None)

        mock_manager.connect.assert_awaited_once_with(ws, "from-query")

    async def test_heartbeat_message_gets_alive_response(self, monkeypatch):
        mock_manager = MagicMock()
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        monkeypatch.setattr("core.websocket.manager", mock_manager)

        heartbeat_msg = json.dumps({"type": "heartbeat"})
        ws = make_endpoint_ws([heartbeat_msg, WebSocketDisconnect()])

        await websocket_endpoint(ws, user_id="u1")

        sent_messages = [c[0][0] for c in ws.send_json.call_args_list]
        assert {"type": "heartbeat", "status": "alive"} in sent_messages

    async def test_join_room_with_room_id_calls_manager(self, monkeypatch):
        mock_manager = MagicMock()
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        mock_manager.join_room = AsyncMock()
        monkeypatch.setattr("core.websocket.manager", mock_manager)

        msg = json.dumps({"type": "join_room", "room_id": "room-1"})
        ws = make_endpoint_ws([msg, WebSocketDisconnect()])

        await websocket_endpoint(ws, user_id="u1")

        mock_manager.join_room.assert_awaited_once_with(ws, "room-1")

    async def test_join_room_without_room_id_is_ignored(self, monkeypatch):
        mock_manager = MagicMock()
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        mock_manager.join_room = AsyncMock()
        monkeypatch.setattr("core.websocket.manager", mock_manager)

        msg = json.dumps({"type": "join_room"})  # no room_id
        ws = make_endpoint_ws([msg, WebSocketDisconnect()])

        await websocket_endpoint(ws, user_id="u1")

        mock_manager.join_room.assert_not_called()

    async def test_leave_room_with_room_id_calls_manager(self, monkeypatch):
        mock_manager = MagicMock()
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        mock_manager.leave_room = AsyncMock()
        monkeypatch.setattr("core.websocket.manager", mock_manager)

        msg = json.dumps({"type": "leave_room", "room_id": "room-1"})
        ws = make_endpoint_ws([msg, WebSocketDisconnect()])

        await websocket_endpoint(ws, user_id="u1")

        mock_manager.leave_room.assert_awaited_once_with(ws, "room-1")

    async def test_unknown_message_type_is_logged_and_ignored(self, monkeypatch, caplog):
        mock_manager = MagicMock()
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        monkeypatch.setattr("core.websocket.manager", mock_manager)

        msg = json.dumps({"type": "something_weird"})
        ws = make_endpoint_ws([msg, WebSocketDisconnect()])

        with caplog.at_level("WARNING"):
            await websocket_endpoint(ws, user_id="u1")

        assert any("Unknown message type" in r.message for r in caplog.records)

    async def test_invalid_json_is_logged_and_loop_continues(self, monkeypatch, caplog):
        mock_manager = MagicMock()
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        monkeypatch.setattr("core.websocket.manager", mock_manager)

        ws = make_endpoint_ws(["not valid json{{{", WebSocketDisconnect()])

        with caplog.at_level("WARNING"):
            await websocket_endpoint(ws, user_id="u1")

        assert any("Invalid JSON" in r.message for r in caplog.records)
        # Loop continued and then exited cleanly via the disconnect below
        mock_manager.disconnect.assert_awaited_once()

    async def test_generic_exception_during_receive_is_logged_and_disconnects(
        self, monkeypatch, caplog
    ):
        mock_manager = MagicMock()
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        monkeypatch.setattr("core.websocket.manager", mock_manager)

        ws = make_endpoint_ws([RuntimeError("socket died")])

        with caplog.at_level("ERROR"):
            await websocket_endpoint(ws, user_id="u1")

        assert any("WebSocket error" in r.message for r in caplog.records)
        mock_manager.disconnect.assert_awaited_once_with(ws, "u1")

    async def test_disconnect_is_always_called_even_on_clean_exit(self, monkeypatch):
        mock_manager = MagicMock()
        mock_manager.connect = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        monkeypatch.setattr("core.websocket.manager", mock_manager)

        ws = make_endpoint_ws([WebSocketDisconnect()])

        await websocket_endpoint(ws, user_id="u1")

        mock_manager.disconnect.assert_awaited_once_with(ws, "u1")


# =============================================================================
# ws_router — real end-to-end test through TestClient.websocket_connect
# =============================================================================

@pytest.fixture
def ws_app():
    app = FastAPI()
    app.include_router(ws_router)
    return app


class TestWsRouterEndToEnd:
    def test_connect_and_receive_welcome_message(self, ws_app):
        client = TestClient(ws_app)
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            assert data["type"] == MessageType.NOTIFICATION.value

    def test_user_scoped_path_echoes_user_id_in_welcome(self, ws_app):
        client = TestClient(ws_app)
        with client.websocket_connect("/ws/fox-123") as websocket:
            data = websocket.receive_json()
            assert data["user_id"] == "fox-123"

    def test_heartbeat_round_trip(self, ws_app):
        client = TestClient(ws_app)
        with client.websocket_connect("/ws/fox-123") as websocket:
            websocket.receive_json()  # discard welcome message
            websocket.send_json({"type": "heartbeat"})
            response = websocket.receive_json()
            assert response == {"type": "heartbeat", "status": "alive"}