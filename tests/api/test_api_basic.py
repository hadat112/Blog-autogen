from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("app/services/json"):
        assert response.json() == {"status": "ok"}
    else:
        assert "<div id=\"root\"></div>" in response.text
