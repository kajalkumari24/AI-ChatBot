_SESSIONS: dict[str, list[dict]] = {}


def get_history(session_id: str) -> list[dict]:
    return _SESSIONS.get(session_id, [])


def append_message(session_id: str, role: str, content: str) -> None:
    _SESSIONS.setdefault(session_id, []).append({"role": role, "content": content})


def clear_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
