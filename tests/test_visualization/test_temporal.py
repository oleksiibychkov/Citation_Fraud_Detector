"""Tests for temporal visualization charts."""

from datetime import date

from cfd.analysis.baselines import DisciplineBaseline
from cfd.analysis.pipeline import AnalysisResult
from cfd.data.models import AuthorData, AuthorProfile, Citation, Publication
from cfd.graph.metrics import IndicatorResult
from cfd.visualization.temporal import build_baseline_overlay, build_ht_nt_figure, build_spike_chart


def _make_profile(**overrides):
    defaults = {"surname": "Test", "full_name": "Test Author", "source_api": "openalex"}
    defaults.update(overrides)
    return AuthorProfile(**defaults)


def _make_baseline():
    return DisciplineBaseline(
        discipline="Computer Science", avg_scr=0.12, std_scr=0.08,
        avg_citations_per_paper=8.5, citation_half_life_years=5.5,
    )


class TestBuildHtNtFigure:
    def test_no_data(self):
        ad = AuthorData(profile=_make_profile(), publications=[], citations=[])
        fig = build_ht_nt_figure(ad)
        assert "no temporal data" in fig.layout.title.text.lower()

    def test_with_publications(self):
        pubs = [
            Publication(work_id=f"W{i}", citation_count=10 * i, source_api="openalex",
                        publication_date=date(2018 + i, 6, 1))
            for i in range(1, 6)
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        fig = build_ht_nt_figure(ad)
        data_dict = fig.to_dict()
        # Should have 2 traces (cumulative citations + cumulative publications)
        assert len(data_dict["data"]) == 2

    def test_dual_axis(self):
        pubs = [
            Publication(work_id="W1", citation_count=10, source_api="openalex",
                        publication_date=date(2020, 1, 1)),
        ]
        cits = [
            Citation(source_work_id="E1", target_work_id="W1",
                     citation_date=date(2021, 1, 1),
                     source_author_id=2, target_author_id=1,
                     is_self_citation=False, source_api="openalex"),
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=cits)
        fig = build_ht_nt_figure(ad)
        # Plotly subplots with secondary_y create yaxis2
        layout = fig.to_dict()["layout"]
        assert "yaxis2" in layout


class TestBuildSpikeChart:
    def test_no_temporal_data(self):
        profile = _make_profile()
        result = AnalysisResult(author_profile=profile, indicators=[])
        ad = AuthorData(profile=profile, publications=[], citations=[])
        fig = build_spike_chart(ad, result)
        assert "no temporal data" in fig.layout.title.text.lower()

    def test_with_ta_details(self):
        profile = _make_profile()
        ta = IndicatorResult("TA", 0.6, {
            "yearly_counts": {"2019": 10, "2020": 12, "2021": 50, "2022": 15},
            "spike_year": 2021,
            "max_z_score": 3.5,
        })
        result = AnalysisResult(author_profile=profile, indicators=[ta])
        ad = AuthorData(profile=profile, publications=[], citations=[])
        fig = build_spike_chart(ad, result)
        data_dict = fig.to_dict()
        # Should have bar trace
        bar_traces = [t for t in data_dict["data"] if t.get("type") == "bar"]
        assert len(bar_traces) == 1
        assert len(bar_traces[0]["x"]) == 4

    def test_spike_year_highlighted(self):
        profile = _make_profile()
        ta = IndicatorResult("TA", 0.6, {
            "yearly_counts": {"2019": 5, "2020": 5, "2021": 100, "2022": 5},
            "spike_year": 2021,
        })
        result = AnalysisResult(author_profile=profile, indicators=[ta])
        ad = AuthorData(profile=profile, publications=[], citations=[])
        fig = build_spike_chart(ad, result)
        data_dict = fig.to_dict()
        bar_trace = [t for t in data_dict["data"] if t.get("type") == "bar"][0]
        colors = bar_trace["marker"]["color"]
        # Spike year should be red (critical color)
        assert "#c0392b" in colors


class TestBuildBaselineOverlay:
    def test_no_data(self):
        ad = AuthorData(profile=_make_profile(), publications=[], citations=[])
        fig = build_baseline_overlay(ad, _make_baseline())
        assert "no data" in fig.layout.title.text.lower()

    def test_with_publications(self):
        pubs = [
            Publication(work_id=f"W{i}", citation_count=10 * i, source_api="openalex",
                        publication_date=date(2020 - i, 6, 1))
            for i in range(1, 6)
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        fig = build_baseline_overlay(ad, _make_baseline())
        data_dict = fig.to_dict()
        # Should have 2 traces (author + baseline)
        assert len(data_dict["data"]) == 2

    def test_baseline_discipline_in_title(self):
        pubs = [
            Publication(work_id="W1", citation_count=10, source_api="openalex",
                        publication_date=date(2020, 1, 1)),
        ]
        ad = AuthorData(profile=_make_profile(), publications=pubs, citations=[])
        baseline = _make_baseline()
        fig = build_baseline_overlay(ad, baseline)
        assert baseline.discipline in fig.layout.title.text
