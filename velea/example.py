import matplotlib.pyplot as plt
from geopandas import GeoDataFrame, GeoSeries
from shapely.geometry import box, Polygon

from velea import EligibilityAnalysis

# Rebuild of the illustrative example in the paper
# The situations after (a) Data input and (e) Post-processing are plotted

# Area definitions:
# Base area, displayed in blue
base = {
    "source": GeoDataFrame(
        geometry=GeoSeries(
            [
                box(1, 0, 6, 6),
            ]
        )
    )
}

# Included area, displayed in green
included = {
    "source": GeoDataFrame(
        geometry=GeoSeries(
            [
                Polygon(((0, 4), (0, 5), (3, 5), (6, 5), (6, 4), (3, 1), (0, 4))),
            ]
        )
    )
}

# Excluded area on the left, displayed in red, requires a rectangular buffer of 1 unit
excluded_left = {
    "source": GeoDataFrame(
        geometry=GeoSeries(
            [
                box(1, 1, 2, 2),
            ]
        )
    ),
    "buffer_args": {
        "distance": 1,
        "cap_style": "square",
        "join_style": "mitre",
    },
}

# Excluded area on the right, displayed in red
excluded_right = {
    "source": GeoDataFrame(
        geometry=GeoSeries(
            [
                box(4, 0, 5, 6),
            ]
        )
    )
}

# Plot the initial situation after (a) Data input
ax = base["source"].plot(color="blue", edgecolor="black", alpha=0.4)
included["source"].plot(ax=ax, color="green", edgecolor="black", alpha=0.4)
excluded_right["source"].plot(ax=ax, color="red", edgecolor="black", alpha=0.4)
excluded_left["source"].plot(ax=ax, color="red", edgecolor="black", alpha=0.4)
plt.show()

# Setup and run the eligibility analysis
# Note the sliver_threshold of 2 to remove the small resulting eligible area at the right
analysis = EligibilityAnalysis(
    base_area=base,
    included_areas=[included],
    excluded_areas=[excluded_left, excluded_right],
    restricted_areas=None,
    sliver_threshold=2,
)
eligible_areas, restricted_areas = analysis.run()

# Plot the resulting eligible areas after (e) Post-processing in green
eligible_areas.plot(color="green", edgecolor="black", alpha=0.8)
plt.show()
