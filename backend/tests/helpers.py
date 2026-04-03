"""Shared test helpers used across the test suite."""


class MockEmbeddingFunction:
    """Deterministic fake embedding function — avoids loading sentence-transformers during tests.

    Implements the ChromaDB 1.0 EmbeddingFunction interface (name() + is_legacy).
    """

    is_legacy = False

    def name(self) -> str:
        return "MockEmbeddingFunction"

    def __call__(self, input):  # noqa: A002
        embeddings = []
        for text in input:
            seed = sum(ord(c) for c in text) % 100
            embedding = [(seed + j) % 100 / 100.0 for j in range(384)]
            embeddings.append(embedding)
        return embeddings
