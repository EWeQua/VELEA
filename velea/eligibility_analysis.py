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
        """
        Initialize EligibilityAnalysis object.

        :param base_area: The base area of interest. All results will be clipped to the extent of this area. E.g.
        {"source": "path/base.shp"}.
        :type base_area: dict
        :param included_areas: A list of areas to be included as eligible areas if they do not overlap with areas to
        exclude. E.g. [{"source": "path/to/include.shp", "buffer": 1000}, {"source": "path/to/include2.shp"},]. If the
        whole base area is to be included, input the base area wrapped in a list.
        :type included_areas: list[dict]
        :param excluded_areas: A list of areas to be excluded as ineligible. E.g.
        [{"source": "path/to/exclude.shp", "buffer": 100}, {"source": "path/to/exclude2.shp"},]
        :type excluded_areas: list[dict]
        :param restricted_areas: A list of areas to be included as eligible areas with restriction if they do not
        overlap with areas to exclude E.g. [{"source": "path/to/restricted.shp", "buffer": 100}]
        :type restricted_areas: list[dict]
        :param sliver_threshold: The size of areas to be removed in units of the chosen coordinate reference system.
        E.g. 100 to drop geometries smaller than 100 units of the chosen coordinate reference system or 0 to keep all
        geometries.
        :type sliver_threshold: float
        :param crs: The coordinate reference system to use as a pyproj-compliant string or pyproj CRS. E.g. "EPSG:4326"
        :type crs: CRS | str
        """
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
        """
        Main function of EligibilityAnalysis to be called after initialization. It contains the preprocessing,
        overlaying excluded nad restricted areas and sliver removal. The results are returned as a tuple of
        GeoDataFrames where the first item contains the eligible areas and the second item contains the
        eligible areas with restrictions.

        :return: The results of EligibilityAnalysis as a tuple of GeoDataFrames (eligible_areas,
        eligible_areas_with_restrictions).
        :rtype: tuple[GeoDataFrame, GeoDataFrame]
        """
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
        """
        Reads and filters the given area_dict and returns the result as a GeoDataFrame in the correct crs.

        :param area_dict:A dictionary containing (paths to) geodata alongside buffer and filter options. E.g.
        {"source": "path/file.shp", "buffer": 10,"where": "GFK not in ('31001_1313')"}
        :type area_dict: dict
        :return:The resulting geodata in a GeoDataFrame.
        :rtype: GeoDataFrame
        """
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
        """
        Reads and filters the given list_of_areas, calls applies the required buffers, clips the result to the base area
        and then drops any non-polygon geometry resulting from the aforementioned processes. The results are concat into
        a single GeoDataFrame and returned as such.

        :param list_of_areas: A list of dictionaries containing (paths to) geodata alongside buffer and filter options.
        E.g. [{"source": "path/to/shapefile.shp", "buffer": 1000}, {"source": "path/to/another.shp"},]
        :type list_of_areas: list[dict]
        :return: The resulting geodata in a GeoDataFrame.
        :rtype: GeoDataFrame
        """
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
        self, gdf: GeoDataFrame, buffer: float, buffer_args: dict
    ) -> GeoSeries:
        """
        Applies a buffer specified by buffer or buffer_args to the given GeoDataFrame and returns the buffered
        geometries after performing a unary_union to prevent overlapping as a GeoSeries. If both buffer and buffer_args
        are set, a warning is raised.

        :param gdf: The GeoDataFrame to be buffered.
        :type gdf: GeoDataFrame
        :param buffer: The buffer size to be applied in units of the crs.
        :type buffer: float
        :param buffer_args: A dictionary with arguments to pass to the GeoDataFrame.buffer() method after unpacking.
        :type buffer_args: dict
        :return: The buffered and unioned geometries as a GeoSeries.
        :rtype: GeoSeries
        """
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
        """
        Ensure that the GeoDataFrame or GeoSeries has the correct Coordinate Reference System (CRS).

        If the input GeoDataFrame or GeoSeries is empty or `self.crs` is not set, it returns the input as is.
        Otherwise, if the input GeoDataFrame or GeoSeries has a CRS set, it projects the input to the specified CRS
        in `self.crs` using `GeoDataFrame.to_crs()`. If the input GeoDataFrame or GeoSeries has no CRS set, it
        sets the input to the specified CRS in `self.crs` using `GeoDataFrame.set_crs()`.

        :param gdf: The input GeoDataFrame or GeoSeries.
        :type gdf: GeoDataFrame | GeoSeries
        :return: A GeoDataFrame or GeoSeries with the specified CRS.
        :rtype: GeoDataFrame | GeoSeries
        """
        if gdf.empty or not self.crs:
            return gdf

        if gdf.crs:
            return gdf.to_crs(self.crs)
        else:
            return gdf.set_crs(self.crs)

    def ensure_polygons(
        self, gdf: GeoDataFrame | GeoSeries
    ) -> GeoDataFrame | GeoSeries:
        """
        Ensure that the geometries in the GeoDataFrame or GeoSeries are polygons by exploding the contained geometries
        and dropping non-polygon geometries.

        :param gdf: The input GeoDataFrame or GeoSeries.
        :type gdf: GeoDataFrame | GeoSeries
        :return: The input GeoDataFrame or GeoSeries with exploded geometries and only containing polygon geometries.
        :rtype: GeoDataFrame | GeoSeries
        """
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
        """
        Perform an overlay operation on two GeoDataFrames if the second GeoDataFrame is not empty. This method extends
        the GeoPandas `GeoDataFrame.overlay` method by ensuring that the overlay operation is only performed if the
        second GeoDataFrame (`df2`) is not empty. Additionally, it ensures that the resulting GeoDataFrame only contains
        polygons geometries.

        :param df1: The first GeoDataFrame.
        :type df1: GeoDataFrame
        :param df2: The second GeoDataFrame.
        :type df2: GeoDataFrame
        :param how: The type of overlay operation to perform: 'intersection', 'union', 'identity',
        'symmetric_difference' or 'difference'.
        :type how: str
        :param keep_geom_type:  If True, return only geometries of the same geometry type the GeoDataFrame has, if
        False, return all resulting geometries. Defaults to True.
        :type keep_geom_type: bool, optional
        :param make_valid: If True, any invalid input geometries are corrected with a call to make_valid(), if False, a
        `ValueError` is raised if any input geometries are invalid. Defaults to True.
        :type make_valid: bool, optional
        :return: The result of the overlay operation, ensuring only polygons are returned.
        :rtype: GeoDataFrame
        """
        if df2.empty:
            return df1
        else:
            overlay = df1.overlay(
                df2, how=how, keep_geom_type=keep_geom_type, make_valid=make_valid
            )
            return self.ensure_polygons(overlay)

    def remove_slivers(self, gdf: GeoDataFrame) -> GeoDataFrame:
        """
        Remove small geometries (slivers) from a GeoDataFrame based on a specified area threshold
        (`self.sliver_threshold`).

        :param gdf: The input GeoDataFrame.
        :type gdf: GeoDataFrame
        :return: A GeoDataFrame with geometries smaller than `self.sliver_threshold` removed.
        :rtype: GeoDataFrame
        """
        if gdf.empty or not self.sliver_threshold:
            return gdf
        return gdf[gdf.area > self.sliver_threshold]
