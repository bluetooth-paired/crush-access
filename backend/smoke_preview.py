"""Exercise the local preview using only the bundled fictional chat."""

import json
from pathlib import Path

import httpx


def main():
    fixture = Path(__file__).parent / "tests" / "fixtures" / "fictional_chat.json"
    conversation = json.loads(fixture.read_text(encoding="utf-8"))
    with httpx.Client(base_url="http://127.0.0.1:8010", trust_env=False, timeout=20) as client:
        health = client.get("/health").raise_for_status().json()
        assert health["model"]["provider"] == "local-preview"
        report = client.post("/api/v1/analyze", json={"conversation": conversation}).raise_for_status().json()
        assert report["data_quality"]["total_messages"] == len(conversation["messages"])
        context = {"analysis_id": report["analysis_id"], "client_id": report["client_id"]}
        first = client.post(
            "/api/v1/advisor/chat", json={**context, "message": "周末怎么约比较自然？"}
        ).raise_for_status().json()
        second = client.post(
            "/api/v1/advisor/chat",
            json={**context, "session_id": first["session_id"], "message": "对方不方便怎么办？"},
        ).raise_for_status().json()
        assert [first["turn"], second["turn"]] == [1, 2]
        assert first["session_id"] == second["session_id"]
        assert all("预览" in response["reply"] for response in (first, second))
        print("Preview API passed: health, analysis, advisor turns 1 and 2.")


if __name__ == "__main__":
    main()
