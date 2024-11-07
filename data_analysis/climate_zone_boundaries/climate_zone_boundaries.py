"""
This script processes territorial authority shapefile data
to recreate NIWA's climate zone boundaries which are broadly
defined by Territorial Authority (TA) boundaries, but with
some adjustments.
"""

import os
import shutil

import fiona
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import pyproj
from process_river import load_and_process_river
from pyproj import CRS
from shapely.geometry import LineString, MultiPolygon, Polygon, shape
from shapely.ops import split, transform
from ta_to_climate_zone import ta_to_climate_zone

# pylint: disable=possibly-used-before-assignment, too-many-locals

#### Constants

RANGITIKEI_SPLIT_LINE = LineString(
    [(lon, -39.833333333) for lon in (175.41445, 175.80)]
)
OTEKAIEKE_END_POINTS = [
    (170.333, -44.904),
    (170.5846, -44.815),
]  # Force the river to cross the TA boundary
OTEKAIEKE = load_and_process_river(
    "Otekaieke River", OTEKAIEKE_END_POINTS
)  # Get the river geometry, removing braiding and
# extending to just past the TA boundary
DIRECTORY_PATH = (
    "../supplementary_data/statsnz-territorial-authority-2023-clipped-generalised-SHP"
)
INPUT_SHAPEFILE_NAME = "territorial-authority-2023-clipped-generalised.shp"
INPUT_SHAPEFILE_PATH = f"{DIRECTORY_PATH}/{INPUT_SHAPEFILE_NAME}"
OUTPUT_PATH = "./output"
OUTPUT_SHAPEFILE_PATH = (
    f"{OUTPUT_PATH}/eeca_niwa_climate_boundaries/eeca_niwa_climate_boundaries.shp"
)


#### Functions


def transform_geometry(geometry, transformer):
    """Transform geometry using a pyproj Transformer."""
    return transform(transformer.transform, geometry)


def adjust_longitude(x, y):
    """Adjust longitudes to be within [0, 360]."""
    if x < 0:
        x += 360
    return x, y


def load_and_transform_shapefile(shapefile_path):
    """Load the shapefile, transform geometries to WGS84, and adjust longitudes."""
    with fiona.open(shapefile_path, "r") as shapefile:
        # Get CRS from source shapefile
        source_crs = shapefile.crs
        target_crs = CRS("EPSG:4326")  # Define target CRS as WGS84
        # Prepare transformer to convert source CRS to WGS84
        transformer = pyproj.Transformer.from_crs(
            source_crs, target_crs, always_xy=True
        )
        geometries = []
        for feature in shapefile:
            geometry = shape(feature["geometry"])
            transformed_geometry = transform(transformer.transform, geometry)
            adjusted_geometry = transform(adjust_longitude, transformed_geometry)
            ta_name = feature["properties"].get("TA2023_V_1", "Unknown")
            climate = ta_to_climate_zone.get(ta_name, "Unknown")
            geometries.append((adjusted_geometry, climate, ta_name))
        # Create GeoDataFrame
        gdf = gpd.GeoDataFrame(
            geometries,
            columns=["geometry", "climate", "ta_name"],
            crs=target_crs.to_string(),
        )
        return gdf


def split_geometry_by_line(geom, line, crs):
    """Split the given geometry by the given line and return all parts."""
    split_result = split(geom, line)
    polygons = [
        geom for geom in split_result.geoms if isinstance(geom, (Polygon, MultiPolygon))
    ]
    split_gdf = gpd.GeoDataFrame(geometry=polygons, crs=crs)
    split_gdf = split_gdf.to_crs("EPSG:2193")  # Convert to NZTM for area calculation
    split_gdf["area"] = split_gdf["geometry"].area
    split_gdf = split_gdf.to_crs(crs)  # Convert back for plotting
    return split_gdf


def plot_geometries(gdf, additional_features, title):
    """Plot the given list of Shapely geometries with climate zones, including river."""
    gdf = gdf[["geometry", "climate", "ta_name"]]
    geometries = list(gdf.itertuples(index=False, name=None))
    _, ax = plt.subplots(figsize=(10, 10))
    climate_colors = {}
    unique_zones = sorted(set(zone for _, zone, _ in geometries))
    cmap = plt.get_cmap("tab20", len(unique_zones))
    for i, zone in enumerate(unique_zones):
        climate_colors[zone] = cmap(i)
    legend_labels = {}
    for geometry, climate, ta_name in geometries:
        fill_color = climate_colors[climate]
        if geometry.geom_type == "Polygon":
            xs, ys = geometry.exterior.xy
            patch = ax.fill(
                xs, ys, alpha=0.5, fc=fill_color, edgecolor="black", label=ta_name
            )
        elif geometry.geom_type == "MultiPolygon":
            for poly in geometry.geoms:
                xs, ys = poly.exterior.xy
                patch = ax.fill(xs, ys, alpha=0.5, fc=fill_color, edgecolor="black")
        if climate not in legend_labels:
            legend_labels[climate] = patch[0]
    for feature_name, feature_geometry in additional_features.items():
        if feature_geometry.geom_type == "LineString":
            xs, ys = feature_geometry.xy
            ax.plot(xs, ys, color="blue", label=feature_name)
        elif feature_geometry.geom_type == "MultiLineString":
            for line in feature_geometry.geoms:
                xs, ys = line.xy
                ax.plot(xs, ys, color="blue", label=feature_name)
    ax.legend(
        legend_labels.values(),
        list(legend_labels.keys()) + list(additional_features.keys()),
    )
    ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    plt.grid(True)


def ensure_empty_directory(directory):
    """Ensure that the specified directory is empty."""
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory, exist_ok=True)


def main():
    """
    Main function to process territorial authority shapefile data
    """
    ensure_empty_directory(OUTPUT_PATH)

    # Load the TA shapefile and map the TA names to climate zones
    ta_gdf = load_and_transform_shapefile(INPUT_SHAPEFILE_PATH)
    additional_features = {
        "Otekaieke River": OTEKAIEKE,
        "Rangitikei Split Line": RANGITIKEI_SPLIT_LINE,
    }
    plot_geometries(
        ta_gdf,
        additional_features,
        "Territorial Authority Boundaries with Approximate Climate Zones",
    )
    plt.savefig(f"{OUTPUT_PATH}/1-territorial-authority-boundaries.png")

    # Split Waitaki District based on the Otekaieke River.
    ta_name = "Waitaki District"
    waitaki_geom = ta_gdf[ta_gdf["ta_name"] == ta_name]["geometry"].iloc[0]
    split_waitaki = split_geometry_by_line(waitaki_geom, OTEKAIEKE, ta_gdf.crs)
    # Use lat to determine climate zone of each piece.
    split_waitaki["centroid_lat"] = split_waitaki["geometry"].apply(
        lambda g: g.centroid.y
    )
    threshold_lat = OTEKAIEKE.centroid.y
    split_waitaki["climate"] = [
        "Dunedin" if lat < threshold_lat else "Central Otago"
        for lat in split_waitaki["centroid_lat"]
    ]
    split_waitaki["ta_name"] = [
        (
            "Waitaki District (Coastal)"
            if lat < threshold_lat
            else "Waitaki District (Inland)"
        )
        for lat in split_waitaki["centroid_lat"]
    ]
    new_gdf = gpd.GeoDataFrame(
        [
            {
                "geometry": split_waitaki.iloc[i]["geometry"],
                "climate": split_waitaki.iloc[i]["climate"],
                "ta_name": split_waitaki.iloc[i]["ta_name"],
            }
            for i in range(len(split_waitaki))
        ],
        crs=ta_gdf.crs,
    )
    # Replace the original Waitaki District geometry with the split geometries
    ta_gdf = ta_gdf[ta_gdf["ta_name"] != ta_name]
    ta_gdf = pd.concat([ta_gdf, new_gdf], ignore_index=True)

    # Split the Rangitikei District based on the Rangitikei Split Line (latitude).
    ta_name = "Rangitikei District"
    rangitikei_geom = ta_gdf[ta_gdf["ta_name"] == ta_name]["geometry"].iloc[0]
    split_rangitikei = split_geometry_by_line(
        rangitikei_geom, RANGITIKEI_SPLIT_LINE, ta_gdf.crs
    )
    # Use lat to determine climate zone of each piece.
    split_rangitikei["centroid_lat"] = split_rangitikei["geometry"].apply(
        lambda g: g.centroid.y
    )
    threshold_lat = RANGITIKEI_SPLIT_LINE.centroid.y
    split_rangitikei["climate"] = [
        "Manawatu" if lat < threshold_lat else "Taupo"
        for lat in split_rangitikei["centroid_lat"]
    ]
    split_rangitikei["ta_name"] = [
        (
            "Rangitikei District (Coastal)"
            if lat < threshold_lat
            else "Rangitikei District (Inland)"
        )
        for lat in split_rangitikei["centroid_lat"]
    ]
    new_gdf = gpd.GeoDataFrame(
        [
            {
                "geometry": split_rangitikei.iloc[i]["geometry"],
                "climate": split_rangitikei.iloc[i]["climate"],
                "ta_name": split_rangitikei.iloc[i]["ta_name"],
            }
            for i in range(len(split_rangitikei))
        ],
        crs=ta_gdf.crs,
    )
    # Replace the original Rangitikei District geometry with the split geometries
    ta_gdf = ta_gdf[ta_gdf["ta_name"] != ta_name]
    ta_gdf = pd.concat([ta_gdf, new_gdf], ignore_index=True)
    plot_geometries(
        ta_gdf,
        additional_features,
        "Territorial Authority Boundaries with Corrected Climate Zones",
    )
    plt.savefig(f"{OUTPUT_PATH}/2-territorial-authority-boundaries-climate-zones.png")

    # Merge contiguous territorial authorities with the same climate zone
    merged_gdf = ta_gdf.dissolve(by="climate", aggfunc="first")
    merged_gdf.reset_index(inplace=True)
    additional_features = {}
    plot_geometries(
        merged_gdf, additional_features, "EECA-reconstructed NIWA Climate Zones"
    )
    plt.savefig(f"{OUTPUT_PATH}/3-eeca-niwa-climate-zones.png")

    # Save the merged geometries to the output shapefile
    ensure_empty_directory(os.path.dirname(OUTPUT_SHAPEFILE_PATH))
    merged_gdf.to_file(OUTPUT_SHAPEFILE_PATH)
    print(f"Saved merged climate zone boundaries to {OUTPUT_SHAPEFILE_PATH}")

    # Save as a GeoJSON file for visualization in GitHub
    merged_gdf.to_file(
        OUTPUT_SHAPEFILE_PATH.replace(".shp", ".geojson"), driver="GeoJSON"
    )
    print(
        f"Saved merged climate zone boundaries to "
        f"{OUTPUT_SHAPEFILE_PATH.replace('.shp', '.geojson')}"
    )

    # Save as a geopackage for use in the DNA library
    merged_gdf.to_file(OUTPUT_SHAPEFILE_PATH.replace(".shp", ".gpkg"), driver="GPKG")
    print(
        "Saved merged climate zone boundaries to ",
        "{OUTPUT_SHAPEFILE_PATH.replace('.shp', '.gpkg')}",
    )
    return merged_gdf


if __name__ == "__main__":
    my_merged_gdf = main()
