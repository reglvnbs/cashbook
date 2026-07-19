from __future__ import annotations

import json


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_ai_parse_returns_editable_drafts_without_writing(
    client, csrf_headers, monkeypatch
):
    model_output = {
        "transactions": [
            {
                "transaction_type": "expense",
                "amount": "32.00",
                "category_id": 1,
                "occurred_on": "2026-01-15",
                "note": "午饭",
            }
        ]
    }
    api_output = {
        "choices": [{"message": {"content": json.dumps(model_output, ensure_ascii=False)}}]
    }
    monkeypatch.setattr(
        "app.services.ai_service.urlopen", lambda *_args, **_kwargs: FakeResponse(api_output)
    )
    response = client.post(
        "/api/ai/parse", json={"text": "1 月 15 日午饭 32 元"}, headers=csrf_headers
    )
    assert response.status_code == 200
    assert response.json["data"]["drafts"][0]["amount"] == "32.00"
    assert client.get("/api/transactions").json["data"]["pagination"]["total_items"] == 0


def test_ai_invalid_response_is_stable_error(client, csrf_headers, monkeypatch):
    api_output = {"choices": [{"message": {"content": "not json"}}]}
    monkeypatch.setattr(
        "app.services.ai_service.urlopen", lambda *_args, **_kwargs: FakeResponse(api_output)
    )
    response = client.post(
        "/api/ai/parse", json={"text": "午饭 32 元"}, headers=csrf_headers
    )
    assert response.status_code == 503
    assert response.json["error"]["code"] == "AI_INVALID_RESPONSE"

