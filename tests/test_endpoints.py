"""
Phase 3 — API endpoint tests
-----------------------------
Run with:  pytest tests/test_endpoints.py -v
"""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ── /health ───────────────────────────────────────────────────────────────────

class TestHealthEndpoint:

    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_response_has_status_key(self):
        data = client.get("/health").json()
        assert "status" in data


# ── / (root) ──────────────────────────────────────────────────────────────────

class TestRootEndpoint:

    def test_root_returns_200(self):
        assert client.get("/").status_code == 200

    def test_root_contains_service_name(self):
        data = client.get("/").json()
        assert "service" in data

    def test_root_lists_endpoints(self):
        data = client.get("/").json()
        assert "endpoints" in data
        assert "/health" in data["endpoints"]
        assert "/chat" in data["endpoints"]


# ── POST /chat — schema validation ────────────────────────────────────────────

class TestChatSchemaValidation:

    def test_valid_single_user_message(self):
        payload = {"messages": [{"role": "user", "content": "I need an assessment"}]}
        response = client.post("/chat", json=payload)
        assert response.status_code == 200

    def test_response_has_required_fields(self):
        payload = {"messages": [{"role": "user", "content": "I need an assessment"}]}
        data = client.post("/chat", json=payload).json()
        assert "reply" in data
        assert "recommendations" in data
        assert "end_of_conversation" in data

    def test_reply_is_non_empty_string(self):
        payload = {"messages": [{"role": "user", "content": "Hello"}]}
        data = client.post("/chat", json=payload).json()
        assert isinstance(data["reply"], str)
        assert len(data["reply"]) > 0

    def test_recommendations_is_list(self):
        payload = {"messages": [{"role": "user", "content": "Hello"}]}
        data = client.post("/chat", json=payload).json()
        assert isinstance(data["recommendations"], list)

    def test_end_of_conversation_is_bool(self):
        payload = {"messages": [{"role": "user", "content": "Hello"}]}
        data = client.post("/chat", json=payload).json()
        assert isinstance(data["end_of_conversation"], bool)

    def test_invalid_role_returns_422(self):
        payload = {"messages": [{"role": "system", "content": "Hello"}]}
        assert client.post("/chat", json=payload).status_code == 422

    def test_empty_content_returns_422(self):
        payload = {"messages": [{"role": "user", "content": ""}]}
        assert client.post("/chat", json=payload).status_code == 422

    def test_empty_messages_list_returns_422(self):
        payload = {"messages": []}
        assert client.post("/chat", json=payload).status_code == 422

    def test_missing_messages_key_returns_422(self):
        assert client.post("/chat", json={}).status_code == 422

    def test_max_7_history_messages_accepted(self):
        messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(7)
        ]
        assert client.post("/chat", json={"messages": messages}).status_code == 200

    def test_8_history_messages_returns_422_to_prevent_ninth_message(self):
        messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(8)
        ]
        assert client.post("/chat", json={"messages": messages}).status_code == 422

    def test_multi_turn_conversation(self):
        messages = [
            {"role": "user", "content": "I need a programming skills test"},
            {"role": "assistant", "content": "What language?"},
            {"role": "user", "content": "Java"},
        ]
        response = client.post("/chat", json={"messages": messages})
        assert response.status_code == 200

    def test_missing_role_field_returns_422(self):
        payload = {"messages": [{"content": "Hello"}]}
        assert client.post("/chat", json=payload).status_code == 422

    def test_missing_content_field_returns_422(self):
        payload = {"messages": [{"role": "user"}]}
        assert client.post("/chat", json=payload).status_code == 422


# ── RecommendationItem schema ─────────────────────────────────────────────────

class TestRecommendationItemSchema:
    """
    When recommendations are returned, each item must conform to the
    RecommendationItem schema: name (str), url (shl.com), test_type ([A-Z0-9]{1,3}).
    """

    def _get_recommendations(self, content="I need to assess Java developers"):
        payload = {
            "messages": [
                {"role": "user", "content": content},
                {"role": "assistant", "content": "What seniority level?"},
                {"role": "user", "content": "Mid-level senior engineers"},
                {"role": "assistant", "content": "Any specific frameworks?"},
                {"role": "user", "content": "Spring Boot and REST APIs"},
            ]
        }
        return client.post("/chat", json=payload).json().get("recommendations", [])

    def test_recommendation_url_starts_with_shl(self):
        recs = self._get_recommendations()
        for rec in recs:
            assert rec["url"].startswith("https://www.shl.com"), (
                f"Invalid URL: {rec['url']}"
            )

    def test_recommendation_has_name(self):
        recs = self._get_recommendations()
        for rec in recs:
            assert rec["name"] and len(rec["name"]) > 0

    def test_recommendation_has_test_type(self):
        recs = self._get_recommendations()
        for rec in recs:
            assert rec["test_type"] and len(rec["test_type"]) <= 3

    def test_max_10_recommendations(self):
        recs = self._get_recommendations()
        assert len(recs) <= 10


# ── Non-chat HTTP methods ─────────────────────────────────────────────────────

class TestMethodNotAllowed:

    def test_post_to_health_returns_405(self):
        assert client.post("/health").status_code == 405

    def test_get_to_chat_returns_405(self):
        assert client.get("/chat").status_code == 405

    def test_put_to_chat_returns_405(self):
        assert client.put("/chat", json={}).status_code == 405


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
