import pytest
from geopandas import GeoSeries, GeoDataFrame
from shapely.geometry import Polygon

from velea import Area


@pytest.fixture
def base_areas(request):
    return GeoSeries(
        [
            Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
            Polygon([(2, 2), (4, 2), (4, 4), (2, 4)]),
        ]
    )


@pytest.fixture
def suitable_areas(request, base_areas) -> Area:
    return Area(
        GeoDataFrame({"col1": [1, 2], "geometry": base_areas}),
        "suitable_areas",
    )


@pytest.fixture
def suitable_areas_filter(request, base_areas) -> Area:
    return Area(
        GeoDataFrame({"col1": [1, 2], "geometry": base_areas}),
        "suitable_areas",
        query_filter="col1 == 1",
    )


@pytest.fixture
def suitable_areas_buffer(request, base_areas) -> Area:
    return Area(
        GeoDataFrame({"col1": [1, 2], "geometry": base_areas}),
        "suitable_areas",
        buffer_args={"distance": 1},
    )


@pytest.fixture
def suitable_areas_columns_to_keep(request, base_areas) -> Area:
    return Area(
        GeoDataFrame({"col1": [1, 2], "geometry": base_areas}),
        "suitable_areas",
        columns_to_keep=["col1"],
    )


@pytest.fixture
def suitable_areas_columns_to_keep_buffer(request, base_areas) -> Area:
    return Area(
        GeoDataFrame({"col1": [1, 2], "geometry": base_areas}),
        "suitable_areas",
        columns_to_keep=["col1"],
        buffer_args={"distance": 1},
    )


def test_no_filter(suitable_areas):
    assert suitable_areas.prepare().size == 2


def test_filter(suitable_areas_filter):
    assert suitable_areas_filter.prepare().size == 1


def test_drop_columns_buffer(suitable_areas_buffer):
    assert suitable_areas_buffer.prepare().columns == ["geometry"]


def test_keep_columns(suitable_areas_columns_to_keep):
    column_names = suitable_areas_columns_to_keep.prepare().columns
    intersection = column_names.intersection(
        ["geometry", *suitable_areas_columns_to_keep.columns_to_keep]
    )
    assert intersection.size == len(suitable_areas_columns_to_keep.columns_to_keep) + 1


def test_drop_columns_on_buffer(suitable_areas_columns_to_keep_buffer):
    with pytest.warns(
        UserWarning,
        match="columns_to_keep and buffer_args cannot be set at the same time.",
    ):
        assert suitable_areas_columns_to_keep_buffer.prepare().columns == ["geometry"]
