import pytest
from geopandas import GeoSeries, GeoDataFrame
from shapely.geometry import Polygon

from velea import EligibilityAnalysis


@pytest.fixture
def base_area(request):
    s1 = GeoSeries(
        [
            Polygon([(0, 0), (4, 0), (4, 4), (0, 4)]),
        ]
    )
    return {"source": GeoDataFrame(geometry=s1)}


@pytest.fixture
def suitable_areas(request):
    s1 = GeoSeries(
        [
            Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
            Polygon([(2, 2), (4, 2), (4, 4), (2, 4)]),
        ]
    )
    return {"source": GeoDataFrame({"col1": [1, 2], "geometry": s1})}


@pytest.fixture
def unsuitable_areas(request):
    s1 = GeoSeries(
        [
            Polygon([(1, 1), (3, 1), (3, 3), (1, 3)]),
        ]
    )
    return {"source": GeoDataFrame(geometry=s1)}


@pytest.fixture
def restricted_areas(request):
    s1 = GeoSeries(
        [
            Polygon([(2, 0), (4, 0), (4, 2), (2, 2)]),
        ]
    )
    return {"source": GeoDataFrame(geometry=s1)}


def test_empty_suitable(base_area):
    base = base_area
    analysis = EligibilityAnalysis(
        base_area=base,
        included_areas=None,
        excluded_areas=None,
        restricted_areas=None,
        sliver_threshold=0,
    )
    eligible_areas, restricted_areas = analysis.execute()
    assert eligible_areas.empty


def test_sum_suitable(base_area, suitable_areas):
    base = base_area
    suitable = suitable_areas
    analysis = EligibilityAnalysis(
        base_area=base,
        included_areas=[suitable],
        excluded_areas=None,
        restricted_areas=None,
        sliver_threshold=0,
    )
    eligible_areas, restricted_areas = analysis.execute()
    assert eligible_areas.area.sum() == 8


def test_empty_restricted(base_area, suitable_areas):
    base = base_area
    suitable = suitable_areas
    analysis = EligibilityAnalysis(
        base_area=base,
        included_areas=[suitable],
        excluded_areas=None,
        restricted_areas=None,
        sliver_threshold=0,
    )
    eligible_areas, restricted_areas = analysis.execute()
    assert restricted_areas.area.sum() == 0


def test_empty_restricted_with_excluded(base_area, suitable_areas, unsuitable_areas):
    base = base_area
    suitable = suitable_areas
    unsuitable = unsuitable_areas
    analysis = EligibilityAnalysis(
        base_area=base,
        included_areas=[suitable],
        excluded_areas=[unsuitable],
        restricted_areas=[],
        sliver_threshold=0,
    )
    eligible_areas, restricted_areas = analysis.execute()
    assert restricted_areas.area.sum() == 0


def test_sum_buffer_suitable(base_area, suitable_areas):
    base = base_area
    suitable = suitable_areas
    suitable["buffer_args"] = {
        "distance": 1,
        "cap_style": "square",
        "join_style": "mitre",
    }
    analysis = EligibilityAnalysis(
        base_area=base,
        included_areas=[suitable],
        excluded_areas=[],
        restricted_areas=[],
        sliver_threshold=0,
    )
    eligible_areas, restricted_areas = analysis.execute()
    assert eligible_areas.area.sum() == 28


def test_sum(base_area, suitable_areas, unsuitable_areas):
    base = base_area
    suitable = suitable_areas
    unsuitable = unsuitable_areas
    analysis = EligibilityAnalysis(
        base_area=base,
        included_areas=[suitable],
        excluded_areas=[unsuitable],
        restricted_areas=[],
        sliver_threshold=0,
    )
    eligible_areas, restricted_areas = analysis.execute()
    assert eligible_areas.area.sum() == 6


def test_sum_difference_buffer(base_area, suitable_areas, unsuitable_areas):
    base = base_area
    suitable = suitable_areas
    unsuitable = unsuitable_areas
    unsuitable.buffer_args = {
        "distance": 1,
        "cap_style": "square",
        "join_style": "mitre",
    }
    analysis = EligibilityAnalysis(
        base_area=base,
        included_areas=[suitable],
        excluded_areas=[unsuitable],
        restricted_areas=[],
        sliver_threshold=0,
    )
    eligible_areas, restricted_areas = analysis.execute()
    assert eligible_areas.area.sum() == 0


def test_sum_difference_buffer_restricted(base_area, suitable_areas, unsuitable_areas):
    base = base_area
    suitable = suitable_areas
    restricted = unsuitable_areas
    restricted.buffer_args = {
        "distance": 1,
        "cap_style": "square",
        "join_style": "mitre",
    }
    analysis = EligibilityAnalysis(
        base_area=base,
        included_areas=[suitable],
        excluded_areas=[],
        restricted_areas=[restricted],
        sliver_threshold=0,
    )
    eligible_areas, restricted_areas = analysis.execute()
    assert eligible_areas.area.sum() == 0
    assert restricted_areas.area.sum() == 8


def test_linstring_overlap_is_empty(base_area, suitable_areas, restricted_areas):
    base = base_area
    suitable = suitable_areas
    restricted = restricted_areas
    analysis = EligibilityAnalysis(
        base_area=base,
        included_areas=[suitable],
        excluded_areas=[],
        restricted_areas=[restricted],
        sliver_threshold=0,
    )
    eligible_areas, restricted_areas = analysis.execute()
    assert eligible_areas.area.sum() == 8
    assert restricted_areas.area.sum() == 0
    assert restricted_areas.empty
