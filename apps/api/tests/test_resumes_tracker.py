from fastapi.testclient import TestClient

from tests.conftest import RESUME_TEXT


def test_resume_crud(client: TestClient) -> None:
    res = client.post(
        "/resumes",
        json={"title": "Primary", "content": RESUME_TEXT, "skills": ["Python", "LLM"]},
    )
    assert res.status_code == 200
    rid = res.json()["id"]

    listed = client.get("/resumes")
    assert listed.status_code == 200
    assert any(r["id"] == rid for r in listed.json())

    got = client.get(f"/resumes/{rid}")
    assert got.status_code == 200
    assert "Python" in got.json()["content"]

    deleted = client.delete(f"/resumes/{rid}")
    assert deleted.status_code == 200


def test_tracker_crud(client: TestClient) -> None:
    res = client.post(
        "/tracker",
        json={
            "job_id": "j1",
            "title": "AI Engineer",
            "company": "Acme",
            "apply_url": "https://himalayas.app/jobs/1",
            "source": "Himalayas",
            "status": "saved",
            "score": 88,
        },
    )
    assert res.status_code == 200
    item_id = res.json()["id"]

    listed = client.get("/tracker")
    assert any(i["id"] == item_id for i in listed.json())

    patched = client.patch(f"/tracker/{item_id}", json={"status": "applied"})
    assert patched.status_code == 200
    assert patched.json()["status"] == "applied"

    client.delete(f"/tracker/{item_id}")
