"""Unit tests for SessionManager — no external dependencies."""
import pytest
from session_manager import SessionManager, Message


class TestCreateSession:
    def test_returns_string_id(self):
        sm = SessionManager()
        sid = sm.create_session()
        assert isinstance(sid, str)

    def test_first_session_id(self):
        sm = SessionManager()
        assert sm.create_session() == "session_1"

    def test_increments_on_each_call(self):
        sm = SessionManager()
        sid1 = sm.create_session()
        sid2 = sm.create_session()
        assert sid1 != sid2
        assert sid2 == "session_2"

    def test_initialises_empty_message_list(self):
        sm = SessionManager()
        sid = sm.create_session()
        assert sm.sessions[sid] == []


class TestAddMessage:
    def test_appends_message_to_session(self):
        sm = SessionManager()
        sid = sm.create_session()
        sm.add_message(sid, "user", "Hello")
        assert len(sm.sessions[sid]) == 1
        assert sm.sessions[sid][0].role == "user"
        assert sm.sessions[sid][0].content == "Hello"

    def test_creates_session_if_missing(self):
        sm = SessionManager()
        sm.add_message("ghost_session", "user", "Hi")
        assert "ghost_session" in sm.sessions

    def test_history_cap_trims_oldest_messages(self):
        sm = SessionManager(max_history=2)  # cap at 4 total
        sid = sm.create_session()
        for i in range(6):
            sm.add_message(sid, "user", f"msg {i}")
        assert len(sm.sessions[sid]) == 4
        assert sm.sessions[sid][0].content == "msg 2"

    def test_assistant_message_stored(self):
        sm = SessionManager()
        sid = sm.create_session()
        sm.add_message(sid, "assistant", "I can help!")
        assert sm.sessions[sid][0].role == "assistant"


class TestAddExchange:
    def test_adds_two_messages(self):
        sm = SessionManager()
        sid = sm.create_session()
        sm.add_exchange(sid, "What is X?", "X is Y.")
        msgs = sm.sessions[sid]
        assert len(msgs) == 2

    def test_user_message_first(self):
        sm = SessionManager()
        sid = sm.create_session()
        sm.add_exchange(sid, "Question", "Answer")
        assert sm.sessions[sid][0].role == "user"
        assert sm.sessions[sid][0].content == "Question"

    def test_assistant_message_second(self):
        sm = SessionManager()
        sid = sm.create_session()
        sm.add_exchange(sid, "Question", "Answer")
        assert sm.sessions[sid][1].role == "assistant"
        assert sm.sessions[sid][1].content == "Answer"


class TestGetConversationHistory:
    def test_returns_none_for_unknown_session(self):
        sm = SessionManager()
        assert sm.get_conversation_history("nonexistent") is None

    def test_returns_none_for_none_input(self):
        sm = SessionManager()
        assert sm.get_conversation_history(None) is None

    def test_returns_none_for_empty_session(self):
        sm = SessionManager()
        sid = sm.create_session()
        assert sm.get_conversation_history(sid) is None

    def test_formats_messages_as_string(self):
        sm = SessionManager()
        sid = sm.create_session()
        sm.add_exchange(sid, "Question", "Answer")
        history = sm.get_conversation_history(sid)
        assert isinstance(history, str)
        assert "User: Question" in history
        assert "Assistant: Answer" in history

    def test_multiple_exchanges_in_history(self):
        sm = SessionManager()
        sid = sm.create_session()
        sm.add_exchange(sid, "Q1", "A1")
        sm.add_exchange(sid, "Q2", "A2")
        history = sm.get_conversation_history(sid)
        assert "Q1" in history
        assert "A2" in history


class TestClearSession:
    def test_clears_messages(self):
        sm = SessionManager()
        sid = sm.create_session()
        sm.add_message(sid, "user", "Hello")
        sm.clear_session(sid)
        assert sm.sessions[sid] == []

    def test_session_still_exists_after_clear(self):
        sm = SessionManager()
        sid = sm.create_session()
        sm.clear_session(sid)
        assert sid in sm.sessions

    def test_no_error_on_missing_session(self):
        sm = SessionManager()
        sm.clear_session("nonexistent")  # Should not raise


class TestDeleteSession:
    def test_removes_session(self):
        sm = SessionManager()
        sid = sm.create_session()
        sm.delete_session(sid)
        assert sid not in sm.sessions

    def test_no_error_on_missing_session(self):
        sm = SessionManager()
        sm.delete_session("nonexistent")  # Should not raise
