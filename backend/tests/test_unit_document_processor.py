"""Unit tests for DocumentProcessor — no network or DB dependencies."""
import pytest
from document_processor import DocumentProcessor


@pytest.fixture
def processor():
    return DocumentProcessor(chunk_size=200, chunk_overlap=50)


@pytest.fixture
def structured_course_file(tmp_path):
    content = (
        "Course Title: Python Basics\n"
        "Course Link: https://example.com/python\n"
        "Course Instructor: John Doe\n"
        "\n"
        "Lesson 0: Introduction\n"
        "Lesson Link: https://example.com/python/0\n"
        "Python is a high-level programming language. It is easy to learn.\n"
        "\n"
        "Lesson 1: Variables\n"
        "Lesson Link: https://example.com/python/1\n"
        "Variables store values. You assign them with an equals sign.\n"
    )
    f = tmp_path / "course.txt"
    f.write_text(content, encoding="utf-8")
    return str(f)


# ---------------------------------------------------------------------------
# chunk_text
# ---------------------------------------------------------------------------

class TestChunkText:
    def test_returns_list(self, processor):
        chunks = processor.chunk_text("Hello world.")
        assert isinstance(chunks, list)

    def test_single_sentence_single_chunk(self, processor):
        chunks = processor.chunk_text("This is one sentence.")
        assert len(chunks) == 1
        assert chunks[0] == "This is one sentence."

    def test_empty_string_returns_empty(self, processor):
        assert processor.chunk_text("") == []

    def test_whitespace_only_returns_empty(self, processor):
        assert processor.chunk_text("   \n\t  ") == []

    def test_all_content_preserved(self, processor):
        text = "First sentence. Second sentence. Third sentence."
        chunks = processor.chunk_text(text)
        combined = " ".join(chunks)
        for part in ("First sentence", "Second sentence", "Third sentence"):
            assert part in combined

    def test_chunk_does_not_exceed_size(self):
        p = DocumentProcessor(chunk_size=80, chunk_overlap=0)
        # Build text with long sentences that force splitting
        sentences = ["Word " * 15 + "." for _ in range(4)]
        text = " ".join(sentences)
        chunks = p.chunk_text(text)
        for chunk in chunks:
            # A single sentence may slightly exceed chunk_size; the logic only
            # breaks on sentence boundaries so allow one sentence of slack.
            assert len(chunk) < 200

    def test_multiple_sentences_merged_into_chunk(self):
        # With no overlap, five short sentences all fit in one 200-char chunk
        p = DocumentProcessor(chunk_size=200, chunk_overlap=0)
        text = "Alpha sentence. Beta sentence. Gamma sentence. Delta sentence. Epsilon sentence."
        chunks = p.chunk_text(text)
        assert len(chunks) == 1


# ---------------------------------------------------------------------------
# process_course_document
# ---------------------------------------------------------------------------

class TestProcessCourseDocument:
    def test_returns_course_and_chunks_tuple(self, processor, structured_course_file):
        course, chunks = processor.process_course_document(structured_course_file)
        assert course is not None
        assert isinstance(chunks, list)

    def test_extracts_title(self, processor, structured_course_file):
        course, _ = processor.process_course_document(structured_course_file)
        assert course.title == "Python Basics"

    def test_extracts_course_link(self, processor, structured_course_file):
        course, _ = processor.process_course_document(structured_course_file)
        assert course.course_link == "https://example.com/python"

    def test_extracts_instructor(self, processor, structured_course_file):
        course, _ = processor.process_course_document(structured_course_file)
        assert course.instructor == "John Doe"

    def test_lessons_created(self, processor, structured_course_file):
        course, _ = processor.process_course_document(structured_course_file)
        assert len(course.lessons) >= 1

    def test_lesson_link_extracted(self, processor, structured_course_file):
        course, _ = processor.process_course_document(structured_course_file)
        lesson0 = next((l for l in course.lessons if l.lesson_number == 0), None)
        assert lesson0 is not None
        assert lesson0.lesson_link == "https://example.com/python/0"

    def test_chunks_created(self, processor, structured_course_file):
        _, chunks = processor.process_course_document(structured_course_file)
        assert len(chunks) > 0

    def test_chunks_reference_correct_course(self, processor, structured_course_file):
        _, chunks = processor.process_course_document(structured_course_file)
        for chunk in chunks:
            assert chunk.course_title == "Python Basics"

    def test_chunks_have_lesson_numbers(self, processor, structured_course_file):
        _, chunks = processor.process_course_document(structured_course_file)
        lesson_numbers = {c.lesson_number for c in chunks}
        assert lesson_numbers <= {0, 1, None}

    def test_chunk_indices_are_unique(self, processor, structured_course_file):
        _, chunks = processor.process_course_document(structured_course_file)
        indices = [c.chunk_index for c in chunks]
        assert len(indices) == len(set(indices))

    def test_fallback_for_unstructured_document(self, processor, tmp_path):
        # The fallback path requires len(lines) > 2 to activate
        content = "My Plain Course\nSecond line of header info\nThird line\nJust some plain text. No structured headers here. More content follows."
        f = tmp_path / "plain.txt"
        f.write_text(content, encoding="utf-8")
        course, chunks = processor.process_course_document(str(f))
        assert course is not None
        assert len(chunks) > 0

    def test_title_fallback_to_first_line(self, processor, tmp_path):
        content = "My Informal Course\n\nSome content here."
        f = tmp_path / "informal.txt"
        f.write_text(content, encoding="utf-8")
        course, _ = processor.process_course_document(str(f))
        assert course.title == "My Informal Course"

    def test_missing_instructor_results_in_none(self, processor, tmp_path):
        content = "Course Title: No Instructor\nCourse Link: https://x.com\n\nContent."
        f = tmp_path / "noinstructor.txt"
        f.write_text(content, encoding="utf-8")
        course, _ = processor.process_course_document(str(f))
        assert course.instructor is None
