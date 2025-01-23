# VELEA - Vector-based Land Eligibility Analysis for Renewable Energy Sources

VELEA is an open-source tool, capable of performing land eligibility analysis for renewable energy sources.
The aim of VELEA is to simplify finding eligible areas, e.g., for constructing open-field PV or wind power plants, given
a base area, areas to include as eligible, areas to include as eligible with restrictions and areas to exclude as 
ineligible as vector-based geodata.
Therefore, VELEA can be seen as the vector-based counterpart to [GLAES](https://github.com/FZJ-IEK3-VSA/glaes).
As VELEA is based on [geopandas](https://github.com/geopandas/geopandas) it allows data input in any format supported by
geopandas.
Similar to GLAES input geodata can optionally be filtered and buffered before performing land eligibility analysis.
VELEA allows data input according to the input specification of GLAES to simplify migration or experiments with both 
tools.

## Installation

To install VELEA, we recommend to use the [conda](https://docs.conda.io/en/latest/) package manager. conda can be 
obtained by installing the [Anaconda Distribution](https://www.anaconda.com/distribution/) or
[miniconda](https://docs.anaconda.com/miniconda/). See the 
[Conda installation docs](https://conda.io/docs/user-guide/install/download.html>) for more information.

### Installing with conda

    conda install swifmaneum::velea
    
### Installing from source

    cd velea
    conda env create --file=environment-dev.yml
    conda activate velea

## Usage
### Illustrative example
For a self-contained simplified example (the illustrative example used in the paper) see [example.py](/velea/example.py).

### Using VELEA with your own (real-world) data
Define the base area of your analysis as a dict with a `source` key pointing to file that can be read using 
[`geopandas.read_file`](https://geopandas.org/en/stable/docs/reference/api/geopandas.read_file.html) or directly using a 
[`GeoDataFrame`](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.html):
```python
base_area = {"source": "./input/RMK/base.shp"}
```
Next define included areas, excluded areas and restricted areas as lists of dicts in the same format. 
Optionally, areas can be buffered using the `buffer` key or filtered using a `where` key:
```python
included_areas = [
    {
        "source": "./input/RMK/include/Benachteiligte Gebiete.shp",
    },
    {
        "source": "./input/RMK/include/Deponie.shp",
        "where": "zustand = '2100' and funktion = '8100'",
    },
    {
        "source": "./input/RMK/include/Schienennetz.shp",
        "buffer": 120,
    },
]
excluded_areas = [
    {
        "source": "./input/RMK/exclude/Alle Straßen.shp", 
        "buffer": 2.5
     },
    {
        "source": "./input/RMK/exclude/Schienennetz.shp", 
        "buffer": 20
    },
    {
        "source": "./input/RMK/exclude/Biosphaerengebiet Kernzone.shp",
        "where": "ZONE = 'Kernzone'",
    },
]
restricted_areas = []
```
Using this input, you can run an eligibility analysis, also optionally specifying the coordinate reference system (crs)
as a `pyroj`-compliant string and a sliver threshold (the minimal size of returned areas in units of the crs). The 
output will be two `GeoDataFrames` containing the resulting eligible areas and the resulting eligible areas with 
restrictions.

```python
from velea import EligibilityAnalysis

eligible_areas, eligible_areas_with_restrictions = EligibilityAnalysis(
    base_area,
    included_areas,
    excluded_areas,
    restricted_areas,
    sliver_threshold=100,
    crs="EPSG:25832",
).run()
```
### Using raster data
Using raster data is not supported in VELEA natively. However, you can simply vectorize your raster data, e.g., using 
[rasterio](https://github.com/rasterio/rasterio) and use the resulting vector-data. For example use or adapt the 
following function from VELEA-eval that reads a raster file provided by its path and creates a `GeoDataFrame` from all 
shapes where the value of the first band equals 100:
```python
import rasterio
from geopandas import GeoDataFrame
from rasterio.features import shapes

def vectorize(path: str) -> GeoDataFrame:
    # Inspired by https://gis.stackexchange.com/questions/187877/how-to-polygonize-raster-to-shapely-polygons
    with rasterio.Env():
        with rasterio.open(path) as src:
            image = src.read(1)  # first band
            geoms = [
                {"properties": {"raster_val": v}, "geometry": s}
                for _, (s, v) in enumerate(shapes(image, transform=src.transform))
                # We're only interested in the eligible areas (v == 100) --> drop other values
                if v == 100
            ]
    return GeoDataFrame.from_features(geoms, crs="EPSG:25832")
```

## Acknowledgments
This work was funded by the Bavarian State Ministry of Science and the Arts to promote applied research and development 
at universities of applied sciences and technical universities.