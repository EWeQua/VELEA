# VELEA


## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation

To install VELEA, we recommend to use the [conda](https://docs.conda.io/en/latest/) package manager. conda can be 
obtained by installing the [Anaconda Distribution](https://www.anaconda.com/distribution/) or
[miniconda](https://docs.anaconda.com/miniconda/). See the 
[Conda installation docs](https://conda.io/docs/user-guide/install/download.html>) for more information.

### Installing with conda

TODO:

    conda install velea
    
### Installing from source

    cd velea
    conda env create --file=environment-dev.yml
    conda activate velea

## Usage
Define the base area of your analysis as a dict with a `source` key pointing to file that can be read using 
[`geopandas.read_file`](https://geopandas.org/en/stable/docs/reference/api/geopandas.read_file.html) or directly using a 
[`GeoDataFrame`](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.html):
```python
base_area = {"source": "./input/RMK/base.shp"}
```
Next define areas that are eligible, eligible with restrictions and ineligible as lists of dicts in the same format. 
Optionally, areas can be buffered using the `buffer` key or filtered using a `where` key:
```python
eligible = [
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
ineligible = [
    {
        "source": "./input/RMK/exclude/Alle Straßen.shp", 
        "buffer": 2.5
     },
    {
        "source": "./input/RMK/exclude/Schienennetz.shp", 
        "buffer": 20},
    {
        "source": "./input/RMK/exclude/Biosphaerengebiet Kernzone.shp",
        "where": "ZONE = 'Kernzone'",
    },
]
eligible_with_restrictions = []
```
Using this input, you can run an eligibility analysis, also optionally specifying the coordinate reference system (crs)
as a `pyroj`-compliant string and a sliver threshold (the minimal size of returned areas in units of the crs). The 
output will be two `GeoDataFrames` containing the resulting eligible areas and the resulting eligible areas with 
restrictions.
```python
from velea import EligibilityAnalysis

eligible_areas, eligible_areas_with_restrictions = EligibilityAnalysis(
    base_area,
    eligible,
    ineligible,
    eligible_with_restrictions,
    sliver_threshold=100,
    crs="EPSG:25832",
).execute()
```
## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.
