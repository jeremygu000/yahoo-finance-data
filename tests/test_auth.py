from unittest.mock import patch

from fastapi.testclient import TestClient

from market_data.server import app


class TestAuth:
    """Test optional API key authentication middleware."""

    def test_no_api_key_configured_allows_all_requests(self) -> None:
        """When API_KEY is not set, all requests should pass through."""
        client = TestClient(app, raise_server_exceptions=False)

        with patch("market_data.server.API_KEY", None):
            resp = client.get("/api/v1/tickers")

        assert resp.status_code != 401

    def test_api_key_configured_with_correct_header_returns_200(self) -> None:
        """When API_KEY is set and correct X-API-Key header is provided, request succeeds."""
        from market_data.server import store

        client = TestClient(app, raise_server_exceptions=False)

        with patch("market_data.server.API_KEY", "test-secret-key"):
            with patch("market_data.server.store.status", return_value=[]):
                resp = client.get("/api/v1/tickers", headers={"X-API-Key": "test-secret-key"})

        assert resp.status_code == 200

    def test_api_key_configured_with_wrong_header_returns_401(self) -> None:
        """When API_KEY is set and wrong X-API-Key header is provided, request fails with 401."""
        client = TestClient(app, raise_server_exceptions=False)

        with patch("market_data.server.API_KEY", "test-secret-key"):
            resp = client.get("/api/v1/tickers", headers={"X-API-Key": "wrong-key"})

        assert resp.status_code == 401
        assert resp.json() == {"error": "Invalid or missing API key"}

    def test_api_key_configured_with_missing_header_returns_401(self) -> None:
        """When API_KEY is set and X-API-Key header is missing, request fails with 401."""
        client = TestClient(app, raise_server_exceptions=False)

        with patch("market_data.server.API_KEY", "test-secret-key"):
            resp = client.get("/api/v1/tickers")

        assert resp.status_code == 401
        assert resp.json() == {"error": "Invalid or missing API key"}

    def test_health_endpoint_bypasses_auth(self) -> None:
        """Health endpoint should bypass auth even when API_KEY is set."""
        client = TestClient(app, raise_server_exceptions=False)

        with patch("market_data.server.API_KEY", "test-secret-key"):
            resp = client.get("/health")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_ready_endpoint_bypasses_auth(self) -> None:
        """Ready endpoint should bypass auth even when API_KEY is set."""
        client = TestClient(app, raise_server_exceptions=False)

        with patch("market_data.server.API_KEY", "test-secret-key"):
            resp = client.get("/ready")

        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "data_dir_exists" in data


class TestWebSocketAuth:
    """Test WebSocket endpoint authentication via query parameter."""

    def test_ws_no_api_key_configured_allows_connection(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        with patch("market_data.server.API_KEY", None):
            with client.websocket_connect("/ws/prices") as ws:
                ws.close()

    def test_ws_correct_api_key_allows_connection(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        with patch("market_data.server.API_KEY", "ws-secret"):
            with client.websocket_connect("/ws/prices?api_key=ws-secret") as ws:
                ws.close()

    def test_ws_wrong_api_key_rejects_connection(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        with patch("market_data.server.API_KEY", "ws-secret"):
            try:
                with client.websocket_connect("/ws/prices?api_key=wrong") as ws:
                    ws.close()
                assert False, "Expected WebSocket to be rejected"
            except Exception:
                pass

    def test_ws_missing_api_key_rejects_connection(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        with patch("market_data.server.API_KEY", "ws-secret"):
            try:
                with client.websocket_connect("/ws/prices") as ws:
                    ws.close()
                assert False, "Expected WebSocket to be rejected"
            except Exception:
                pass


class TestSecurityHeaders:
    """Test security response headers are present."""

    def test_response_includes_security_headers(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "X-Request-ID" in resp.headers
