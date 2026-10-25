from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["supabase"] == "memory"
