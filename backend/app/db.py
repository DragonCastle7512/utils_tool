import os
from datetime import datetime
from pymongo import MongoClient

class DatabaseHelper:
    def __init__(self, uri: str = None, db_name: str = "util_tools"):
        self.uri = uri or os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.client = MongoClient(self.uri)
        self.db = self.client[db_name]

    def ping(self) -> bool:
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False

    def create_session(self, session_id: str, title: str):
        self.db.sessions.insert_one({
            "session_id": session_id,
            "title": title,
            "status": "CLARIFYING",
            "created_at": datetime.utcnow()
        })

    def get_session(self, session_id: str) -> dict:
        return self.db.sessions.find_one({"session_id": session_id})

    def update_session_status(self, session_id: str, status: str):
        self.db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": status}}
        )

    def save_chat(self, session_id: str, role: str, message: str):
        self.db.chats.insert_one({
            "session_id": session_id,
            "role": role,
            "message": message,
            "timestamp": datetime.utcnow()
        })

    def get_chat_history(self, session_id: str) -> list:
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
