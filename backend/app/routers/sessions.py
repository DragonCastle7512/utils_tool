import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
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

class SessionDetailResponse(BaseModel):
    session_id: str
    title: str
    status: str
    progress_message: str

class ChatReq(BaseModel):
    message: str
    framework: Optional[str] = "vanilla"
    image_data: Optional[str] = None
    mime_type: Optional[str] = None

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
    image_data: Optional[str] = None
    mime_type: Optional[str] = None
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

def generate_and_review_design_task(session_id: str, summary: str, framework: str, db_name: str = "util_tools"):
    db = DatabaseHelper(db_name=db_name)
    try:
        db.update_progress_message(session_id, "디자인 에이전트가 1차 코드를 작성 중입니다...")
        initial_design = orchestrator.generate_design(summary, framework)
        
        db.update_progress_message(session_id, "검토 에이전트가 소스코드를 리팩토링 및 검수 중입니다...")
        generated_design = orchestrator.review_and_correct_design(initial_design, summary)
        
        existing_designs = db.get_designs(session_id)
        next_version = len(existing_designs) + 1
        db.save_design(
            session_id=session_id,
            version=next_version,
            framework=generated_design["framework"],
            files=generated_design["files"],
            preview_html=generated_design["preview_html"],
            summary=generated_design["summary"]
        )
        
        db.update_session_status(session_id, "COMPLETED")
        db.update_progress_message(session_id, "완성되었습니다!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        db.update_session_status(session_id, "FAILED")
        db.update_progress_message(session_id, f"오류 발생: {str(e)}")

@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_session_details(session_id: str, db: DatabaseHelper = Depends(get_db)):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    return SessionDetailResponse(
        session_id=session["session_id"],
        title=session["title"],
        status=session["status"],
        progress_message=session.get("progress_message", "")
    )

@router.post("/{session_id}/chat", response_model=ChatResponse)
def chat(session_id: str, req: ChatReq, background_tasks: BackgroundTasks, db: DatabaseHelper = Depends(get_db)):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    # 1. 사용자 채팅 내용 DB 저장
    db.save_chat(session_id, "user", req.message, req.image_data, req.mime_type)

    # 2. 전체 대화 기록 컨텍스트 조회
    history = db.get_chat_history(session_id)

    # 3. 메인 에이전트(기획)를 호출하여 답변 및 기획 완료 여부, 그리고 자동 판별된 프레임워크 확인
    reply, is_ready, summary, detected_framework = orchestrator.get_chat_response(history)
    db.save_chat(session_id, "assistant", reply)

    if is_ready:
        # 세션 상태를 'DESIGNING(디자인중)'으로 변경
        db.update_session_status(session_id, "DESIGNING")
        db.update_progress_message(session_id, "디자인 에이전트 가동을 준비 중입니다...")

        # 백그라운드 태스크 등록
        background_tasks.add_task(generate_and_review_design_task, session_id, summary, detected_framework, db.db.name)
    else:
        # 기획 미완료 상태인 경우 상태를 'CLARIFYING'으로 유지
        db.update_session_status(session_id, "CLARIFYING")

    return ChatResponse(
        reply=reply,
        is_ready=is_ready,
        design=None
    )

@router.get("/{session_id}/history", response_model=List[ChatHistoryResponse])
def get_chat_history(session_id: str, db: DatabaseHelper = Depends(get_db)):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    history = db.get_chat_history(session_id)
    return [
        ChatHistoryResponse(
            role=h["role"],
            message=h["message"],
            image_data=h.get("image_data"),
            mime_type=h.get("mime_type"),
            timestamp=h["timestamp"]
        )
        for h in history
    ]

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
