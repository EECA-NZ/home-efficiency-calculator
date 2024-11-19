"""
Generate a lookup table from postcode to electricity and gas plans.

As a side effect, generate some data visualizations.
"""

import pandas as pd

from app.constants import EXCLUDE_POSTCODES
from data_analysis.postcode_lookup_tables.geo_utils import (
    load_and_transform_shapefile,
    plot_maps,
    reproject_gdf,
)
from data_analysis.postcode_lookup_tables.helpers import (
    plot_histogram,
    process_postcodes,
    save_results,
)

# Constants
OUTPUT_CSV = "./output/postcode_to_edb_region.csv"
EDB_REGION_SHAPEFILE = "../supplementary_data/EDB_Boundaries/EDBBoundaries.shp"
POSTCODE_SHAPEFILE = "../supplementary_data/PNF_V2024Q2_V01/PN_V2024Q2V01_POLYGONS.shp"

# Functions


def main():
    """
    Main function to generate the lookup table from postcode to edb region.
    """
    print("Loading and transforming postcode shapefile...")
    my_postcode_gdf = load_and_transform_shapefile(POSTCODE_SHAPEFILE)

    print("Loading and transforming EDB boundaries shapefile...")
    my_edb_boundaries_gdf = load_and_transform_shapefile(EDB_REGION_SHAPEFILE)

    print("Loading tariff data...")
    my_tariff_data = pd.read_csv(
        "../supplementary_data/tariff_data/tariffDataReport_240903.csv"
    )

    print("Plotting postcode and EDB boundaries...")
    plot_maps(
        my_postcode_gdf,
        my_edb_boundaries_gdf,
        column="name",
        title1="New Zealand Postcode Boundaries",
        title2="Electricity Distribution Board Boundaries",
        legend_title="EDB Regions",
        figname="output/postcode_edb_boundaries.png",
    )

    my_postcode_gdf = reproject_gdf(my_postcode_gdf)
    my_edb_boundaries_gdf = reproject_gdf(my_edb_boundaries_gdf)
    print("Process postcodes to determine edb regions")
    results = process_postcodes(
        postcode_gdf=my_postcode_gdf,
        overlay_gdf=my_edb_boundaries_gdf,
        overlay_column="name",
        result_column_name="edb_region",
        percentage_column_name="percentage_in_edb_region",
    )
    plot_histogram(
        results=results,
        percentage_column_name="percentage_in_edb_region",
        title="Histogram of Percentage of Each Postcode's Area in the Main EDB Region",
        xlabel="Percentage of Area in Main EDB Region",
        figname="output/percentage_in_main_edb_region.png",
    )
    print("Prepare the lookup table")
    lookup_table = (
        results[["POSTCODE", "edb_region"]]
        .rename(columns={"POSTCODE": "postcode"})
        .sort_values("postcode")
    )
    print("Filter out the following postcodes: ", EXCLUDE_POSTCODES)
    exclude_postcodes = [
        postcode for sublist in EXCLUDE_POSTCODES.values() for postcode in sublist
    ]
    lookup_table = lookup_table[~lookup_table["postcode"].isin(exclude_postcodes)]
    print("Save the lookup table")
    save_results(lookup_table, OUTPUT_CSV)
    return lookup_table, results, my_tariff_data


if __name__ == "__main__":
    main_lookup_table, main_results, main_my_tariff_data = main()
