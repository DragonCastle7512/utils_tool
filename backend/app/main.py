from dotenv import load_dotenv
# .env 파일로부터 환경 변수 로드
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.sessions import router as sessions_router

# FastAPI 앱 객체 초기화
app = FastAPI(title="Util Tools API")

# 크로스 도메인 자원 공유(CORS) 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 세션 및 채팅 라우터 등록
app.include_router(sessions_router)

@app.get("/health")
def health():
    """서버 헬스 체크 엔드포인트"""
    return {"status": "ok"}
