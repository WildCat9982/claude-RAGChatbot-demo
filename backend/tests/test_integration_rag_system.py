"""Integration tests for RAGSystem.

Real document processing and ChromaDB (real PersistentClient with isolated
tmp_path) are used.  The Anthropic API is mocked so no network calls are made.
"""
import pytest
import shutil
from unittest.mock import MagicMock, patch

from helpers import MockEmbeddingFunction
from rag_system import RAGSystem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_text_response(text: str):
    response = MagicMock()
    response.stop_reason = "end_turn"
    block = MagicMock()
    block.text = text
    response.content = [block]
    return response


def make_course_file(tmp_path, name: str, index: int = 0) -> str:
    content = (
        f"Course Title: {name}\n"
        f"Course Link: https://example.com/course{index}\n"
        f"Course Instructor: Instructor {index}\n"
        "\n"
        "Lesson 0: Introduction\n"
        f"Lesson Link: https://example.com/course{index}/0\n"
        f"This is the introductory content for {name}.\n"
        "\n"
        "Lesson 1: Core Concepts\n"
        f"Lesson Link: https://example.com/course{index}/1\n"
        f"Core concept content for {name} goes here.\n"
    )
    f = tmp_path / f"{name.replace(' ', '_')}.txt"
    f.write_text(content, encoding="utf-8")
    return str(f)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def rag(tmp_path):
    """RAGSystem with per-test ChromaDB directory and mocked Anthropic."""
    with patch(
        "vector_store.chromadb.utils.embedding_functions"
        ".SentenceTransformerEmbeddingFunction"
    ) as mock_emb, \
         patch("ai_generator.anthropic.Anthropic") as mock_anthropic_cls:

        mock_emb.return_value = MockEmbeddingFunction()

        mock_api = MagicMock()
        mock_anthropic_cls.return_value = mock_api

        config = MagicMock()
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "claude-test"
        config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        config.CHUNK_SIZE = 300
        config.CHUNK_OVERLAP = 50
        config.MAX_RESULTS = 3
        config.MAX_HISTORY = 2
        config.CHROMA_PATH = str(tmp_path / "chroma")

        system = RAGSystem(config)
        system._mock_api = mock_api
        yield system


# ---------------------------------------------------------------------------
# add_course_document
# ---------------------------------------------------------------------------

class TestAddCourseDocument:
    def test_returns_course_and_chunk_count(self, rag, tmp_path):
        path = make_course_file(tmp_path, "Python 101", 0)
        course, count = rag.add_course_document(path)
        assert course is not None
        assert course.title == "Python 101"
        assert count > 0

    def test_course_stored_in_vector_store(self, rag, tmp_path):
        path = make_course_file(tmp_path, "Machine Learning", 1)
        rag.add_course_document(path)
        assert "Machine Learning" in rag.vector_store.get_existing_course_titles()

    def test_content_chunks_stored(self, rag, tmp_path):
        path = make_course_file(tmp_path, "Data Science", 2)
        rag.add_course_document(path)
        results = rag.vector_store.search("introductory content")
        assert not results.is_empty()

    def test_invalid_path_returns_none_and_zero(self, rag):
        course, count = rag.add_course_document("/nonexistent/path/course.txt")
        assert course is None
        assert count == 0


# ---------------------------------------------------------------------------
# add_course_folder
# ---------------------------------------------------------------------------

class TestAddCourseFolder:
    def test_processes_all_txt_files(self, rag, tmp_path):
        for i in range(3):
            make_course_file(tmp_path, f"Course {i}", i)
        courses, chunks = rag.add_course_folder(str(tmp_path))
        assert courses == 3
        assert chunks > 0

    def test_skips_already_existing_courses(self, rag, tmp_path):
        path = make_course_file(tmp_path, "Existing Course", 0)
        rag.add_course_document(path)

        # Add the same file to a new folder
        folder = tmp_path / "reload"
        folder.mkdir()
        shutil.copy(path, folder / "course.txt")

        courses, _ = rag.add_course_folder(str(folder))
        assert courses == 0

    def test_nonexistent_folder_returns_zeros(self, rag):
        courses, chunks = rag.add_course_folder("/does/not/exist")
        assert courses == 0
        assert chunks == 0

    def test_clear_existing_removes_old_data(self, rag, tmp_path):
        make_course_file(tmp_path, "Old Course", 0)
        rag.add_course_folder(str(tmp_path))
        assert rag.vector_store.get_course_count() == 1

        # Now add a fresh folder with a different course, clearing old data
        new_folder = tmp_path / "new"
        new_folder.mkdir()
        make_course_file(new_folder, "New Course", 1)
        rag.add_course_folder(str(new_folder), clear_existing=True)

        titles = rag.vector_store.get_existing_course_titles()
        assert "Old Course" not in titles
        assert "New Course" in titles


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------

class TestQuery:
    def test_returns_answer_and_sources(self, rag, tmp_path):
        make_course_file(tmp_path, "Python 101", 0)
        rag.add_course_document(str(tmp_path / "Python_101.txt"))
        rag._mock_api.messages.create.return_value = make_text_response("Python is awesome!")

        answer, sources = rag.query("What is Python?")
        assert answer == "Python is awesome!"
        assert isinstance(sources, list)

    def test_creates_session_history_when_session_provided(self, rag, tmp_path):
        make_course_file(tmp_path, "Python 101", 0)
        rag.add_course_document(str(tmp_path / "Python_101.txt"))
        rag._mock_api.messages.create.return_value = make_text_response("Answer")

        sid = rag.session_manager.create_session()
        rag.query("Question?", sid)

        history = rag.session_manager.get_conversation_history(sid)
        assert history is not None
        assert "Question?" in history

    def test_no_session_does_not_create_history(self, rag):
        rag._mock_api.messages.create.return_value = make_text_response("Answer")
        # No session_id — session_manager should have no entries
        initial_count = len(rag.session_manager.sessions)
        rag.query("General question")
        assert len(rag.session_manager.sessions) == initial_count

    def test_sources_reset_after_query(self, rag):
        rag._mock_api.messages.create.return_value = make_text_response("Answer")
        rag.query("Question?")
        # After the query the tool manager should have cleared its sources
        assert rag.tool_manager.get_last_sources() == []


# ---------------------------------------------------------------------------
# get_course_analytics
# ---------------------------------------------------------------------------

class TestGetCourseAnalytics:
    def test_empty_analytics(self, rag):
        analytics = rag.get_course_analytics()
        assert analytics["total_courses"] == 0
        assert analytics["course_titles"] == []

    def test_analytics_after_adding_courses(self, rag, tmp_path):
        for i in range(2):
            path = make_course_file(tmp_path, f"Course {i}", i)
            rag.add_course_document(path)
        analytics = rag.get_course_analytics()
        assert analytics["total_courses"] == 2
        assert "Course 0" in analytics["course_titles"]
        assert "Course 1" in analytics["course_titles"]
