import pytest
from app.db import DatabaseHelper

@pytest.fixture(scope="module")
def db():
    helper = DatabaseHelper(uri="mongodb://localhost:27017", db_name="test_util_tools")
    yield helper
    # 테스트 완료 후 테스트용 데이터베이스 삭제
    helper.client.drop_database("test_util_tools")

def test_database_connection(db):
    assert db.ping() is True

def test_session_lifecycle(db):
    session_id = "test-session-123"
    title = "테스트용 AI 쇼핑몰 빌더"
    
    # 1. 세션 생성
    db.create_session(session_id, title)
    
    # 2. 세션 정보 조회 검증
    session = db.get_session(session_id)
    assert session is not None
    assert session["session_id"] == session_id
    assert session["title"] == title
    assert session["status"] == "CLARIFYING"
    assert session["progress_message"] == ""

    # 3. 진행 상황 메시지 업데이트 검증
    db.update_progress_message(session_id, "작업 중...")
    session = db.get_session(session_id)
    assert session["progress_message"] == "작업 중..."

def test_chat_lifecycle(db):
    session_id = "test-session-123"
    
    # 1. 채팅 내역 추가 저장
    db.save_chat(session_id, "user", "멋진 포트폴리오 사이트를 만들어줘")
    db.save_chat(session_id, "assistant", "어떤 컬러 테마를 원하시나요?")
    
    # 2. 대화 기록 목록 조회 검증
    history = db.get_chat_history(session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["message"] == "멋진 포트폴리오 사이트를 만들어줘"
    assert history[1]["role"] == "assistant"
    assert history[1]["message"] == "어떤 컬러 테마를 원하시나요?"

def test_chat_lifecycle_with_image(db):
    session_id = "test-session-image-123"
    db.create_session(session_id, "이미지 테스트")
    db.save_chat(session_id, "user", "초안 참고해줘", image_data="dGVzdF9kYXRh", mime_type="image/png")
    history = db.get_chat_history(session_id)
    assert len(history) == 1
    assert history[0]["image_data"] == "dGVzdF9kYXRh"
    assert history[0]["mime_type"] == "image/png"

def test_design_lifecycle(db):
    session_id = "test-session-123"
    
    files = [
        {"path": "index.html", "content": "<h1>나의 포트폴리오</h1>"},
        {"path": "style.css", "content": "body { background: #fff; }"}
    ]
    preview_html = "<h1>나의 포트폴리오</h1><style>body { background: #fff; }</style>"
    summary = "기본적인 HTML/CSS 포트폴리오"
    
    # 1. 디자인 버전 1 저장
    db.save_design(session_id, 1, "vanilla", files, preview_html, summary)
    
    # 2. 저장된 디자인 목록 조회 검증
    designs = db.get_designs(session_id)
    assert len(designs) == 1
    assert designs[0]["version"] == 1
    assert designs[0]["framework"] == "vanilla"
    assert len(designs[0]["files"]) == 2
    assert designs[0]["preview_html"] == preview_html
    assert designs[0]["summary"] == summary
