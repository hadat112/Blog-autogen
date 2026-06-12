from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("text/html"):
        assert '<div id="root"></div>' in response.text
    else:
        assert response.json() == {"status": "ok"}
