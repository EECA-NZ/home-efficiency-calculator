"""
Generate a lookup table from postcode to electricity and gas plans.

As a side effect, generate some data visualizations.
"""

import fiona
import pyproj
from pyproj import CRS
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.ops import transform
from shapely.geometry import shape
import pandas as pd


EDB_REGION_SHAPEFILE = "../supplementary_data/EDB_Boundaries/EDBBoundaries.shp"
POSTCODE_SHAPEFILE = "../supplementary_data/PNF_V2024Q2_V01/PN_V2024Q2V01_POLYGONS.shp"


# Functions
def adjust_longitude(x, y):
    """Adjust longitudes to be within [0, 360]."""
    if x < 0:
        x += 360
    return x, y

def load_and_transform_shapefile(shapefile_path):
    """
    Load the shapefile, transform geometries to WGS84, and adjust longitudes.
    Returns a GeoDataFrame.
    """
    with fiona.open(shapefile_path, "r") as shapefile:
        # Get CRS from source shapefile
        source_crs = shapefile.crs
        target_crs = CRS("EPSG:4326")  # WGS84

        # Prepare transformer to convert source CRS to WGS84
        transformer = pyproj.Transformer.from_crs(
            source_crs, target_crs, always_xy=True
        )

        geometries = []
        properties_list = []
        for feature in shapefile:
            geometry = shape(feature["geometry"])
            # Transform geometry to WGS84
            transformed_geometry = transform(transformer.transform, geometry)
            # Adjust longitudes
            adjusted_geometry = transform(adjust_longitude, transformed_geometry)
            geometries.append(adjusted_geometry)
            properties = feature["properties"]
            properties_list.append(properties)

        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(
            properties_list, geometry=geometries, crs=target_crs.to_string()
        )

        return gdf

def plot_maps(postcode_gdf, climate_zones_gdf, figname):
    """
    Plot the postcode and climate zone boundaries as two subplots.
    """
    print("Plotting postcode and climate zone boundaries...")
    # Reproject to WGS84 for plotting
    postcode_gdf_plot = postcode_gdf.to_crs(epsg=4326)
    edb_zones_gdf_plot = climate_zones_gdf.to_crs(epsg=4326)

    _, axes = plt.subplots(1, 2, figsize=(20, 10))

    # Plot postcode boundaries
    postcode_gdf_plot.plot(ax=axes[0], color="none", edgecolor="blue", linewidth=0.5)
    axes[0].set_title("New Zealand Postcode Boundaries")
    axes[0].set_xlabel("Longitude")
    axes[0].set_ylabel("Latitude")

    # Plot EDB zones with distinct colors and a legend
    edb_zones_gdf_plot.plot(
        ax=axes[1],
        column="name",
        cmap="tab20",
        alpha=0.5,
        legend=True,
        edgecolor="black",
        linewidth=0.5,
    )
    axes[1].set_title("Electricity Distribution Board Boundaries")
    axes[1].set_xlabel("Longitude")
    axes[1].set_ylabel("Latitude")

    # Adjust legend
    leg = axes[1].get_legend()
    leg.set_bbox_to_anchor((1.15, 1))  # Position the legend outside the plot
    leg.set_title("EDB Regions")

    # Adjust layout and save the plot
    plt.tight_layout()
    plt.savefig(figname)
    plt.close()



print("Loading and transforming postcode shapefile...")
my_postcode_gdf = load_and_transform_shapefile(POSTCODE_SHAPEFILE)

print("Loading and transforming EDB boundaries shapefile...")
my_edb_boundaries_gdf = load_and_transform_shapefile(EDB_REGION_SHAPEFILE)

print("Loading tariff data...")
my_tariff_data = pd.read_csv("../supplementary_data/tariff_data/tariffDataReport_240903.csv")

plot_maps(my_postcode_gdf, my_edb_boundaries_gdf, "output/postcode_edb_boundaries.png")
