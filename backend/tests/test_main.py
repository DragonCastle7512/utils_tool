from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    # FastAPI 서버가 정상적으로 켜져 있고 통신 가능한지 검증하는 테스트
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
