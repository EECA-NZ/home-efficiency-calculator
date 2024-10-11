"""
Generate a lookup table from postcode to climate zone.

As a side effect, generate some data visualizations.
"""

import fiona
import pyproj
import seaborn as sns
from pyproj import CRS
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.ops import transform
from shapely.geometry import shape

# Constants
OUTPUT_CSV = "../../lookup/postcode_to_climate_zone.csv"
SHAPEFILE = "../supplementary_data/PNF_V2024Q2_V01/PN_V2024Q2V01_POLYGONS.shp"
CLIMATE_GPKG = (
    "../climate_zone_boundaries/"
    "output/eeca_niwa_climate_boundaries/"
    "eeca_niwa_climate_boundaries.gpkg"
)


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


def load_gpkg(gpkg_path):
    """Load the first layer of a GeoPackage as a GeoDataFrame."""
    return gpd.read_file(gpkg_path, layer=0)


def plot_maps(postcode_gdf, climate_zones_gdf, figname):
    """
    Plot the postcode and climate zone boundaries as two subplots.
    """
    print("Plotting postcode and climate zone boundaries...")
    # Reproject to WGS84 for plotting
    postcode_gdf_plot = postcode_gdf.to_crs(epsg=4326)
    climate_zones_gdf_plot = climate_zones_gdf.to_crs(epsg=4326)

    _, axes = plt.subplots(1, 2, figsize=(20, 10))

    # Plot postcode boundaries
    postcode_gdf_plot.plot(ax=axes[0], color="none", edgecolor="blue", linewidth=0.5)
    axes[0].set_title("New Zealand Postcode Boundaries")
    axes[0].set_xlabel("Longitude")
    axes[0].set_ylabel("Latitude")

    # Plot climate zones with distinct colors and a legend
    climate_zones_gdf_plot.plot(
        ax=axes[1],
        column="climate",
        cmap="tab20",
        alpha=0.5,
        legend=True,
        edgecolor="black",
        linewidth=0.5,
    )
    axes[1].set_title("New Zealand Climate Zone Boundaries")
    axes[1].set_xlabel("Longitude")
    axes[1].set_ylabel("Latitude")

    # Adjust legend
    leg = axes[1].get_legend()
    leg.set_bbox_to_anchor((1.15, 1))  # Position the legend outside the plot
    leg.set_title("Climate Zones")

    # Adjust layout and save the plot
    plt.tight_layout()
    plt.savefig(figname)
    plt.close()


def process_postcodes(postcode_gdf, climate_zones_gdf):
    """
    Process the postcodes to determine climate zones.
    Returns a DataFrame with results.
    """
    # Calculate the area of each postcode polygon
    print("Calculating postcode areas...")
    postcode_gdf["postcode_area"] = postcode_gdf.geometry.area

    # Perform spatial overlay to find intersections between postcodes and climate zones
    print("Performing spatial overlay to find intersections...")
    overlay = gpd.overlay(postcode_gdf, climate_zones_gdf, how="intersection")

    # Calculate the area of the intersected polygons
    print("Calculating intersection areas...")
    overlay["intersection_area"] = overlay.geometry.area

    # Group by POSTCODE and climate to sum the intersection areas
    print("Grouping and summing intersection areas...")
    area_by_postcode_climate = (
        overlay.groupby(["POSTCODE", "climate"])
        .agg({"intersection_area": "sum"})
        .reset_index()
    )

    # Merge the total postcode area
    area_by_postcode = postcode_gdf[["POSTCODE", "postcode_area"]]
    area_by_postcode_climate = area_by_postcode_climate.merge(
        area_by_postcode, on="POSTCODE"
    )

    # Calculate the percentage of the postcode area within each climate zone
    area_by_postcode_climate["percentage"] = (
        area_by_postcode_climate["intersection_area"]
        / area_by_postcode_climate["postcode_area"]
    ) * 100

    # Determine the main climate zone for each postcode
    print("Determining main climate zone for each postcode...")
    idx = area_by_postcode_climate.groupby("POSTCODE")["percentage"].idxmax()
    main_climate = area_by_postcode_climate.loc[
        idx, ["POSTCODE", "climate", "percentage"]
    ].reset_index(drop=True)

    # Merge the main climate zone back into the postcode GeoDataFrame
    postcode_gdf = postcode_gdf.merge(main_climate, on="POSTCODE", how="left")

    # Handle postcodes without a climate zone assignment
    missing_climate_zones = postcode_gdf["climate"].isnull().sum()
    if missing_climate_zones > 0:
        print(
            f"There are {missing_climate_zones} postcodes without climate zone assignments."
        )
        # Assign 'Unknown' to missing climate zones
        postcode_gdf["climate"] = postcode_gdf["climate"].fillna("Unknown")
        postcode_gdf["percentage"] = postcode_gdf["percentage"].fillna(0)

    # Analyze the number of postcodes entirely within a single climate zone
    num_entirely_within = (postcode_gdf["percentage"] >= 99).sum()
    total_postcodes = postcode_gdf["POSTCODE"].nunique()
    print(
        "Number of postcodes entirely within a single climate zone: ",
        int(num_entirely_within),
        " out of ",
        total_postcodes,
    )

    # Prepare the results DataFrame
    results = postcode_gdf[
        [
            "MAIL_TOWN",
            "POSTCODE",
            "ROUND_NAME",
            "climate",
            "percentage",
        ]
    ].rename(
        columns={
            "climate": "climate_zone",
            "percentage": "percentage_in_climate_zone",
        }
    )

    return results


def plot_histogram(results, figname):
    """
    Plot a histogram of the percentage of each postcode's area in the main climate zone.
    """
    print("Plotting histogram...")
    plt.figure(figsize=(12, 6))
    sns.histplot(
        data=results,
        x="percentage_in_climate_zone",
        bins=50,
        kde=False,
        edgecolor="black",
    )
    plt.title(
        "Histogram of Percentage of Each Postcode's Area in the Main Climate Zone"
    )
    plt.xlabel("Percentage of Area in Main Climate Zone")
    plt.ylabel("Number of Postcodes")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.savefig(figname)
    plt.close()


def save_results(results, output_csv):
    """
    Save the results to a CSV file.
    """
    print(f"Saving results to {output_csv}...")
    results.to_csv(output_csv, index=False)
    print("Process completed successfully.")


def main():
    """
    Main function to generate the lookup table from postcode to climate zone.
    """
    # Load and transform the postcode shapefile
    print("Loading and transforming postcode shapefile...")
    postcode_gdf = load_and_transform_shapefile(SHAPEFILE)

    # Load climate zones GeoPackage
    print("Loading climate zones GeoPackage...")
    climate_zones_gdf = load_gpkg(CLIMATE_GPKG)

    # Plot the postcode and climate zone boundaries
    plot_maps(postcode_gdf, climate_zones_gdf, "postcode_climate_boundaries.png")

    # Reproject to EPSG:2193 (New Zealand Transverse Mercator 2000)
    print("Reprojecting GeoDataFrames to EPSG:2193...")
    postcode_gdf = postcode_gdf.to_crs(epsg=2193)
    climate_zones_gdf = climate_zones_gdf.to_crs(epsg=2193)

    # Process postcodes to determine climate zones
    results = process_postcodes(postcode_gdf, climate_zones_gdf)

    # Plot the histogram
    plot_histogram(results, "percentage_in_main_climate_zone.png")

    # Prepare and save the lookup table
    lookup_table = (
        results[["POSTCODE", "climate_zone"]]
        .rename(columns={"POSTCODE": "postcode"})
        .sort_values("postcode")
    )
    save_results(lookup_table, OUTPUT_CSV)


if __name__ == "__main__":
    main()
