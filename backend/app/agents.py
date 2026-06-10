import json
import re
from typing import List, Dict, Tuple
from pydantic import BaseModel, Field, ConfigDict
from google import genai
from google.genai import types

# Gemini 구조화된 출력을 위한 Pydantic 스키마 정의
class ReadinessSchema(BaseModel):
    is_ready: bool = Field(description="사용자의 기획 요구사항이 웹사이트 코드를 생성하기에 충분히 구체적인 경우 True, 아직 대화가 더 필요한 경우 False")
    summary: str = Field(description="완료된 경우(is_ready가 True인 경우) 웹사이트의 구조, 테마 색상, 구성 요소 등을 요약한 기획 명세서 정보. 완료되지 않은 경우 빈 문자열")

class CodeFile(BaseModel):
    path: str = Field(description="소스코드 파일의 상대 경로 (예: index.html, src/App.jsx, src/index.css)")
    content: str = Field(description="해당 소스코드 파일의 전체 내용")

class DesignSchema(BaseModel):
    framework: str = Field(description="사용자가 요청했거나 가장 적합한 프레임워크 명칭 (vanilla, react, vue)")
    files: List[CodeFile] = Field(description="웹사이트를 구성하는 소스코드 파일 목록")
    preview_html: List[str] = Field(default=[], description="호환성을 위한 미사용 필드 또는 preview_html 문자열 예비 필드")
    preview_html_str: str = Field(alias="preview_html", description="iframe 내에서 실시간으로 직접 렌더링이 가능한 단일 HTML 소스코드 (스타일과 스크립트가 모두 포함된 완성형 페이지)")
    summary: str = Field(description="생성된 웹사이트 디자인 및 기능에 대한 간략한 요약 설명")

    model_config = ConfigDict(populate_by_name=True)


class AgentOrchestrator:
    def __init__(self, api_key: str = None, chat_model: str = "gemini-3.1-flash-lite", design_model: str = "gemini-3.1-flash-lite"):
        self.api_key = api_key
        self.chat_model = chat_model
        self.design_model = design_model
        # 테스트 시 API 키가 없어도 인스턴스 생성이 실패하지 않도록 클라이언트를 필요할 때 지연 로딩함
        self._client = None

    @property
    def client(self):
        if self._client is None:
            # api_key가 제공된 경우에만 인자로 주입하고, 없으면 환경변수(GEMINI_API_KEY)를 사용하도록 인자 없이 호출
            if self.api_key:
                self._client = genai.Client(api_key=self.api_key)
            else:
                self._client = genai.Client()
        return self._client

    def _extract_json(self, text: str) -> dict:
        """구조화된 출력이 마크다운 태그 등에 감싸여 온 경우를 대비해 JSON 블록만 추출하는 파서"""
        text = text.strip()
        # 최초의 '{'와 마지막 '}' 사이의 텍스트 매칭
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return json.loads(text)

    def get_chat_response(self, chat_history: List[Dict[str, str]]) -> str:
        """메인 에이전트를 호출하여 사용자와 대화를 이어가며 기획을 정교화함"""
        system_instruction = (
            "당신은 AI 웹 빌더 서비스의 메인 기획 에이전트입니다. "
            "사용자와 대화하며 사용자가 원하는 웹사이트의 기획(목적, 구조, 디자인 레이아웃, 컬러 테마, 주요 섹션 및 기능 등)을 명확하게 다듬는 역할을 합니다. "
            "한 번에 1~2개씩 질문을 던져 사용자의 답변을 유도하고, 친절하고 전문적인 웹 기획자의 태도를 유지하세요. "
            "요구사항이 모두 정리되었다고 판단되면, 모든 정보가 준비되었으며 이제 웹사이트 디자인 및 코드 생성을 시작하겠다고 사용자에게 안내하십시오."
        )

        # 단순 딕셔너리 히스토리를 Gemini SDK Content 객체 리스트로 변환
        contents = []
        for chat in chat_history:
            role = "user" if chat["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=chat["message"])]
                )
            )

        try:
            response = self.client.models.generate_content(
                model=self.chat_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7
                )
            )
            return response.text
        except Exception as e:
            # 테스트 환경 또는 호출 실패 시의 대체 텍스트 반환
            return f"채팅 모델 호출 중 오류가 발생했습니다: {str(e)}"

    def evaluate_readiness(self, chat_history: List[Dict[str, str]]) -> Tuple[bool, str]:
        """판단 모델을 구조화된 출력(JSON)으로 호출하여 기획 명세가 완료되었는지 체크"""
        prompt = (
            "사용자와 AI 웹 기획 에이전트 간의 아래 대화 내역을 분석해 주세요. "
            "사용자가 요구하는 웹사이트를 코드로 구현하기에 충분한 기획 정보가 수집되었는지 검토해야 합니다. "
            "필수 정보 조건: 웹사이트의 주제/목적, 기본적인 화면 레이아웃 및 섹션 구성(예: 헤더, 메인, 소개, 푸터 등), 그리고 디자인 컬러 톤이나 스타일. "
            "기획이 완료되었다면 is_ready를 true로 설정하고, 정리된 요구사항 명세서를 summary 필드에 구체적으로 한글로 작성해 주세요. "
            "기획 정보가 아직 부족하여 추가적인 대화가 필요하다면 is_ready를 false로 설정하고 summary는 빈 문자열로 두십시오.\n\n"
            "대화 내역:\n"
        )
        for chat in chat_history:
            prompt += f"{chat['role'].upper()}: {chat['message']}\n"

        try:
            response = self.client.models.generate_content(
                model=self.chat_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ReadinessSchema,
                    temperature=0.1
                )
            )
            data = self._extract_json(response.text)
            return bool(data.get("is_ready", False)), data.get("summary", "")
        except Exception as e:
            # 스키마 연동 오류 시 대체 동작 지원
            try:
                data = self._extract_json(response.text)
                return bool(data.get("is_ready", False)), data.get("summary", "")
            except Exception:
                return False, ""

    def generate_design(self, summary: str, framework: str = "vanilla") -> dict:
        """디자인 에이전트를 호출하여 가상 소스코드 파일 및 iframe용 프리뷰 HTML을 한글 기준으로 작성"""
        framework_instructions = {
            "vanilla": (
                "기본적인 HTML/CSS/JS 웹사이트를 생성하십시오. "
                "files 목록에는 최소한 index.html, style.css, script.js 파일이 포함되어야 합니다. "
                "preview_html은 iframe에서 즉시 단독으로 실행될 수 있도록 모든 스타일과 스크립트가 인라인(<style>, <script> 태그)으로 결합된 완성된 단일 HTML 문서 스트링이어야 합니다."
            ),
            "react": (
                "Vite 스타일의 React 웹사이트 소스코드를 생성하십시오. "
                "files 목록에는 src/App.jsx, src/index.css, index.html 등 필요한 모든 소스 파일이 포함되어야 합니다. "
                "preview_html은 iframe 내에서 React 코드의 레이아웃과 동작이 정상적으로 표시될 수 있도록 배포용 형태로 합쳐진 단일 HTML 문서 스트링이어야 합니다. "
                "동작에 필요한 라이브러리가 있다면 CDN 주소를 활용하여 독립 실행이 가능하도록 작성하십시오."
            ),
            "vue": (
                "Vue 3 Single File Component (SFC) 스타일의 프로젝트 소스코드를 생성하십시오. "
                "files 목록에는 src/App.vue, index.html, src/main.js 등 구성에 필요한 파일들이 포함되어야 합니다. "
                "preview_html은 CDN을 통해 Vue 라이브러리를 가져와 렌더링하는 형태로 작성하여 iframe에서 독립적으로 작동하도록 하십시오."
            )
        }

        prompt = (
            "당신은 뛰어난 전문 프론트엔드 개발 에이전트입니다. "
            "다음 기획 명세서를 참고하여 완성도 높고 미려한 웹사이트의 소스코드 파일들을 작성해 주세요.\n\n"
            f"기획 명세서: {summary}\n"
            f"타겟 프레임워크: {framework}\n\n"
            "요구사항:\n"
            "1. 세련되고 트렌디한 모던 디자인을 적용하세요 (HSL 컬러 배합, 그라데이션, 부드러운 호버 애니메이션 및 트랜지션 활용).\n"
            "2. 실무 수준의 깔끔하고 구조화된 코드를 작성하십시오.\n"
            "3. 텍스트 플레이스홀더를 사용하지 말고 실제 사이트 테마에 어울리는 실감나는 한국어 문구와 내용으로 가득 채우십시오.\n"
            f"4. 프레임워크 제약사항: {framework_instructions.get(framework, framework_instructions['vanilla'])}\n"
        )

        try:
            response = self.client.models.generate_content(
                model=self.design_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DesignSchema,
                    temperature=0.2
                )
            )
            data = self._extract_json(response.text)
            return {
                "framework": data.get("framework", framework),
                "files": data.get("files", []),
                "preview_html": data.get("preview_html", ""),
                "summary": data.get("summary", "")
            }
        except Exception as e:
            try:
                data = self._extract_json(response.text)
                return {
                    "framework": data.get("framework", framework),
                    "files": data.get("files", []),
                    "preview_html": data.get("preview_html", ""),
                    "summary": data.get("summary", "")
                }
            except Exception:
                return {
                    "framework": framework,
                    "files": [{"path": "index.html", "content": f"<h1>디자인 생성 중 오류가 발생했습니다: {str(e)}</h1>"}],
                    "preview_html": f"<h1>디자인 생성 중 오류가 발생했습니다: {str(e)}</h1>",
                    "summary": f"생성 실패: {str(e)}"
                }
