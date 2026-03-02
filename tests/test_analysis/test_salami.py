"""Tests for Salami Slicing Detector (SSD) indicator."""

from datetime import date

from cfd.analysis.embeddings import NaiveTfidfStrategy
from cfd.analysis.salami import _find_publication_series, _find_similar_pairs, _title_jaccard, compute_ssd
from cfd.data.models import AuthorData, AuthorProfile, Publication


def _make_profile(**kw):
    defaults = {"surname": "Test", "source_api": "openalex"}
    defaults.update(kw)
    return AuthorProfile(**defaults)


def _make_pub(work_id, title=None, abstract=None, pub_date=None, **kw):
    return Publication(
        work_id=work_id,
        title=title or f"Paper {work_id}",
        abstract=abstract,
        publication_date=pub_date or date(2023, 6, 1),
        source_api="openalex",
        **kw,
    )


class TestComputeSSD:
    def test_no_publications(self):
        ad = AuthorData(profile=_make_profile(), publications=[], citations=[])
        result = compute_ssd(ad)
        assert result.indicator_type == "SSD"
        assert result.value == 0.0

    def test_single_publication(self):
        ad = AuthorData(profile=_make_profile(), publications=[_make_pub("W1")], citations=[])
        result = compute_ssd(ad)
        assert result.value == 0.0

    def test_diverse_papers_low_ssd(self):
        pubs = [
            _make_pub("W1", abstract="Machine learning algorithms for classification tasks"),
            _make_pub("W2", abstract="Organic chemistry synthesis of novel compounds"),
            _make_pub("W3", abstract="Historical analysis of medieval European trade routes"),
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_ssd(ad, similarity_threshold=0.7)
        assert result.value < 0.5

    def test_similar_abstracts_high_ssd(self):
        pubs = [
            _make_pub("W1", abstract="Deep learning neural network approach to image classification"),
            _make_pub("W2", abstract="Deep learning neural network method for image classification"),
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_ssd(ad, similarity_threshold=0.5)
        assert result.value > 0.0

    def test_no_abstracts_fallback(self):
        pubs = [_make_pub("W1"), _make_pub("W2")]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_ssd(ad)
        # No abstracts means no similar pairs from embeddings; might get series pairs
        assert result.value >= 0.0

    def test_publication_series_detected(self):
        pubs = [
            _make_pub("W1", title="Study of X part 1", pub_date=date(2023, 1, 1)),
            _make_pub("W2", title="Study of X part 2", pub_date=date(2023, 1, 15)),
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_ssd(ad, interval_days=30)
        assert result.value > 0.0

    def test_distant_publications_no_series(self):
        pubs = [
            _make_pub("W1", title="Study of X part 1", pub_date=date(2020, 1, 1)),
            _make_pub("W2", title="Study of X part 2", pub_date=date(2023, 6, 1)),
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_ssd(ad, interval_days=30)
        # Distant dates = no series
        assert "publication_series" in result.details

    def test_details_fields(self):
        pubs = [_make_pub("W1", abstract="abc"), _make_pub("W2", abstract="def")]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_ssd(ad)
        assert "similar_pairs" in result.details
        assert "publication_series" in result.details
        assert "suspicious_paper_count" in result.details
        assert "total_papers" in result.details

    def test_value_normalized(self):
        pubs = [
            _make_pub(f"W{i}", abstract="same abstract for all papers repeated here")
            for i in range(5)
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_ssd(ad)
        assert 0.0 <= result.value <= 1.0

    def test_custom_embedding_strategy(self):
        strategy = NaiveTfidfStrategy(max_features=100)
        pubs = [_make_pub("W1", abstract="hello world"), _make_pub("W2", abstract="hello world")]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        result = compute_ssd(ad, embedding_strategy=strategy)
        assert result.indicator_type == "SSD"


class TestFindSimilarPairs:
    def test_no_abstracts(self):
        pubs = [_make_pub("W1"), _make_pub("W2")]
        strategy = NaiveTfidfStrategy()
        assert _find_similar_pairs(pubs, strategy) == []

    def test_identical_abstracts(self):
        pubs = [
            _make_pub("W1", abstract="testing identical content here"),
            _make_pub("W2", abstract="testing identical content here"),
        ]
        strategy = NaiveTfidfStrategy()
        pairs = _find_similar_pairs(pubs, strategy, threshold=0.5)
        assert len(pairs) >= 1


class TestFindPublicationSeries:
    def test_close_dates_similar_titles(self):
        pubs = [
            _make_pub("W1", title="Analysis of X method", pub_date=date(2023, 3, 1)),
            _make_pub("W2", title="Analysis of X approach", pub_date=date(2023, 3, 20)),
        ]
        series = _find_publication_series(pubs, interval_days=30)
        assert len(series) >= 1

    def test_distant_dates(self):
        pubs = [
            _make_pub("W1", title="Study part 1", pub_date=date(2020, 1, 1)),
            _make_pub("W2", title="Study part 2", pub_date=date(2023, 1, 1)),
        ]
        series = _find_publication_series(pubs, interval_days=30)
        assert len(series) == 0


class TestTitleJaccard:
    def test_identical(self):
        assert _title_jaccard("hello world", "hello world") == 1.0

    def test_disjoint(self):
        assert _title_jaccard("abc def", "ghi jkl") == 0.0

    def test_partial_overlap(self):
        sim = _title_jaccard("hello world foo", "hello world bar")
        assert 0.0 < sim < 1.0

    def test_none_input(self):
        assert _title_jaccard(None, "hello") == 0.0
        assert _title_jaccard("hello", None) == 0.0
