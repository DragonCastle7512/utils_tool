import pytest
from unittest.mock import MagicMock, patch
from app.agents import AgentOrchestrator

@pytest.fixture
def orchestrator():
    return AgentOrchestrator(api_key="mock_api_key")

@patch("app.agents.genai.Client")
def test_get_chat_response(mock_genai_client_class, orchestrator):
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client
    
    # Gemini로부터 텍스트 응답을 받는 경우 모킹
    mock_response = MagicMock()
    mock_response.text = "안녕하세요! AI 웹 기획 에이전트입니다. 어떤 홈페이지를 제작하고 싶으신가요?"
    mock_client.models.generate_content.return_value = mock_response
    
    history = [{"role": "user", "message": "안녕"}]
    reply = orchestrator.get_chat_response(history)
    
    assert reply == "안녕하세요! AI 웹 기획 에이전트입니다. 어떤 홈페이지를 제작하고 싶으신가요?"
    mock_client.models.generate_content.assert_called_once()

@patch("app.agents.genai.Client")
def test_evaluate_readiness_not_ready(mock_genai_client_class, orchestrator):
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client
    
    # 기획 미완료 상태의 구조화된 JSON 응답 모킹
    mock_response = MagicMock()
    mock_response.text = '{"is_ready": false, "summary": ""}'
    mock_client.models.generate_content.return_value = mock_response
    
    history = [{"role": "user", "message": "쇼핑몰 만들래"}]
    is_ready, summary = orchestrator.evaluate_readiness(history)
    
    assert is_ready is False
    assert summary == ""

@patch("app.agents.genai.Client")
def test_evaluate_readiness_ready(mock_genai_client_class, orchestrator):
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client
    
    # 기획 완료 상태의 구조화된 JSON 응답 모킹
    mock_response = MagicMock()
    mock_response.text = '{"is_ready": true, "summary": "리액트 기반 쇼핑몰, 핑크 테마, 메인페이지 3개 섹션 구성"}'
    mock_client.models.generate_content.return_value = mock_response
    
    history = [{"role": "user", "message": "리액트로 핑크 테마 쇼핑몰 만들어줘. 메인/상품/푸터로 구성해줘."}]
    is_ready, summary = orchestrator.evaluate_readiness(history)
    
    assert is_ready is True
    assert summary == "리액트 기반 쇼핑몰, 핑크 테마, 메인페이지 3개 섹션 구성"

@patch("app.agents.genai.Client")
def test_generate_design(mock_genai_client_class, orchestrator):
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client
    
    # 가상 코드 파일 및 프리뷰 HTML 생성 마크다운 응답 모킹
    mock_response = MagicMock()
    mock_response.text = '''
[FRAMEWORK]: react
[SUMMARY]: 러블리 핑크 쇼핑몰 완성본

[FILE]: src/App.jsx
```jsx
export default function App() { return <h1>핑크 쇼핑몰</h1>; }
```

[FILE]: preview.html
```html
<h1>핑크 쇼핑몰</h1>
```
'''
    mock_client.models.generate_content.return_value = mock_response
    
    design = orchestrator.generate_design("리액트 기반 쇼핑몰, 핑크 테마, 메인페이지 3개 섹션 구성", "react")
    
    assert design["framework"] == "react"
    assert design["files"][0]["path"] == "src/App.jsx"
    assert "핑크 쇼핑몰" in design["preview_html"]

@patch("app.agents.genai.Client")
def test_review_and_correct_design(mock_genai_client_class, orchestrator):
    mock_client = MagicMock()
    mock_genai_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = '''
[FRAMEWORK]: react
[SUMMARY]: 러블리 핑크 쇼핑몰 완성본 (검토 완료)

[FILE]: src/App.jsx
```jsx
export default function App() { return <h1>핑크 쇼핑몰 (검토 완료)</h1>; }
```

[FILE]: preview.html
```html
<h1>핑크 쇼핑몰 (검토 완료)</h1>
```
'''
    mock_client.models.generate_content.return_value = mock_response
    
    initial_design = {
        "framework": "react",
        "files": [
            {"path": "src/App.jsx", "content": "export default function App() { return <h1>핑크 쇼핑몰</h1>; }"},
            {"path": "preview.html", "content": "<h1>핑크 쇼핑몰</h1>"}
        ]
    }
    
    corrected_design = orchestrator.review_and_correct_design(initial_design, "리액트 기반 쇼핑몰, 핑크 테마, 메인페이지 3개 섹션 구성")
    
    assert corrected_design["framework"] == "react"
    assert corrected_design["files"][0]["path"] == "src/App.jsx"
    assert "핑크 쇼핑몰 (검토 완료)" in corrected_design["preview_html"]

def test_inline_resources(orchestrator):
    files = [
        {"path": "style.css", "content": "body { background: black; }"},
        {"path": "script.js", "content": "console.log('hello');"},
        {"path": "index.html", "content": '<html><head><link rel="stylesheet" href="style.css"></head><body><h1>Test</h1><script src="script.js"></script></body></html>'}
    ]
    raw_html = files[2]["content"]
    
    inlined_html = orchestrator._inline_resources("vanilla", files, raw_html)
    
    assert "<style>\nbody { background: black; }\n</style>" in inlined_html
    assert "<script>\nconsole.log('hello');\n</script>" in inlined_html
    assert '<link rel="stylesheet"' not in inlined_html
    assert 'src="script.js"' not in inlined_html
