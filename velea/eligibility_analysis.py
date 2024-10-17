import warnings
from datetime import datetime

import pandas as pd
from geopandas import GeoDataFrame
import geopandas as gpd


class EligibilityAnalysis:
    def __init__(
        self,
        base_area: dict,
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
        self.base_area_gdf = self.read_source(self.base_area)

        print(f"Start preparing: {datetime.now()}\n")
        self.exclude_gdf = self.prepare_areas(self.excludes)
        self.include_gdf = self.prepare_areas(self.includes)
        self.restricted_gdf = self.prepare_areas(self.restricted)

        print(f"Start ensuring poylgons: {datetime.now()}\n")
        polygon_exclude_gdf = self.ensure_polygons(self.exclude_gdf)
        polygon_include_gdf = self.ensure_polygons(self.include_gdf)
        polygon_restricted_gdf = self.ensure_polygons(self.restricted_gdf)

        print(f"Start overlaying excluded areas: {datetime.now()}\n")
        polygon_all_eligible_areas_gdf = self.overlay_non_empty(
            polygon_include_gdf, polygon_exclude_gdf, how="difference"
        )

        print(f"Start overlaying restricted areas: {datetime.now()}\n")
        polygon_eligible_gdf = self.overlay_non_empty(
            polygon_all_eligible_areas_gdf, polygon_restricted_gdf, how="difference"
        )

        polygon_restricted_areas_gdf = self.overlay_non_empty(
            polygon_all_eligible_areas_gdf, polygon_eligible_gdf, how="difference"
        )

        return (
            self.remove_slivers(polygon_eligible_gdf),
            self.remove_slivers(polygon_restricted_areas_gdf),
        )

    def overlay_non_empty(
        self,
        df1: GeoDataFrame,
        df2: GeoDataFrame,
        how: str,
        keep_geom_type: bool = True,
        make_valid: bool = True,
    ) -> GeoDataFrame:
        if df2.empty:
            return df1
        else:
            overlay = df1.overlay(
                df2, how=how, keep_geom_type=keep_geom_type, make_valid=make_valid
            )
            return self.ensure_polygons(overlay)

    def prepare_areas(self, list_of_areas: list[dict]) -> GeoDataFrame:
        gdfs = []
        for area_dict in list_of_areas:

            buffer = None
            if "buffer" in area_dict:
                buffer = area_dict["buffer"]

            buffer_args = None
            if "buffer_args" in area_dict:
                buffer_args = area_dict["buffer_args"]

            columns_to_keep = None
            if "columns_to_keep" in area_dict:
                columns_to_keep = area_dict["columns_to_keep"]

            gdf = self.read_source(area_dict)

            if buffer:
                unary_union = gdf.buffer(buffer).unary_union
                geometry = [unary_union]
            elif buffer_args:
                unary_union = gdf.buffer(**buffer_args).unary_union
                geometry = [unary_union]
            else:
                geometry = gdf.geometry

            if columns_to_keep:
                if buffer:
                    warnings.warn(
                        "columns_to_keep and buffer cannot be set at the same time. "
                        "The parameter columns_to_keep is ignored"
                    )
                    gdf = GeoDataFrame(geometry=geometry)
                else:
                    gdf = GeoDataFrame(data=gdf[columns_to_keep], geometry=geometry)
            else:
                gdf = GeoDataFrame(geometry=geometry)
            gdfs.append(gdf)

        if not gdfs:
            return GeoDataFrame()

        return GeoDataFrame(pd.concat(gdfs, ignore_index=True))

    def read_source(self, area_dict: dict) -> GeoDataFrame:
        assert "source" in area_dict
        source = area_dict["source"]

        where = None
        if "where" in area_dict:
            where = area_dict["where"]

        if isinstance(source, GeoDataFrame):
            if where:
                warnings.warn(
                    "'where' filter is ignored when passing a GeoDataFrame as 'source'."
                )
            return source
        else:
            return gpd.read_file(source, where=where)

    def ensure_polygons(self, gdf: GeoDataFrame) -> GeoDataFrame:
        if gdf.empty:
            return gdf
        exploded_gdf = gdf.explode()
        return exploded_gdf[exploded_gdf.geom_type == "Polygon"]

    def remove_slivers(self, gdf: GeoDataFrame) -> GeoDataFrame:
        if gdf.empty:
            return gdf
        return gdf[gdf.area > self.sliver_threshold]
