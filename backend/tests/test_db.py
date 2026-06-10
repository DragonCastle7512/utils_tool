import pytest
from app.db import DatabaseHelper

@pytest.fixture(scope="module")
def db():
    helper = DatabaseHelper(uri="mongodb://localhost:27017", db_name="test_util_tools")
    yield helper
    # Clean up test database after tests
    helper.client.drop_database("test_util_tools")

def test_database_connection(db):
    assert db.ping() is True

def test_session_lifecycle(db):
    session_id = "test-session-123"
    title = "Test AI Shop Builder"
    
    # 1. Create session
    db.create_session(session_id, title)
    
    # 2. Retrieve session
    session = db.get_session(session_id)
    assert session is not None
    assert session["session_id"] == session_id
    assert session["title"] == title
    assert session["status"] == "CLARIFYING"

def test_chat_lifecycle(db):
    session_id = "test-session-123"
    
    # 1. Insert chat message
    db.save_chat(session_id, "user", "Create a nice portfolio site")
    db.save_chat(session_id, "assistant", "What color theme do you prefer?")
    
    # 2. Retrieve history
    history = db.get_chat_history(session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["message"] == "Create a nice portfolio site"
    assert history[1]["role"] == "assistant"
    assert history[1]["message"] == "What color theme do you prefer?"

def test_design_lifecycle(db):
    session_id = "test-session-123"
    
    files = [
        {"path": "index.html", "content": "<h1>My Portfolio</h1>"},
        {"path": "style.css", "content": "body { background: #fff; }"}
    ]
    preview_html = "<h1>My Portfolio</h1><style>body { background: #fff; }</style>"
    summary = "Vanilla HTML/CSS Portfolio"
    
    # 1. Save design version 1
    db.save_design(session_id, 1, "vanilla", files, preview_html, summary)
    
    # 2. Retrieve designs
    designs = db.get_designs(session_id)
    assert len(designs) == 1
    assert designs[0]["version"] == 1
    assert designs[0]["framework"] == "vanilla"
    assert len(designs[0]["files"]) == 2
    assert designs[0]["preview_html"] == preview_html
    assert designs[0]["summary"] == summary
