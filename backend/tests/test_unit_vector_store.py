"""Unit tests for VectorStore.

The sentence-transformers embedding model is swapped for a deterministic mock
to avoid slow model downloads.  A real PersistentClient is used with an
isolated tmp_path per test to prevent cross-test data leakage (EphemeralClient
shares in-memory state across instances in the same process).
"""
import pytest
from unittest.mock import patch
from helpers import MockEmbeddingFunction

from vector_store import VectorStore, SearchResults
from models import Course, Lesson, CourseChunk


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def vector_store(tmp_path):
    """VectorStore with per-test ChromaDB directory and mock embedding fn."""
    with patch(
        "vector_store.chromadb.utils.embedding_functions"
        ".SentenceTransformerEmbeddingFunction"
    ) as mock_emb_fn:
        mock_emb_fn.return_value = MockEmbeddingFunction()

        store = VectorStore(
            chroma_path=str(tmp_path / "chroma"),
            embedding_model="all-MiniLM-L6-v2",
            max_results=5,
        )
        yield store


@pytest.fixture
def sample_course():
    return Course(
        title="Python Basics",
        course_link="https://example.com/python",
        instructor="Jane Doe",
        lessons=[
            Lesson(lesson_number=0, title="Introduction",
                   lesson_link="https://example.com/python/0"),
            Lesson(lesson_number=1, title="Variables",
                   lesson_link="https://example.com/python/1"),
        ],
    )


@pytest.fixture
def sample_chunks():
    return [
        CourseChunk(content="Python is a high-level programming language.",
                    course_title="Python Basics", lesson_number=0, chunk_index=0),
        CourseChunk(content="Variables store data values.",
                    course_title="Python Basics", lesson_number=1, chunk_index=1),
        CourseChunk(content="You assign values with the equals sign.",
                    course_title="Python Basics", lesson_number=1, chunk_index=2),
    ]


# ---------------------------------------------------------------------------
# SearchResults helpers
# ---------------------------------------------------------------------------

class TestSearchResults:
    def test_from_chroma_parses_nested_lists(self):
        data = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"k": "v1"}, {"k": "v2"}]],
            "distances": [[0.1, 0.2]],
        }
        sr = SearchResults.from_chroma(data)
        assert sr.documents == ["doc1", "doc2"]
        assert len(sr.metadata) == 2
        assert sr.distances == [0.1, 0.2]

    def test_empty_factory_sets_error(self):
        sr = SearchResults.empty("test error")
        assert sr.is_empty()
        assert sr.error == "test error"

    def test_is_empty_false_when_documents_exist(self):
        sr = SearchResults(documents=["doc"], metadata=[{}], distances=[0.1])
        assert not sr.is_empty()

    def test_from_chroma_empty_results(self):
        data = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        sr = SearchResults.from_chroma(data)
        assert sr.is_empty()


# ---------------------------------------------------------------------------
# VectorStore — metadata & catalog
# ---------------------------------------------------------------------------

class TestCourseMetadata:
    def test_add_course_appears_in_titles(self, vector_store, sample_course):
        vector_store.add_course_metadata(sample_course)
        assert "Python Basics" in vector_store.get_existing_course_titles()

    def test_get_course_count_empty(self, vector_store):
        assert vector_store.get_course_count() == 0

    def test_get_course_count_after_add(self, vector_store, sample_course):
        vector_store.add_course_metadata(sample_course)
        assert vector_store.get_course_count() == 1

    def test_get_all_courses_metadata_includes_lessons(self, vector_store, sample_course):
        vector_store.add_course_metadata(sample_course)
        metadata = vector_store.get_all_courses_metadata()
        assert len(metadata) == 1
        assert metadata[0]["title"] == "Python Basics"
        assert "lessons" in metadata[0]
        assert len(metadata[0]["lessons"]) == 2

    def test_get_course_link(self, vector_store, sample_course):
        vector_store.add_course_metadata(sample_course)
        link = vector_store.get_course_link("Python Basics")
        assert link == "https://example.com/python"

    def test_get_course_link_missing(self, vector_store, sample_course):
        vector_store.add_course_metadata(sample_course)
        assert vector_store.get_course_link("Nonexistent") is None

    def test_get_lesson_link(self, vector_store, sample_course):
        vector_store.add_course_metadata(sample_course)
        link = vector_store.get_lesson_link("Python Basics", 0)
        assert link == "https://example.com/python/0"

    def test_get_lesson_link_wrong_number(self, vector_store, sample_course):
        vector_store.add_course_metadata(sample_course)
        assert vector_store.get_lesson_link("Python Basics", 99) is None


# ---------------------------------------------------------------------------
# VectorStore — course outline
# ---------------------------------------------------------------------------

class TestCourseOutline:
    def test_get_course_outline_returns_structure(self, vector_store, sample_course):
        vector_store.add_course_metadata(sample_course)
        outline = vector_store.get_course_outline("Python Basics")
        assert outline is not None
        assert outline["title"] == "Python Basics"
        assert "lessons" in outline
        assert len(outline["lessons"]) == 2

    def test_get_course_outline_includes_course_link(self, vector_store, sample_course):
        vector_store.add_course_metadata(sample_course)
        outline = vector_store.get_course_outline("Python Basics")
        assert outline["course_link"] == "https://example.com/python"

    def test_get_course_outline_empty_catalog_returns_none(self, vector_store):
        """With an empty catalog _resolve_course_name cannot find anything."""
        assert vector_store.get_course_outline("Ghost Course XYZ") is None


# ---------------------------------------------------------------------------
# VectorStore — content search
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_empty_store_returns_empty(self, vector_store):
        results = vector_store.search("Python")
        assert results.is_empty()

    def test_search_returns_results_after_add(
        self, vector_store, sample_course, sample_chunks
    ):
        vector_store.add_course_metadata(sample_course)
        vector_store.add_course_content(sample_chunks)
        results = vector_store.search("programming language")
        assert not results.is_empty()

    def test_search_result_has_metadata(
        self, vector_store, sample_course, sample_chunks
    ):
        vector_store.add_course_metadata(sample_course)
        vector_store.add_course_content(sample_chunks)
        results = vector_store.search("variables")
        assert all("course_title" in m for m in results.metadata)

    def test_search_with_course_filter(
        self, vector_store, sample_course, sample_chunks
    ):
        vector_store.add_course_metadata(sample_course)
        vector_store.add_course_content(sample_chunks)
        results = vector_store.search("Python", course_name="Python Basics")
        assert not results.is_empty()
        for meta in results.metadata:
            assert meta["course_title"] == "Python Basics"

    def test_search_course_name_without_catalog_returns_error(self, vector_store):
        """With an empty catalog _resolve_course_name raises, returning an error."""
        results = vector_store.search("Python", course_name="Nonexistent Course")
        assert results.error is not None

    def test_search_fuzzy_course_name_matches_nearest_neighbor(
        self, vector_store, sample_course, sample_chunks
    ):
        """_resolve_course_name has no similarity threshold; any query returns
        the nearest course in the catalog — never an error when catalog is non-empty."""
        vector_store.add_course_metadata(sample_course)
        vector_store.add_course_content(sample_chunks)
        # Completely different name still resolves to "Python Basics" (only course)
        results = vector_store.search("Python", course_name="Totally Unrelated Name XYZ")
        assert results.error is None

    def test_search_with_lesson_filter(
        self, vector_store, sample_course, sample_chunks
    ):
        vector_store.add_course_metadata(sample_course)
        vector_store.add_course_content(sample_chunks)
        results = vector_store.search("data", lesson_number=1)
        for meta in results.metadata:
            assert meta["lesson_number"] == 1

    def test_add_course_content_empty_list_does_not_raise(self, vector_store):
        vector_store.add_course_content([])  # Should be a no-op


# ---------------------------------------------------------------------------
# VectorStore — filters
# ---------------------------------------------------------------------------

class TestBuildFilter:
    def test_no_params_returns_none(self, vector_store):
        assert vector_store._build_filter(None, None) is None

    def test_course_title_only(self, vector_store):
        f = vector_store._build_filter("Python Basics", None)
        assert f == {"course_title": "Python Basics"}

    def test_lesson_number_only(self, vector_store):
        f = vector_store._build_filter(None, 1)
        assert f == {"lesson_number": 1}

    def test_both_uses_and_clause(self, vector_store):
        f = vector_store._build_filter("Python Basics", 2)
        assert "$and" in f
        conditions = f["$and"]
        assert {"course_title": "Python Basics"} in conditions
        assert {"lesson_number": 2} in conditions


# ---------------------------------------------------------------------------
# VectorStore — clear
# ---------------------------------------------------------------------------

class TestClearAllData:
    def test_clears_catalog(self, vector_store, sample_course):
        vector_store.add_course_metadata(sample_course)
        vector_store.clear_all_data()
        assert vector_store.get_course_count() == 0

    def test_clears_content(self, vector_store, sample_course, sample_chunks):
        vector_store.add_course_metadata(sample_course)
        vector_store.add_course_content(sample_chunks)
        vector_store.clear_all_data()
        results = vector_store.search("Python")
        assert results.is_empty()
