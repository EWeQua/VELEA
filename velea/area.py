import warnings

from geopandas import GeoDataFrame


class Area:
    def __init__(
        self, source, name, query_filter=None, buffer_args=None, columns_to_keep=None
    ):
        self.source = source
        self.name = name
        self.filter = query_filter
        self.buffer_args = buffer_args
        self.columns_to_keep = columns_to_keep

    def prepare(self):
        if self.filter:
            filtered_gdf = self.source.query(self.filter)
        else:
            filtered_gdf = self.source

        if self.buffer_args is not None:
            unary_union = filtered_gdf.buffer(**self.buffer_args).unary_union
            geometry = [unary_union]
        else:
            geometry = filtered_gdf.geometry

        if self.columns_to_keep:
            if self.buffer_args is not None:
                warnings.warn("columns_to_keep and buffer_args cannot be set at the same time. "
                              "The parameter columns_to_keep is ignored")
                return GeoDataFrame(geometry=geometry)

            return GeoDataFrame(
                data=filtered_gdf[self.columns_to_keep], geometry=geometry
            )
        else:
            return GeoDataFrame(geometry=geometry)
