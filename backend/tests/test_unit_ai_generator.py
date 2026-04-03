"""Unit tests for AIGenerator — Anthropic client is fully mocked."""
import pytest
from unittest.mock import MagicMock, patch, call

from ai_generator import AIGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_text_response(text: str):
    """Build a mock Anthropic message response with a single text block."""
    response = MagicMock()
    response.stop_reason = "end_turn"
    block = MagicMock()
    block.text = text
    response.content = [block]
    return response


def make_tool_use_response(tool_name: str, tool_id: str, tool_input: dict):
    """Build a mock Anthropic response that requests tool use."""
    response = MagicMock()
    response.stop_reason = "tool_use"
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.id = tool_id
    block.input = tool_input
    response.content = [block]
    return response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    """Patch anthropic.Anthropic and return the mock instance."""
    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        yield client


@pytest.fixture
def generator(mock_client):
    return AIGenerator(api_key="test-key", model="claude-test-model")


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestInit:
    def test_model_stored(self, mock_client):
        gen = AIGenerator(api_key="key", model="claude-opus")
        assert gen.model == "claude-opus"
        assert gen.base_params["model"] == "claude-opus"

    def test_temperature_is_zero(self, generator):
        assert generator.base_params["temperature"] == 0

    def test_max_tokens_set(self, generator):
        assert generator.base_params["max_tokens"] == 800


# ---------------------------------------------------------------------------
# generate_response — no tools
# ---------------------------------------------------------------------------

class TestGenerateResponseDirect:
    def test_returns_text_from_response(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_response("Hello!")
        result = generator.generate_response("What is Python?")
        assert result == "Hello!"

    def test_query_included_in_user_message(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_response("ok")
        generator.generate_response("My query")
        kwargs = mock_client.messages.create.call_args[1]
        user_content = kwargs["messages"][0]["content"]
        assert "My query" in user_content

    def test_system_prompt_used(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_response("ok")
        generator.generate_response("query")
        kwargs = mock_client.messages.create.call_args[1]
        assert "system" in kwargs
        assert len(kwargs["system"]) > 0

    def test_conversation_history_appended_to_system(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_response("ok")
        generator.generate_response("query", conversation_history="User: Hi\nAssistant: Hello")
        kwargs = mock_client.messages.create.call_args[1]
        assert "User: Hi" in kwargs["system"]

    def test_no_tools_when_none_provided(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_response("ok")
        generator.generate_response("query")
        kwargs = mock_client.messages.create.call_args[1]
        assert "tools" not in kwargs

    def test_tools_included_when_provided(self, generator, mock_client):
        mock_client.messages.create.return_value = make_text_response("ok")
        tools = [{"name": "search", "description": "search", "input_schema": {}}]
        generator.generate_response("query", tools=tools)
        kwargs = mock_client.messages.create.call_args[1]
        assert "tools" in kwargs
        assert kwargs["tool_choice"] == {"type": "auto"}


# ---------------------------------------------------------------------------
# generate_response — tool use flow
# ---------------------------------------------------------------------------

class TestGenerateResponseToolUse:
    def test_tool_execution_triggered_on_tool_use_stop(self, generator, mock_client):
        tool_resp = make_tool_use_response("search_course_content", "id_1", {"query": "Python"})
        final_resp = make_text_response("Final answer")
        mock_client.messages.create.side_effect = [tool_resp, final_resp]

        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "search result"

        result = generator.generate_response(
            "query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tm,
        )
        assert result == "Final answer"
        mock_tm.execute_tool.assert_called_once()

    def test_tool_called_with_correct_name_and_args(self, generator, mock_client):
        tool_resp = make_tool_use_response(
            "search_course_content", "id_2", {"query": "loops", "lesson_number": 3}
        )
        final_resp = make_text_response("Done")
        mock_client.messages.create.side_effect = [tool_resp, final_resp]

        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "result"

        generator.generate_response("query", tools=[{}], tool_manager=mock_tm)
        mock_tm.execute_tool.assert_called_once_with(
            "search_course_content", query="loops", lesson_number=3
        )

    def test_no_tool_execution_without_tool_manager(self, generator, mock_client):
        tool_resp = make_tool_use_response("search_course_content", "id_3", {"query": "x"})
        mock_client.messages.create.return_value = tool_resp
        # stop_reason == "tool_use" but no tool_manager — should return the text block
        # The current implementation calls response.content[0].text which would be
        # the mock's .text attribute. Just ensure it doesn't crash.
        result = generator.generate_response("query", tools=[{}])
        assert result is not None


# ---------------------------------------------------------------------------
# _handle_tool_execution
# ---------------------------------------------------------------------------

class TestHandleToolExecution:
    def test_returns_final_response_text(self, generator, mock_client):
        tool_resp = make_tool_use_response("search_course_content", "t1", {"query": "test"})
        final_resp = make_text_response("Final")
        mock_client.messages.create.return_value = final_resp

        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "Result content"

        base_params = {
            "model": "test",
            "temperature": 0,
            "max_tokens": 800,
            "messages": [{"role": "user", "content": "original query"}],
            "system": "system prompt",
        }
        result = generator._handle_tool_execution(tool_resp, base_params, mock_tm)
        assert result == "Final"

    def test_tool_result_added_to_messages(self, generator, mock_client):
        tool_resp = make_tool_use_response("search_course_content", "t2", {"query": "test"})
        final_resp = make_text_response("Done")
        mock_client.messages.create.return_value = final_resp

        mock_tm = MagicMock()
        mock_tm.execute_tool.return_value = "My result"

        base_params = {
            "model": "test",
            "temperature": 0,
            "max_tokens": 800,
            "messages": [{"role": "user", "content": "q"}],
            "system": "sys",
        }
        generator._handle_tool_execution(tool_resp, base_params, mock_tm)

        # The second API call should include the tool result message
        final_call_kwargs = mock_client.messages.create.call_args[1]
        messages = final_call_kwargs["messages"]
        tool_result_messages = [
            m for m in messages
            if isinstance(m.get("content"), list)
            and any(c.get("type") == "tool_result" for c in m["content"])
        ]
        assert len(tool_result_messages) == 1
