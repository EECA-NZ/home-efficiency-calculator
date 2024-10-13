"""
Generate a lookup table from postcode to climate zone.

As a side effect, generate some data visualizations.
"""

from .helpers import (
    save_results,
    plot_histogram,
    process_postcodes
)
from .geo_utils import (
    load_gpkg,
    load_and_transform_shapefile,
    plot_maps,
    reproject_gdf
)

# Constants
OUTPUT_CSV = "./output/postcode_to_climate_zone.csv"
POSTCODE_SHAPEFILE = "../supplementary_data/PNF_V2024Q2_V01/PN_V2024Q2V01_POLYGONS.shp"
CLIMATE_GPKG = (
    "../climate_zone_boundaries/"
    "output/eeca_niwa_climate_boundaries/"
    "eeca_niwa_climate_boundaries.gpkg"
)


# Functions

def main():
    """
    Main function to generate the lookup table from postcode to climate zone.
    """
    print("Loading and transforming postcode shapefile...")
    my_postcode_gdf = load_and_transform_shapefile(POSTCODE_SHAPEFILE)

    print("Loading climate zones GeoPackage...")
    my_climate_zones_gdf = load_gpkg(CLIMATE_GPKG)

    print("Plotting postcode and climate zone boundaries...")
    plot_maps(
        my_postcode_gdf,
        my_climate_zones_gdf,
        column='climate',
        title1="New Zealand Postcode Boundaries",
        title2="New Zealand Climate Zone Boundaries",
        legend_title="Climate Zones",
        figname="output/postcode_climate_boundaries.png"
    )

    my_postcode_gdf = reproject_gdf(my_postcode_gdf)
    my_climate_zones_gdf = reproject_gdf(my_climate_zones_gdf)
    print("Process postcodes to determine climate zones")
    my_results = process_postcodes(
        postcode_gdf=my_postcode_gdf,
        overlay_gdf=my_climate_zones_gdf,
        overlay_column='climate',
        result_column_name='climate_zone',
        percentage_column_name='percentage_in_climate_zone'
    )
    plot_histogram(
        results=my_results,
        percentage_column_name='percentage_in_climate_zone',
        title="Histogram of Percentage of Each Postcode's Area in the Main Climate Zone",
        xlabel="Percentage of Area in Main Climate Zone",
        figname="output/percentage_in_main_climate_zone.png"
    )
    print("Prepare and save the lookup table")
    my_lookup_table = (
        my_results[["POSTCODE", "climate_zone"]]
        .rename(columns={"POSTCODE": "postcode"})
        .sort_values("postcode")
    )
    save_results(my_lookup_table, OUTPUT_CSV)
    return my_lookup_table, my_results


if __name__ == "__main__":
    main_lookup_table, main_results = main()
