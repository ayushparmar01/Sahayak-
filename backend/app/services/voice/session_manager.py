"""Session-scoped in-memory conversation state manager for SAHAYAK Voice Assistant.

Ensures strict privacy isolation and full memory wipe upon session termination (kiosk purge).
Zero long-term audio or transcript persistence.
"""
from typing import Any
from datetime import datetime, timezone


class VoiceSessionState:
    """Session-scoped volatile state for a citizen voice interaction."""

    def __init__(self, session_id: str, citizen_id: str, language: str = "hi"):
        self.session_id = session_id
        self.citizen_id = citizen_id
        self.language = language
        self.turn_count = 0
        self.max_turns = 15
        self.proposed_profile_updates: dict[str, Any] = {}
        self.last_asked_field: str | None = None
        self.skipped_fields: list[str] = []
        self.last_follow_up_hi: str | None = None
        self.last_follow_up_en: str | None = None
        self.history: list[dict[str, Any]] = []
        self.last_activity = datetime.now(timezone.utc)

    def record_turn(self, user_text: str, assistant_text: str, updates: dict[str, Any]):
        self.turn_count += 1
        self.last_activity = datetime.now(timezone.utc)
        self.history.append({
            "turn": self.turn_count,
            "user": user_text,
            "assistant": assistant_text,
            "updates": updates,
            "timestamp": self.last_activity.isoformat(),
        })
        # Keep only last 5 turns to minimize in-memory footprint
        if len(self.history) > 5:
            self.history = self.history[-5:]


class VoiceSessionManager:
    """Registry maintaining active voice session states."""

    _sessions: dict[str, VoiceSessionState] = {}

    @classmethod
    def get_or_create(cls, session_id: str, citizen_id: str, language: str = "hi") -> VoiceSessionState:
        # Opportunistic cleanup sweep: purge sessions idle for more than 1800s (30 mins)
        cls.cleanup_expired(max_idle_seconds=1800)
        if session_id not in cls._sessions:
            cls._sessions[session_id] = VoiceSessionState(
                session_id=session_id,
                citizen_id=citizen_id,
                language=language,
            )
        state = cls._sessions[session_id]
        state.language = language
        return state

    @classmethod
    def get(cls, session_id: str) -> VoiceSessionState | None:
        return cls._sessions.get(session_id)

    @classmethod
    def clear_session(cls, session_id: str) -> bool:
        """Purges volatile voice session memory completely."""
        if session_id in cls._sessions:
            del cls._sessions[session_id]
            return True
        return False

    @classmethod
    def cleanup_expired(cls, max_idle_seconds: int = 1800) -> int:
        """Purges sessions inactive for more than max_idle_seconds to prevent memory leaks."""
        now = datetime.now(timezone.utc)
        expired_keys = [
            sid for sid, s in cls._sessions.items()
            if (now - s.last_activity).total_seconds() > max_idle_seconds
        ]
        for sid in expired_keys:
            del cls._sessions[sid]
        return len(expired_keys)

    @classmethod
    def active_session_count(cls) -> int:
        return len(cls._sessions)
