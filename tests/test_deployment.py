import json
import unittest
from dataclasses import replace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.health.router import router
from app.health.service import dependency_status
from app.start import server_options


def production_settings(**overrides):
    values = {
        "environment": "production",
        "client_origin": "https://app.example.ch",
        "client_origin_regex": None,
        "supabase_url": "https://project.supabase.co",
        "supabase_service_role_key": "server-test-key",
        "allowed_hosts": ("api.example.ch",),
        "enforce_https": True,
        "redis_url": None,
    }
    return Settings(**(values | overrides))


class ProductionConfigurationTests(unittest.TestCase):
    def test_development_still_allows_local_setup(self):
        Settings(environment="development", client_origin="http://localhost:5173")

    def test_production_rejects_unsafe_or_incomplete_configuration(self):
        valid = production_settings()
        for field, value in [
            ("environment", "prodution"),
            ("client_origin", "http://app.example.ch"),
            ("client_origin", "https://localhost"),
            ("client_origin", "https://192.168.1.2"),
            ("client_origin", "https://app.example.ch/path"),
            ("client_origin", "https://app.example.ch/"),
            ("client_origin_regex", ".*"),
            ("supabase_url", None),
            ("supabase_service_role_key", "your-service-role-key"),
            ("allowed_hosts", ("*",)),
            ("allowed_hosts", ("localhost",)),
            ("allowed_hosts", ("https://api.example.ch",)),
            ("enforce_https", False),
            ("redis_url", "https://redis.example.ch"),
        ]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                replace(valid, **{field: value})

    def test_validation_never_exposes_credentials(self):
        with self.assertRaises(ValueError) as error:
            production_settings(redis_url="https://user:super-secret@redis.example.ch")
        self.assertNotIn("super-secret", str(error.exception))

    @patch("app.start.settings")
    def test_multiple_workers_require_shared_rate_limiter(self, settings):
        settings.redis_url = None
        with patch.dict("os.environ", {"WEB_CONCURRENCY": "2", "PORT": "8080"}):
            with self.assertRaises(ValueError):
                server_options()
            settings.redis_url = "redis://redis:6379/0"
            options = server_options()
        self.assertEqual(options["workers"], 2)
        self.assertEqual(options["port"], 8080)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    @patch("app.health.router.dependency_status")
    def test_liveness_is_independent_of_database(self, dependencies):
        self.assertEqual(self.client.get("/health").status_code, 200)
        dependencies.assert_not_called()

    @patch("app.health.router.dependency_status")
    def test_readiness_reflects_dependency_failure(self, dependencies):
        dependencies.return_value = {"database": "unavailable"}
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["cache-control"], "no-store")
        dependencies.return_value = {"database": "ok"}
        self.assertEqual(self.client.get("/ready").status_code, 200)
        dependencies.return_value = {"database": "ok", "redis": "unavailable"}
        self.assertEqual(self.client.get("/ready").status_code, 503)

    @patch("app.health.service.settings")
    @patch("app.health.service._readiness_redis")
    @patch("app.health.service._readiness_supabase")
    def test_dependency_failures_do_not_expose_internal_errors(self, database, redis, settings):
        settings.redis_url = "redis://localhost:6379"
        database.side_effect = RuntimeError("private-database-secret")
        redis.return_value.ping.side_effect = RuntimeError("private-redis-secret")
        result = dependency_status()
        self.assertEqual(result, {"database": "unavailable", "redis": "unavailable"})
        self.assertNotIn("secret", json.dumps(result))

    @patch("app.health.service.settings")
    @patch("app.health.service._readiness_redis")
    @patch("app.health.service._readiness_supabase")
    def test_readiness_accepts_an_empty_profiles_table_and_skips_unconfigured_redis(self, database, redis, settings):
        settings.redis_url = None
        database.return_value.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock(data=[])
        self.assertEqual(dependency_status(), {"database": "ok"})
        redis.assert_not_called()
