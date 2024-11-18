import warnings
from datetime import datetime

import geopandas as gpd
import pandas as pd
from geopandas import GeoDataFrame, GeoSeries
from pyproj import CRS


class EligibilityAnalysis:
    def __init__(
        self,
        base_area: dict,
        included_areas=None,
        excluded_areas=None,
        restricted_areas=None,
        sliver_threshold=None,
        crs: CRS | str = None,
    ):
        self.base_area = base_area
        self.base_area_gdf = None

        self.excluded_areas, self.included_areas, self.restricted_areas = [
            area if area is not None else []
            for area in [excluded_areas, included_areas, restricted_areas]
        ]

        self.include_gdf = None
        self.exclude_gdf = None
        self.restricted_gdf = None

        self.sliver_threshold = sliver_threshold
        self.crs = crs

    def run(self) -> tuple[GeoDataFrame, GeoDataFrame]:
        self.base_area_gdf = self.read_source(self.base_area)

        print(f"Start preprocessing: {datetime.now()}\n")
        self.exclude_gdf, self.include_gdf, self.restricted_gdf = [
            self.preprocess(areas)
            for areas in [
                self.excluded_areas,
                self.included_areas,
                self.restricted_areas,
            ]
        ]

        print(f"Start overlaying excluded areas: {datetime.now()}\n")
        all_eligible_areas = self.overlay_non_empty(
            self.include_gdf, self.exclude_gdf, how="difference"
        )

        print(f"Start overlaying restricted areas: {datetime.now()}\n")
        eligible_areas = self.overlay_non_empty(
            all_eligible_areas, self.restricted_gdf, how="difference"
        )

        eligible_areas_with_restrictions = self.overlay_non_empty(
            all_eligible_areas, eligible_areas, how="difference"
        )

        return (
            self.remove_slivers(eligible_areas),
            self.remove_slivers(eligible_areas_with_restrictions),
        )

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

        else:
            source = gpd.read_file(source, where=where)

        return self.ensure_crs(source)

    def preprocess(self, list_of_areas: list[dict]) -> GeoDataFrame:
        gdfs = []
        for area_dict in list_of_areas:
            gdf = self.read_source(area_dict)

            buffer = None
            if "buffer" in area_dict:
                buffer = area_dict["buffer"]

            buffer_args = None
            if "buffer_args" in area_dict:
                buffer_args = area_dict["buffer_args"]

            if buffer or buffer_args:
                warnings.warn(
                    f"Applying buffer to {area_dict['source']}, data columns are dropped"
                )
                gdf = GeoDataFrame(
                    geometry=self.apply_buffer(gdf, buffer, buffer_args), crs=self.crs
                )
            clipped_gdf = gdf.clip(self.base_area_gdf)
            clipped_polygon_gdf = self.ensure_polygons(clipped_gdf)
            gdfs.append(clipped_polygon_gdf)

        if not gdfs:
            return self.ensure_crs(GeoDataFrame())

        return self.ensure_crs(GeoDataFrame(pd.concat(gdfs, ignore_index=True)))

    def apply_buffer(
        self, gdf: GeoDataFrame, buffer: dict, buffer_args: dict
    ) -> GeoSeries:
        # No buffer required -> return the gdf geometry unchanged
        if not buffer and not buffer_args:
            return gdf.geometry

        if buffer and buffer_args:
            warnings.warn(
                "buffer and buffer_args cannot be set at the same time. "
                "The parameter buffer is ignored"
            )
        if buffer:
            unary_union = gdf.buffer(buffer).unary_union
        elif buffer_args:
            unary_union = gdf.buffer(**buffer_args).unary_union
        else:
            raise
        return GeoSeries([unary_union], crs=self.crs)

    def ensure_crs(self, gdf: GeoDataFrame | GeoSeries) -> GeoDataFrame | GeoSeries:
        if gdf.empty or not self.crs:
            return gdf

        if gdf.crs:
            return gdf.to_crs(self.crs)
        else:
            return gdf.set_crs(self.crs)

    def ensure_polygons(
        self, gdf: GeoDataFrame | GeoSeries
    ) -> GeoDataFrame | GeoSeries:
        if gdf.empty:
            return gdf
        exploded_gdf = gdf.explode()
        return exploded_gdf[exploded_gdf.geom_type == "Polygon"]

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

    def remove_slivers(self, gdf: GeoDataFrame) -> GeoDataFrame:
        if gdf.empty or not self.sliver_threshold:
            return gdf
        return gdf[gdf.area > self.sliver_threshold]
