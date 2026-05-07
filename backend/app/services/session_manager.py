import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict
from ..models.schemas import SessionData, ChatMessage

class SessionManager:
    def __init__(self, ttl_hours: int = 24):
        self._sessions: Dict[str, dict] = {}
        self._ttl = timedelta(hours=ttl_hours)

    def create_session(self) -> SessionData:
        session_id = str(uuid.uuid4())
        welcome = ChatMessage(
            role="assistant",
            content="Welcome to NexusIQ Document Fraud Detection! 👋\n\nUpload an invoice PDF to begin fraud analysis.",
            message_type="text",
            timestamp=datetime.now().isoformat()
        )
        session = SessionData(session_id=session_id, chat_history=[welcome])
        self._sessions[session_id] = {
            "data": session,
            "created_at": datetime.now()
        }
        return session

    def get_session(self, session_id: str) -> Optional[SessionData]:
        entry = self._sessions.get(session_id)
        if not entry:
            return None
        if datetime.now() - entry["created_at"] > self._ttl:
            del self._sessions[session_id]
            return None
        return entry["data"]

    def update_session(self, session: SessionData):
        if session.session_id in self._sessions:
            self._sessions[session.session_id]["data"] = session

    def add_message(self, session_id: str, role: str, content: str, message_type: str = "text", data=None):
        session = self.get_session(session_id)
        if session:
            session.chat_history.append(ChatMessage(
                role=role, content=content,
                message_type=message_type, data=data,
                timestamp=datetime.now().isoformat()
            ))
            self.update_session(session)

session_manager = SessionManager()
