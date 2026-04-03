"""Unit tests for Pydantic domain models."""
import pytest
from models import Lesson, Course, CourseChunk


class TestLesson:
    def test_creation_with_required_fields(self):
        lesson = Lesson(lesson_number=1, title="Intro")
        assert lesson.lesson_number == 1
        assert lesson.title == "Intro"

    def test_lesson_link_defaults_to_none(self):
        lesson = Lesson(lesson_number=1, title="Intro")
        assert lesson.lesson_link is None

    def test_lesson_link_stored(self):
        lesson = Lesson(lesson_number=2, title="Variables", lesson_link="https://example.com")
        assert lesson.lesson_link == "https://example.com"


class TestCourse:
    def test_creation_with_title_only(self):
        course = Course(title="Python 101")
        assert course.title == "Python 101"

    def test_optional_fields_default_to_none(self):
        course = Course(title="Test")
        assert course.course_link is None
        assert course.instructor is None

    def test_lessons_defaults_to_empty_list(self):
        course = Course(title="Test")
        assert course.lessons == []

    def test_course_with_all_fields(self):
        course = Course(
            title="Advanced Python",
            course_link="https://example.com",
            instructor="Jane Doe",
        )
        assert course.instructor == "Jane Doe"
        assert course.course_link == "https://example.com"

    def test_course_with_lessons(self):
        lesson = Lesson(lesson_number=1, title="Intro")
        course = Course(title="Test Course", lessons=[lesson])
        assert len(course.lessons) == 1
        assert course.lessons[0].title == "Intro"


class TestCourseChunk:
    def test_creation_with_required_fields(self):
        chunk = CourseChunk(content="Hello world", course_title="Test", chunk_index=0)
        assert chunk.content == "Hello world"
        assert chunk.course_title == "Test"
        assert chunk.chunk_index == 0

    def test_lesson_number_defaults_to_none(self):
        chunk = CourseChunk(content="text", course_title="Test", chunk_index=0)
        assert chunk.lesson_number is None

    def test_chunk_with_lesson_number(self):
        chunk = CourseChunk(content="text", course_title="Test", lesson_number=3, chunk_index=1)
        assert chunk.lesson_number == 3
        assert chunk.chunk_index == 1
