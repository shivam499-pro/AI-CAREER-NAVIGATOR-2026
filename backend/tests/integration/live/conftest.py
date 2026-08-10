"""
Live tests make real calls to the Gemini API through process-lifetime
singleton clients (services.gemini_service._gemini_transport and
modules.interview.manager._interview_service). Both are constructed via
AsyncGeminiTransport.create(), which lazily binds an async HTTP session
to whatever event loop is active on first use.

pytest-asyncio gives each async test its own event loop here (function
scope), torn down at the end of that test. If a singleton's underlying
async session was bound to an earlier test's (now-closed) loop, the
next test's Gemini call fails with "RuntimeError: Event loop is closed"
-- not a real application bug (a real uvicorn server runs on one
persistent event loop for its whole process lifetime and never hits
this), just a mismatch between test-level event loop scoping and
process-level singleton caching.

Reset both singletons before each live test so they're constructed
fresh, bound to that test's own event loop.
"""
import pytest

def pytest_collection_modifyitems(config, items):
    for item in items:
        if "integration/live" in str(item.fspath).replace("\\", "/"):
            item.add_marker(pytest.mark.live)
            
@pytest.fixture(autouse=True)
def _reset_gemini_singletons():
    import services.gemini_service as gemini_service
    import modules.interview.manager as interview_manager

    gemini_service._gemini_transport = None
    interview_manager._interview_service = None
    yield
    gemini_service._gemini_transport = None
    interview_manager._interview_service = None