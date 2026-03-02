"""Embedding strategy abstraction for text similarity computation."""

from __future__ import annotations

import abc
import logging
import math
import re
from collections import Counter

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingStrategy(abc.ABC):
    """Abstract strategy for computing text embeddings."""

    @abc.abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """Compute embeddings for a list of texts. Returns shape (n, dim)."""
        ...

    def pairwise_cosine_similarity(self, texts: list[str]) -> np.ndarray:
        """Compute pairwise cosine similarity matrix. Shape (n, n)."""
        if not texts:
            return np.array([]).reshape(0, 0)
        embeddings = self.embed(texts)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        normalized = embeddings / norms
        return normalized @ normalized.T


class NaiveTfidfStrategy(EmbeddingStrategy):
    """TF-IDF embedding using only numpy (no scikit-learn required).

    Tokenizes on word boundaries, computes TF-IDF weights,
    returns dense vectors suitable for cosine similarity.
    """

    def __init__(self, max_features: int = 5000):
        self._max_features = max_features

    def embed(self, texts: list[str]) -> np.ndarray:
        """Compute TF-IDF embeddings. Returns shape (n, vocab_size)."""
        if not texts:
            return np.array([]).reshape(0, 0)

        # Tokenize
        tokenized = [self._tokenize(t) for t in texts]
        n_docs = len(tokenized)

        # Build vocabulary from document frequencies
        doc_freq: Counter[str] = Counter()
        for tokens in tokenized:
            doc_freq.update(set(tokens))

        # Select top features by document frequency
        vocab_items = doc_freq.most_common(self._max_features)
        vocab = {word: idx for idx, (word, _) in enumerate(vocab_items)}
        vocab_size = len(vocab)

        if vocab_size == 0:
            return np.zeros((n_docs, 1))

        # Compute TF-IDF matrix
        matrix = np.zeros((n_docs, vocab_size))
        for i, tokens in enumerate(tokenized):
            if not tokens:
                continue
            tf = Counter(tokens)
            for word, count in tf.items():
                if word in vocab:
                    j = vocab[word]
                    # TF: log(1 + count)
                    # IDF: log(1 + n_docs / (1 + doc_freq)) — smoothed
                    idf = math.log(1 + n_docs / (1 + doc_freq[word]))
                    matrix[i, j] = math.log(1 + count) * idf

        return matrix

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple word tokenizer: lowercase, split on non-alpha, filter short."""
        if not text:
            return []
        words = re.findall(r"[a-zA-Z\u0400-\u04FF]{2,}", text.lower())
        return words


class SentenceTransformerStrategy(EmbeddingStrategy):
    """Sentence-transformers embedding (optional [neural] dependency).

    Requires: pip install citation-fraud-detector[neural]
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None

    def embed(self, texts: list[str]) -> np.ndarray:
        """Compute neural embeddings. Returns shape (n, dim)."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as err:
                raise ImportError(
                    "sentence-transformers required. Install with: "
                    "pip install citation-fraud-detector[neural]"
                ) from err
            self._model = SentenceTransformer(self._model_name)

        if not texts:
            return np.array([]).reshape(0, 0)
        return self._model.encode(texts, show_progress_bar=False)


def get_embedding_strategy(prefer_neural: bool = False) -> EmbeddingStrategy:
    """Factory: return neural strategy if available and requested, else TF-IDF."""
    if prefer_neural:
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401

            return SentenceTransformerStrategy()
        except ImportError:
            logger.info("sentence-transformers not installed, using TF-IDF fallback")
    return NaiveTfidfStrategy()
