"""
Tests for core/config.py -- the Settings class.

Settings isn't imported directly by application code (routers/services read
env vars inline via os.getenv()); the one real caller, core/supabase_client.py,
delegates to these accessors but mocks them out in its own tests (see that
file's docstring). These tests cover the real Settings classmethods directly.
"""
from core.config import Settings


class TestSettingsAccessors:
    def test_get_supabase_url_reads_env(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://real.supabase.co")
        assert Settings.get_supabase_url() == "https://real.supabase.co"

    def test_get_service_key_reads_env(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "real-service-key")
        assert Settings.get_service_key() == "real-service-key"

    def test_get_anon_key_reads_env(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_ANON_KEY", "real-anon-key")
        assert Settings.get_anon_key() == "real-anon-key"


class TestIsProduction:
    def test_defaults_to_false_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("ENV", raising=False)
        assert Settings.is_production() is False

    def test_true_when_env_is_production(self, monkeypatch):
        monkeypatch.setenv("ENV", "production")
        assert Settings.is_production() is True

    def test_false_when_env_is_development(self, monkeypatch):
        monkeypatch.setenv("ENV", "development")
        assert Settings.is_production() is False