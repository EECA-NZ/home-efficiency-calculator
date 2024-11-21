"""
Geo-spatial utilities for loading, transforming, and plotting GeoDataFrames.
"""

import fiona
import geopandas as gpd
import matplotlib.pyplot as plt
import pyproj
from pyproj import CRS
from shapely.geometry import shape
from shapely.ops import transform


def load_gpkg(gpkg_path):
    """
    Load the first layer of a GeoPackage as a GeoDataFrame,
    checking that the CRS is defined.
    """
    # Load the first layer of the GeoPackage
    gdf = gpd.read_file(gpkg_path, layer=0)
    # Check if CRS is defined
    if gdf.crs is None:
        raise ValueError("The input GeoPackage does not have a defined CRS.")
    return gdf


def reproject_gdf(gdf, epsg=2193):
    """
    Reproject a GeoDataFrame to a specified EPSG code.
    Default is EPSG:2193 (NZTM 2000).
    """
    return gdf.to_crs(epsg=epsg)


def adjust_longitude(x, y):
    """Adjust longitudes to be within [0, 360]."""
    if x < 0:
        x += 360
    return x, y


def load_and_transform_shapefile(shapefile_path):
    """
    Load a shapefile, transform geometries to WGS84, and
    adjust longitudes. Returns a GeoDataFrame.
    """
    with fiona.open(shapefile_path, "r") as shapefile:
        source_crs = shapefile.crs
        target_crs = CRS("EPSG:4326")  # WGS84

        transformer = pyproj.Transformer.from_crs(
            source_crs, target_crs, always_xy=True
        )

        geometries = []
        properties_list = []
        for feature in shapefile:
            geometry = shape(feature["geometry"])
            transformed_geometry = transform(transformer.transform, geometry)
            adjusted_geometry = transform(adjust_longitude, transformed_geometry)
            geometries.append(adjusted_geometry)
            properties_list.append(feature["properties"])

        gdf = gpd.GeoDataFrame(
            properties_list, geometry=geometries, crs=target_crs.to_string()
        )

        return gdf


# pylint: disable=too-many-arguments, too-many-positional-arguments
def plot_maps(postcode_gdf, overlay_gdf, column, title1, title2, legend_title, figname):
    """
    Plot the postcode and overlay boundaries with specified parameters.
    """
    print(f"Plotting {title1} and {title2} ...")
    postcode_gdf_plot = postcode_gdf.to_crs(epsg=4326)
    overlay_gdf_plot = overlay_gdf.to_crs(epsg=4326)
    _, axes = plt.subplots(1, 2, figsize=(20, 10))
    postcode_gdf_plot.plot(ax=axes[0], color="none", edgecolor="blue", linewidth=0.5)
    axes[0].set_title(title1)
    axes[0].set_xlabel("Longitude")
    axes[0].set_ylabel("Latitude")
    # Synchronize the limits
    xmin, xmax = axes[0].get_xlim()
    ymin, ymax = axes[0].get_ylim()
    overlay_gdf_plot.plot(
        ax=axes[1],
        column=column,
        cmap="tab20b",
        alpha=0.8,
        legend=True,
        edgecolor="black",
        linewidth=0.5,
    )
    axes[1].set_title(title2)
    axes[1].set_xlabel("Longitude")
    axes[1].set_ylabel("Latitude")
    axes[1].set_xlim(xmin, xmax)
    axes[1].set_ylim(ymin, ymax)
    leg = axes[1].get_legend()
    leg.set_bbox_to_anchor((1.55, 1))
    leg.set_title(legend_title)
    plt.tight_layout()
    plt.savefig(figname)
    plt.close()
