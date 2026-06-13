import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    # 테스트용 DB 클라이언트 설정 및 초기화
    from app.db import DatabaseHelper
    from app.routers.sessions import get_db
    db = DatabaseHelper(db_name="test_util_tools")
    db.client.drop_database("test_util_tools")
    
    # FastAPI 의존성을 테스트용 데이터베이스 헬퍼로 오버라이드
    app.dependency_overrides[get_db] = lambda: db
    yield
    db.client.drop_database("test_util_tools")
    app.dependency_overrides.clear()

def test_session_lifecycle():
    # 1. 세션 생성
    resp = client.post("/api/sessions", json={"title": "화장품 쇼핑몰"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["title"] == "화장품 쇼핑몰"
    
    # 2. 세션 목록 조회
    list_resp = client.get("/api/sessions")
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == data["session_id"]

@patch("app.routers.sessions.orchestrator")
def test_chat_interaction_not_ready(mock_orch):
    # 기획 미완료 상태 응답을 주도록 에이전트 모킹
    mock_orch.get_chat_response.return_value = ("좋습니다! 선호하시는 메인 색상이 있으신가요?", False, "")
    
    # 세션 생성
    create_resp = client.post("/api/sessions", json={"title": "내 홈페이지"})
    sess_id = create_resp.json()["session_id"]
    
    # 채팅 전송
    chat_resp = client.post(f"/api/sessions/{sess_id}/chat", json={"message": "쇼핑몰 만들고 싶어"})
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    
    assert chat_data["reply"] == "좋습니다! 선호하시는 메인 색상이 있으신가요?"
    assert chat_data["is_ready"] is False
    assert chat_data["design"] is None
    
    # 채팅 내역 조회 검증
    hist_resp = client.get(f"/api/sessions/{sess_id}/history")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["message"] == "쇼핑몰 만들고 싶어"
    assert history[1]["role"] == "assistant"
    assert history[1]["message"] == "좋습니다! 선호하시는 메인 색상이 있으신가요?"

    # 세션 상세 조회 검증
    detail_resp = client.get(f"/api/sessions/{sess_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["status"] == "CLARIFYING"
    assert detail["progress_message"] == ""

@patch("app.routers.sessions.orchestrator")
def test_chat_interaction_triggers_design(mock_orch):
    # 기획 완료 상태 및 웹 디자인 생성을 진행하도록 에이전트 모킹
    mock_orch.get_chat_response.return_value = ("요구사항이 명확히 수집되었습니다. 웹사이트 생성을 시작합니다!", True, "리액트 기반 핑크 테마 쇼핑몰")
    mock_orch.generate_design.return_value = {
        "framework": "react",
        "files": [
            {"path": "src/App.jsx", "content": "export default function App() {}"}
        ],
        "preview_html": "<h1>핑크 쇼핑몰 메인</h1>",
        "summary": "러블리 핑크 쇼핑몰 코드"
    }
    mock_orch.review_and_correct_design.side_effect = lambda initial_design, summary: initial_design
    
    # 세션 생성
    create_resp = client.post("/api/sessions", json={"title": "화장품 웹숍"})
    sess_id = create_resp.json()["session_id"]
    
    # 기획 완료 조건에 도달하는 채팅 전송
    chat_resp = client.post(f"/api/sessions/{sess_id}/chat", json={"message": "리액트로 핑크색 테마 쇼핑몰 완성해줘"})
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    
    assert chat_data["is_ready"] is True
    assert chat_data["design"] is None  # 백그라운드로 전송되어 즉시 응답 시에는 None
    
    # TestClient의 경우 백그라운드 태스크가 동기적으로 즉시 수행 완료되므로 상태가 COMPLETED로 전환됨
    detail_resp = client.get(f"/api/sessions/{sess_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["status"] == "COMPLETED"
    assert detail["progress_message"] == "완성되었습니다!"
    
    # 디자인 히스토리 내역 조회 검증
    design_resp = client.get(f"/api/sessions/{sess_id}/designs")
    assert design_resp.status_code == 200
    designs = design_resp.json()
    assert len(designs) == 1
    assert designs[0]["version"] == 1
    assert designs[0]["framework"] == "react"

@patch("app.routers.sessions.orchestrator")
def test_chat_with_image(mock_orch):
    mock_orch.get_chat_response.return_value = ("이미지를 확인했습니다.", False, "")
    
    create_resp = client.post("/api/sessions", json={"title": "이미지 인식 세션"})
    sess_id = create_resp.json()["session_id"]
    
    chat_resp = client.post(f"/api/sessions/{sess_id}/chat", json={
        "message": "이 초안대로 디자인해줘",
        "image_data": "dGVzdF9kYXRh",
        "mime_type": "image/png"
    })
    assert chat_resp.status_code == 200
    
    hist_resp = client.get(f"/api/sessions/{sess_id}/history")
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 2
    assert history[0]["image_data"] == "dGVzdF9kYXRh"
    assert history[0]["mime_type"] == "image/png"

