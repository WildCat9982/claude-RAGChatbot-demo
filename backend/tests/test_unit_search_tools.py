"""Unit tests for CourseSearchTool, CourseOutlineTool, and ToolManager."""
import pytest
from unittest.mock import MagicMock

from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager, Tool
from vector_store import SearchResults


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_store():
    return MagicMock()


@pytest.fixture
def search_tool(mock_store):
    return CourseSearchTool(mock_store)


@pytest.fixture
def outline_tool(mock_store):
    return CourseOutlineTool(mock_store)


@pytest.fixture
def tool_manager():
    return ToolManager()


def _results(docs, metas):
    return SearchResults(documents=docs, metadata=metas, distances=[0.1] * len(docs))


# ---------------------------------------------------------------------------
# CourseSearchTool — definition
# ---------------------------------------------------------------------------

class TestCourseSearchToolDefinition:
    def test_name(self, search_tool):
        assert search_tool.get_tool_definition()["name"] == "search_course_content"

    def test_query_is_required(self, search_tool):
        schema = search_tool.get_tool_definition()["input_schema"]
        assert "query" in schema["required"]

    def test_has_description(self, search_tool):
        assert search_tool.get_tool_definition()["description"]


# ---------------------------------------------------------------------------
# CourseSearchTool — execute
# ---------------------------------------------------------------------------

class TestCourseSearchToolExecute:
    def test_returns_formatted_content(self, search_tool, mock_store):
        mock_store.search.return_value = _results(
            ["Python is great."],
            [{"course_title": "Python Course", "lesson_number": 1}],
        )
        mock_store.get_lesson_link.return_value = "https://example.com/1"
        result = search_tool.execute(query="Python")
        assert "Python Course" in result
        assert "Lesson 1" in result

    def test_returns_error_when_search_has_error(self, search_tool, mock_store):
        mock_store.search.return_value = SearchResults.empty("Course not found")
        result = search_tool.execute(query="test", course_name="Fake")
        assert "Course not found" in result

    def test_returns_no_results_message_for_empty(self, search_tool, mock_store):
        mock_store.search.return_value = _results([], [])
        result = search_tool.execute(query="something obscure")
        assert "No relevant content found" in result

    def test_no_results_message_includes_course_name(self, search_tool, mock_store):
        mock_store.search.return_value = _results([], [])
        result = search_tool.execute(query="test", course_name="My Course")
        assert "My Course" in result

    def test_no_results_message_includes_lesson_number(self, search_tool, mock_store):
        mock_store.search.return_value = _results([], [])
        result = search_tool.execute(query="test", lesson_number=5)
        assert "5" in result

    def test_tracks_sources(self, search_tool, mock_store):
        mock_store.search.return_value = _results(
            ["Content"],
            [{"course_title": "My Course", "lesson_number": 2}],
        )
        mock_store.get_lesson_link.return_value = "https://example.com/2"
        search_tool.execute(query="test")
        assert len(search_tool.last_sources) == 1
        assert "My Course" in search_tool.last_sources[0]

    def test_sources_contain_link_when_available(self, search_tool, mock_store):
        mock_store.search.return_value = _results(
            ["Content"],
            [{"course_title": "Course", "lesson_number": 1}],
        )
        mock_store.get_lesson_link.return_value = "https://link.example"
        search_tool.execute(query="test")
        assert "https://link.example" in search_tool.last_sources[0]

    def test_calls_store_with_correct_params(self, search_tool, mock_store):
        mock_store.search.return_value = _results([], [])
        search_tool.execute(query="loops", course_name="Python", lesson_number=2)
        mock_store.search.assert_called_once_with(
            query="loops", course_name="Python", lesson_number=2
        )


# ---------------------------------------------------------------------------
# CourseOutlineTool — definition & execute
# ---------------------------------------------------------------------------

class TestCourseOutlineTool:
    def test_name(self, outline_tool):
        assert outline_tool.get_tool_definition()["name"] == "get_course_outline"

    def test_course_name_is_required(self, outline_tool):
        schema = outline_tool.get_tool_definition()["input_schema"]
        assert "course_name" in schema["required"]

    def test_execute_returns_structured_output(self, outline_tool, mock_store):
        mock_store.get_course_outline.return_value = {
            "title": "Python Basics",
            "course_link": "https://example.com",
            "lessons": [
                {"lesson_number": 0, "lesson_title": "Intro"},
                {"lesson_number": 1, "lesson_title": "Variables"},
            ],
        }
        result = outline_tool.execute(course_name="Python")
        assert "Python Basics" in result
        assert "Lesson 0" in result
        assert "Lesson 1" in result
        assert "Intro" in result

    def test_execute_includes_course_link(self, outline_tool, mock_store):
        mock_store.get_course_outline.return_value = {
            "title": "Test",
            "course_link": "https://example.com/course",
            "lessons": [],
        }
        result = outline_tool.execute(course_name="Test")
        assert "https://example.com/course" in result

    def test_execute_returns_error_for_unknown_course(self, outline_tool, mock_store):
        mock_store.get_course_outline.return_value = None
        result = outline_tool.execute(course_name="Ghost")
        assert "No course found" in result


# ---------------------------------------------------------------------------
# ToolManager
# ---------------------------------------------------------------------------

class TestToolManager:
    def test_register_tool(self, tool_manager, search_tool):
        tool_manager.register_tool(search_tool)
        assert "search_course_content" in tool_manager.tools

    def test_register_multiple_tools(self, tool_manager, search_tool, outline_tool):
        tool_manager.register_tool(search_tool)
        tool_manager.register_tool(outline_tool)
        assert len(tool_manager.tools) == 2

    def test_register_tool_without_name_raises(self, tool_manager):
        bad_tool = MagicMock(spec=Tool)
        bad_tool.get_tool_definition.return_value = {}
        with pytest.raises(ValueError):
            tool_manager.register_tool(bad_tool)

    def test_get_tool_definitions(self, tool_manager, search_tool, outline_tool):
        tool_manager.register_tool(search_tool)
        tool_manager.register_tool(outline_tool)
        defs = tool_manager.get_tool_definitions()
        names = [d["name"] for d in defs]
        assert "search_course_content" in names
        assert "get_course_outline" in names

    def test_execute_tool_dispatches(self, tool_manager):
        mock_tool = MagicMock(spec=Tool)
        mock_tool.get_tool_definition.return_value = {"name": "my_tool"}
        mock_tool.execute.return_value = "executed"
        tool_manager.register_tool(mock_tool)

        result = tool_manager.execute_tool("my_tool", param="value")
        assert result == "executed"
        mock_tool.execute.assert_called_once_with(param="value")

    def test_execute_unknown_tool_returns_error(self, tool_manager):
        result = tool_manager.execute_tool("ghost_tool")
        assert "not found" in result

    def test_get_last_sources_empty_by_default(self, tool_manager, search_tool):
        tool_manager.register_tool(search_tool)
        assert tool_manager.get_last_sources() == []

    def test_get_last_sources_from_search_tool(self, tool_manager, search_tool):
        search_tool.last_sources = ["Source A", "Source B"]
        tool_manager.register_tool(search_tool)
        assert tool_manager.get_last_sources() == ["Source A", "Source B"]

    def test_reset_sources_clears_all_tools(self, tool_manager, search_tool):
        search_tool.last_sources = ["Source A"]
        tool_manager.register_tool(search_tool)
        tool_manager.reset_sources()
        assert search_tool.last_sources == []
