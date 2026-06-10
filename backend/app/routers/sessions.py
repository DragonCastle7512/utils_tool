import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.db import DatabaseHelper
from app.agents import AgentOrchestrator

router = APIRouter(prefix="/api/sessions")
orchestrator = AgentOrchestrator()

# 데이터베이스 헬퍼 의존성 주입 함수
def get_db():
    return DatabaseHelper()

# 요청/응답용 Pydantic 스키마 정의
class CreateSessionReq(BaseModel):
    title: str

class SessionResponse(BaseModel):
    session_id: str
    title: str
    status: str

class ChatReq(BaseModel):
    message: str
    framework: Optional[str] = "vanilla"

class CodeFileResponse(BaseModel):
    path: str
    content: str

class DesignResponse(BaseModel):
    version: int
    framework: str
    files: List[CodeFileResponse]
    preview_html: str
    summary: str

class ChatResponse(BaseModel):
    reply: str
    is_ready: bool
    design: Optional[DesignResponse] = None

class ChatHistoryResponse(BaseModel):
    role: str
    message: str
    timestamp: Optional[str] = None

@router.post("", response_model=SessionResponse)
def create_session(req: CreateSessionReq, db: DatabaseHelper = Depends(get_db)):
    session_id = str(uuid.uuid4())
    db.create_session(session_id, req.title)
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=500, detail="세션 생성에 실패했습니다.")
    return SessionResponse(
        session_id=session["session_id"],
        title=session["title"],
        status=session["status"]
    )

@router.get("", response_model=List[SessionResponse])
def list_sessions(db: DatabaseHelper = Depends(get_db)):
    cursor = db.db.sessions.find().sort("created_at", -1)
    sessions = []
    for doc in cursor:
        sessions.append(SessionResponse(
            session_id=doc["session_id"],
            title=doc["title"],
            status=doc["status"]
        ))
    return sessions

@router.post("/{session_id}/chat", response_model=ChatResponse)
def chat(session_id: str, req: ChatReq, db: DatabaseHelper = Depends(get_db)):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    # 1. 사용자 채팅 내용 DB 저장
    db.save_chat(session_id, "user", req.message)

    # 2. 전체 대화 기록 컨텍스트 조회
    history = db.get_chat_history(session_id)

    # 3. 메인 에이전트(기획)를 호출하여 대화 답변 생성
    reply = orchestrator.get_chat_response(history)
    db.save_chat(session_id, "assistant", reply)

    # 4. 판단기에 전달할 최종 대화 기록 최신화
    updated_history = db.get_chat_history(session_id)

    # 5. 기획이 완료되어 웹사이트 생성이 가능한지 판별
    is_ready, summary = orchestrator.evaluate_readiness(updated_history)

    design_data = None
    if is_ready:
        # 세션 상태를 'DESIGNING(디자인중)'으로 변경
        db.update_session_status(session_id, "DESIGNING")

        # 생성될 소스코드 디자인 버전 번호 계산
        existing_designs = db.get_designs(session_id)
        next_version = len(existing_designs) + 1

        # 디자인 에이전트를 가동하여 소스코드 파일 트리 및 프리뷰용 단일 HTML 생성
        generated_design = orchestrator.generate_design(summary, req.framework)

        # DB 저장
        db.save_design(
            session_id=session_id,
            version=next_version,
            framework=generated_design["framework"],
            files=generated_design["files"],
            preview_html=generated_design["preview_html"],
            summary=generated_design["summary"]
        )

        # 세션 상태를 'COMPLETED(기획/디자인 완료)'로 변경
        db.update_session_status(session_id, "COMPLETED")

        design_data = DesignResponse(
            version=next_version,
            framework=generated_design["framework"],
            files=[CodeFileResponse(path=f["path"], content=f["content"]) for f in generated_design["files"]],
            preview_html=generated_design["preview_html"],
            summary=generated_design["summary"]
        )
    else:
        # 기획 미완료 상태인 경우 상태를 'CLARIFYING(대화기획중)'으로 유지
        db.update_session_status(session_id, "CLARIFYING")

    return ChatResponse(
        reply=reply,
        is_ready=is_ready,
        design=design_data
    )

@router.get("/{session_id}/history", response_model=List[ChatHistoryResponse])
def get_chat_history(session_id: str, db: DatabaseHelper = Depends(get_db)):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    history = db.get_chat_history(session_id)
    return [ChatHistoryResponse(role=h["role"], message=h["message"], timestamp=h["timestamp"]) for h in history]

@router.get("/{session_id}/designs", response_model=List[DesignResponse])
def get_designs(session_id: str, db: DatabaseHelper = Depends(get_db)):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    designs = db.get_designs(session_id)
    return [
        DesignResponse(
            version=d["version"],
            framework=d["framework"],
            files=[CodeFileResponse(path=f["path"], content=f["content"]) for f in d["files"]],
            preview_html=d["preview_html"],
            summary=d["summary"]
        )
        for d in designs
    ]
