from datetime import datetime

import pandas as pd
from geopandas import GeoDataFrame

from velea import Area


class EligibilityAnalysis:
    def __init__(
        self,
        base_area: Area,
        included_areas=None,
        excluded_areas=None,
        restricted_areas=None,
        sliver_threshold=100,
    ):
        self.base_area = base_area
        self.base_area_gdf = None

        if excluded_areas is None:
            excluded_areas = []
        self.excludes = excluded_areas
        if included_areas is None:
            included_areas = []
        self.includes = included_areas
        if restricted_areas is None:
            restricted_areas = []
        self.restricted = restricted_areas

        self.include_gdf = None
        self.exclude_gdf = None
        self.restricted_gdf = None

        self.sliver_threshold = sliver_threshold

    def execute(self) -> tuple[GeoDataFrame, GeoDataFrame]:
        self.base_area_gdf = self.base_area.prepare()

        print(f"Start preparing: {datetime.now()}\n")
        self.exclude_gdf = self.concat_areas(self.excludes)
        self.include_gdf = self.concat_areas(self.includes)
        self.restricted_gdf = self.concat_areas(self.restricted)

        print(f"Start ensuring poylgons: {datetime.now()}\n")
        polygon_exclude_gdf = self.ensure_polygons(self.exclude_gdf)
        polygon_include_gdf = self.ensure_polygons(self.include_gdf)
        polygon_restricted_gdf = self.ensure_polygons(self.restricted_gdf)

        print(f"Start overlaying excluded areas: {datetime.now()}\n")
        if not polygon_exclude_gdf.empty:
            all_eligible_areas_gdf = polygon_include_gdf.overlay(
                polygon_exclude_gdf, how="difference"
            )
            polygon_all_eligible_areas_gdf = self.ensure_polygons(
                all_eligible_areas_gdf
            )
        else:
            polygon_all_eligible_areas_gdf = polygon_include_gdf

        print(f"Start overlaying restricted areas: {datetime.now()}\n")
        if not polygon_restricted_gdf.empty:
            eligible_gdf = polygon_all_eligible_areas_gdf.overlay(
                polygon_restricted_gdf, how="difference"
            )
            polygon_eligible_gdf = self.ensure_polygons(eligible_gdf)
        else:
            polygon_eligible_gdf = polygon_all_eligible_areas_gdf

        if not polygon_eligible_gdf.empty:
            restricted_areas_gdf = polygon_all_eligible_areas_gdf.overlay(
                polygon_eligible_gdf, how="difference"
            )
            polygon_restricted_areas_gdf = self.ensure_polygons(restricted_areas_gdf)
        else:
            polygon_restricted_areas_gdf = polygon_all_eligible_areas_gdf

        return (
            self.remove_slivers(polygon_eligible_gdf),
            self.remove_slivers(polygon_restricted_areas_gdf),
        )

    def concat_areas(self, list_of_areas: list[Area]) -> GeoDataFrame:
        gdfs = [area.prepare() for area in list_of_areas]
        if not gdfs:
            return GeoDataFrame()

        return GeoDataFrame(pd.concat(gdfs, ignore_index=True))

    def ensure_polygons(self, gdf: GeoDataFrame) -> GeoDataFrame:
        if gdf.empty:
            return gdf
        exploded_gdf = gdf.explode()
        return exploded_gdf[exploded_gdf.geom_type == "Polygon"]

    def remove_slivers(self, gdf: GeoDataFrame) -> GeoDataFrame:
        if gdf.empty:
            return gdf
        return gdf[gdf.area > self.sliver_threshold]
