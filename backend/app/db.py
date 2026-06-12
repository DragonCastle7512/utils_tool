import os
from datetime import datetime
from pymongo import MongoClient

class DatabaseHelper:
    def __init__(self, uri: str = None, db_name: str = "util_tools"):
        self.uri = uri or os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.client = MongoClient(self.uri)
        self.db = self.client[db_name]

    def ping(self) -> bool:
        """데이터베이스 연결 성공 여부 핑 검사"""
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False

    def create_session(self, session_id: str, title: str):
        """새로운 대화 세션 생성"""
        self.db.sessions.insert_one({
            "session_id": session_id,
            "title": title,
            "status": "CLARIFYING",
            "progress_message": "",
            "created_at": datetime.utcnow()
        })

    def get_session(self, session_id: str) -> dict:
        """특정 세션 정보 단건 조회"""
        return self.db.sessions.find_one({"session_id": session_id})

    def update_session_status(self, session_id: str, status: str):
        """세션의 기획 및 생성 상태 갱신"""
        self.db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": status}}
        )

    def update_progress_message(self, session_id: str, progress_message: str):
        """세션의 실시간 진행률 메시지 갱신"""
        self.db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"progress_message": progress_message}}
        )

    def save_chat(self, session_id: str, role: str, message: str):
        """채팅 내역 단건 기록"""
        self.db.chats.insert_one({
            "session_id": session_id,
            "role": role,
            "message": message,
            "timestamp": datetime.utcnow()
        })

    def get_chat_history(self, session_id: str) -> list:
        """특정 세션의 대화 내역 전체를 시간 순서대로 정렬하여 반환"""
        cursor = self.db.chats.find({"session_id": session_id}).sort("timestamp", 1)
        history = []
        for doc in cursor:
            history.append({
                "role": doc["role"],
                "message": doc["message"],
                "timestamp": doc["timestamp"].isoformat() if "timestamp" in doc else None
            })
        return history

    def save_design(self, session_id: str, version: int, framework: str, files: list, preview_html: str, summary: str):
        """생성된 소스코드 디자인 버전 정보 저장"""
        self.db.designs.insert_one({
            "session_id": session_id,
            "version": version,
            "framework": framework,
            "files": files,
            "preview_html": preview_html,
            "summary": summary,
            "created_at": datetime.utcnow()
        })

    def get_designs(self, session_id: str) -> list:
        """특정 세션에 생성된 소스코드 버전을 리스트 형식으로 순서대로 조회"""
        cursor = self.db.designs.find({"session_id": session_id}).sort("version", 1)
        designs = []
        for doc in cursor:
            designs.append({
                "session_id": doc["session_id"],
                "version": doc["version"],
                "framework": doc["framework"],
                "files": doc["files"],
                "preview_html": doc["preview_html"],
                "summary": doc["summary"],
                "created_at": doc["created_at"].isoformat() if "created_at" in doc else None
            })
        return designs
