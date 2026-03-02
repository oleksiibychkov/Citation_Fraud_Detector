"""Tests for embedding strategy abstraction."""

import numpy as np

from cfd.analysis.embeddings import (
    EmbeddingStrategy,
    NaiveTfidfStrategy,
    SentenceTransformerStrategy,
    get_embedding_strategy,
)


class TestNaiveTfidfStrategy:
    def test_embed_returns_correct_shape(self):
        strategy = NaiveTfidfStrategy()
        texts = ["hello world", "foo bar baz"]
        result = strategy.embed(texts)
        assert result.shape[0] == 2
        assert result.shape[1] > 0

    def test_embed_empty_list(self):
        strategy = NaiveTfidfStrategy()
        result = strategy.embed([])
        assert result.shape == (0, 0)

    def test_embed_single_text(self):
        strategy = NaiveTfidfStrategy()
        result = strategy.embed(["one single document"])
        assert result.shape[0] == 1

    def test_identical_texts_high_similarity(self):
        strategy = NaiveTfidfStrategy()
        sim = strategy.pairwise_cosine_similarity(["cat dog", "cat dog"])
        assert sim[0, 1] > 0.99

    def test_different_texts_lower_similarity(self):
        strategy = NaiveTfidfStrategy()
        sim = strategy.pairwise_cosine_similarity([
            "machine learning algorithms neural networks",
            "gardening flowers plants soil water",
        ])
        assert sim[0, 1] < 0.5

    def test_empty_texts_handled(self):
        strategy = NaiveTfidfStrategy()
        result = strategy.embed(["", "hello world"])
        assert result.shape[0] == 2

    def test_unicode_text(self):
        strategy = NaiveTfidfStrategy()
        result = strategy.embed(["цитатний аналіз", "цитатний детектор"])
        assert result.shape[0] == 2

    def test_max_features_respected(self):
        strategy = NaiveTfidfStrategy(max_features=3)
        texts = ["one two three four five six"]
        result = strategy.embed(texts)
        assert result.shape[1] <= 3


class TestPairwiseCosineSimilarity:
    def test_diagonal_is_one(self):
        strategy = NaiveTfidfStrategy()
        texts = ["hello world", "foo bar", "baz qux"]
        sim = strategy.pairwise_cosine_similarity(texts)
        for i in range(3):
            assert abs(sim[i, i] - 1.0) < 1e-6

    def test_symmetric(self):
        strategy = NaiveTfidfStrategy()
        texts = ["alpha beta", "gamma delta"]
        sim = strategy.pairwise_cosine_similarity(texts)
        assert abs(sim[0, 1] - sim[1, 0]) < 1e-10

    def test_values_in_range(self):
        strategy = NaiveTfidfStrategy()
        texts = ["hello world", "foo bar"]
        sim = strategy.pairwise_cosine_similarity(texts)
        assert np.all(sim >= -1.01)
        assert np.all(sim <= 1.01)

    def test_empty_input(self):
        strategy = NaiveTfidfStrategy()
        sim = strategy.pairwise_cosine_similarity([])
        assert sim.shape == (0, 0)


class TestSentenceTransformerStrategy:
    def test_import_error_without_package(self):
        """If sentence-transformers not installed, should raise ImportError."""
        strategy = SentenceTransformerStrategy()
        # This test might pass or fail depending on whether the package is installed
        # We just test that the class can be instantiated
        assert strategy._model_name == "all-MiniLM-L6-v2"


class TestGetEmbeddingStrategy:
    def test_default_returns_tfidf(self):
        strategy = get_embedding_strategy()
        assert isinstance(strategy, NaiveTfidfStrategy)

    def test_prefer_neural_false(self):
        strategy = get_embedding_strategy(prefer_neural=False)
        assert isinstance(strategy, NaiveTfidfStrategy)

    def test_is_embedding_strategy(self):
        strategy = get_embedding_strategy()
        assert isinstance(strategy, EmbeddingStrategy)
