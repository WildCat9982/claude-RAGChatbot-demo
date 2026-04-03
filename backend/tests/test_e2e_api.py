"""End-to-end tests for the REST API.

A lightweight test app mirrors the endpoints in app.py but omits the static-file
mount (which requires the frontend directory to exist) and the startup document
loader.  The RAGSystem is fully mocked so no ChromaDB or Anthropic calls happen.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from unittest.mock import MagicMock

from session_manager import SessionManager


# ---------------------------------------------------------------------------
# Test app factory
# ---------------------------------------------------------------------------

def create_test_app(rag_system) -> FastAPI:
    """Build a FastAPI app with the same API routes as app.py, without static files."""

    app = FastAPI(title="RAG Test App")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def delete_session(session_id: str):
        rag_system.session_manager.delete_session(session_id)
        return {"status": "ok"}

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag():
    rag = MagicMock()
    rag.session_manager = SessionManager()
    rag.query.return_value = ("This is the answer.", ["Source 1", "Source 2"])
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Course A", "Course B"],
    }
    return rag


@pytest.fixture
def client(mock_rag):
    app = create_test_app(mock_rag)
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    def test_returns_200(self, client):
        resp = client.post("/api/query", json={"query": "What is Python?"})
        assert resp.status_code == 200

    def test_response_contains_required_fields(self, client):
        data = client.post("/api/query", json={"query": "test"}).json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

    def test_answer_matches_mock(self, client):
        data = client.post("/api/query", json={"query": "test"}).json()
        assert data["answer"] == "This is the answer."

    def test_sources_matches_mock(self, client):
        data = client.post("/api/query", json={"query": "test"}).json()
        assert data["sources"] == ["Source 1", "Source 2"]

    def test_auto_creates_session_id(self, client):
        data = client.post("/api/query", json={"query": "hello"}).json()
        assert data["session_id"].startswith("session_")

    def test_uses_provided_session_id(self, client, mock_rag):
        sid = mock_rag.session_manager.create_session()
        data = client.post("/api/query", json={"query": "hi", "session_id": sid}).json()
        assert data["session_id"] == sid

    def test_missing_query_returns_422(self, client):
        resp = client.post("/api/query", json={})
        assert resp.status_code == 422

    def test_rag_exception_returns_500(self, client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("DB exploded")
        resp = client.post("/api/query", json={"query": "test"})
        assert resp.status_code == 500
        assert "DB exploded" in resp.json()["detail"]

    def test_query_forwarded_to_rag(self, client, mock_rag):
        client.post("/api/query", json={"query": "specific question"})
        call_args = mock_rag.query.call_args
        assert "specific question" in call_args[0][0]

    def test_empty_sources_allowed(self, client, mock_rag):
        mock_rag.query.return_value = ("Answer with no sources.", [])
        data = client.post("/api/query", json={"query": "q"}).json()
        assert data["sources"] == []


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:
    def test_returns_200(self, client):
        assert client.get("/api/courses").status_code == 200

    def test_total_courses_correct(self, client):
        data = client.get("/api/courses").json()
        assert data["total_courses"] == 2

    def test_course_titles_correct(self, client):
        data = client.get("/api/courses").json()
        assert "Course A" in data["course_titles"]
        assert "Course B" in data["course_titles"]

    def test_response_structure(self, client):
        data = client.get("/api/courses").json()
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

    def test_analytics_exception_returns_500(self, client, mock_rag):
        mock_rag.get_course_analytics.side_effect = Exception("Analytics down")
        resp = client.get("/api/courses")
        assert resp.status_code == 500
        assert "Analytics down" in resp.json()["detail"]

    def test_empty_course_list(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }
        data = client.get("/api/courses").json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []


# ---------------------------------------------------------------------------
# DELETE /api/session/{session_id}
# ---------------------------------------------------------------------------

class TestDeleteSessionEndpoint:
    def test_returns_200(self, client, mock_rag):
        sid = mock_rag.session_manager.create_session()
        resp = client.delete(f"/api/session/{sid}")
        assert resp.status_code == 200

    def test_returns_ok_status(self, client, mock_rag):
        sid = mock_rag.session_manager.create_session()
        data = client.delete(f"/api/session/{sid}").json()
        assert data == {"status": "ok"}

    def test_session_actually_removed(self, client, mock_rag):
        sid = mock_rag.session_manager.create_session()
        client.delete(f"/api/session/{sid}")
        assert sid not in mock_rag.session_manager.sessions

    def test_deleting_nonexistent_session_still_returns_ok(self, client):
        resp = client.delete("/api/session/ghost_session_xyz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_session_history_cleared(self, client, mock_rag):
        sid = mock_rag.session_manager.create_session()
        mock_rag.session_manager.add_message(sid, "user", "Hello")
        client.delete(f"/api/session/{sid}")
        assert sid not in mock_rag.session_manager.sessions
