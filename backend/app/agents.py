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
    def __init__(self, api_key: str = None, chat_model: str = "gemma-4-26b-a4b-it", design_model: str = "gemma-4-26b-a4b-it"):
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
            "당신은 실무 경력 10년 이상의 수석 프론트엔드 UI/UX 엔지니어이자 최고 수준의 디지털 디자이너 에이전트입니다. "
            "단순하고 뻔한 인공지능 스타일의 양산형 UI 디자인(하얀 배경에 보라색 그라데이션 카드 그리드, 획일화된 레이아웃 등)을 극도로 지양하며, "
            "독창적이고 완성도 높은 최상급의 프론트엔드 코드셋을 작성해야 합니다.\n\n"
            
            f"[기획 명세서]:\n{summary}\n"
            f"[타겟 프레임워크]: {framework}\n\n"
            
            "웹사이트 생성 시 반드시 준수해야 하는 [디자인 및 엔지니어링 지침]:\n\n"
            
            "1. 컨셉추얼한 비주얼 테마 설정 (Aesthetic Point-of-View)\n"
            "   - 명세서의 주제에 가장 어울리는 과감하고 독창적인 디자인 스타일을 하나 선택해 일관성 있게 구현하세요.\n"
            "   - 디자인 스타일 예시: 미니멀리즘(Brutally Minimal), 레트로 퓨처리즘(Retro-futuristic), 편집샵 잡지 레이아웃(Editorial/Magazine), 오가닉/내추럴(Organic/Natural), 프리미엄 하이엔드/럭셔리(Luxury/Refined), 인더스트리얼(Industrial/Utilitarian) 등.\n"
            "   - 모든 색상, 경계선 둥글기(border-radius), 여백 비율은 선택한 컨셉의 톤앤매너에 맞게 정밀하게 조정하세요.\n\n"
            
            "2. 타이포그래피 설계 및 폰트 페어링 (Typography)\n"
            "   - 브라우저 기본 폰트나 단순 Inter, Arial 같은 식상한 폰트를 쓰지 마세요.\n"
            "   - Google Fonts에서 제목용 개성 있는 디스플레이/세리프 폰트(예: Playfair Display, Cormorant Garamond, Syne, Space Grotesk, Cabinet Grotesk, DM Serif 등)와 본문용 가독성 좋은 산세리프 폰트를 CSS `@import` 또는 `<link>` 태그로 로드하여 조합해 사용하세요.\n"
            "   - 글자 크기(Heading 1~6, Body, Small)의 위계질서(Hierarchy)를 뚜렷하게 설정하세요.\n\n"
            
            "3. 레이아웃의 입체감과 깊이 설계 (Layout & Visual Depth)\n"
            "   - 평평하고 심심한 단색 배경 대신, CSS 그라데이션 메쉬(Gradient Mesh), 미세한 미디엄 노이즈 효과, 그리드 패턴 배경, 투명 레이어링(backdrop-filter: blur), 입체적인 그림자(dramatic box-shadows) 등을 사용해 고급스러운 분위기를 연출하세요.\n"
            "   - 뻔한 카드 격자 배열을 피하고, 비대칭 배치(Asymmetry), 겹침 효과(Overlap), 대각선 흐름(Diagonal Flow), 그리드를 살짝 벗어나는 요소들을 도입해 리듬감 있는 배치를 구성하세요.\n\n"
            
            "4. 모션 및 인터랙션 디테일 (Motion & Micro-interactions)\n"
            "   - 웹페이지 로드 시 요소들이 시간 차(animation-delay)를 두고 서서히 떠오르는 스태거드 페이드인(Staggered reveal) CSS 애니메이션을 적용하세요.\n"
            "   - 모든 버튼과 인터랙티브 요소에는 마우스를 올렸을 때 부드러운 스케일 변화, 컬러 페이딩, 화살표 밀림 등 매력적인 호버 상태를 부여하세요.\n\n"
            
            "5. 실무 수준의 시맨틱 마크업 및 접근성 (Semantic HTML & Engineering)\n"
            "   - 의미 있는 HTML5 시맨틱 태그(<header>, <nav>, <main>, <section>, <article>, <footer>)를 올바르게 계층화해 작성하세요.\n"
            "   - 320px(모바일)부터 768px(태블릿), 1024px, 1440px(데스크톱)까지 레이아웃이 깨지지 않고 부드럽게 반응하는 완전 반응형 웹 디자인을 구성하세요.\n"
            "   - 임의의 픽셀값(예: 13px, 29px)을 남발하지 말고 4px/8px 배수 단위(0.25rem, 0.5rem, 1rem 등)의 규칙적인 Spacing Scale을 유지하세요.\n"
            "   - 스크린 리더와 키보드 접근성을 위해 적합한 ARIA 어트리뷰트(aria-label, role)를 지정하세요.\n\n"
            
            "6. 텍스트 플레이스홀더 배제 및 가독성 높은 콘텐츠\n"
            "   - 'Lorem Ipsum'이나 '여기에 텍스트 입력'과 같은 무의미한 플레이스홀더를 절대 사용하지 마세요.\n"
            "   - 생성 대상 서비스의 비즈니스 목적에 완벽하게 부합하고, 기획 감성을 자극하는 실감나고 전문적인 **한국어 카피라이팅** 문구들로 모든 텍스트를 정성스레 채워 넣으십시오.\n\n"
            
            f"[프레임워크별 소스코드 구조화 제약사항]:\n{framework_instructions.get(framework, framework_instructions['vanilla'])}\n"
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
