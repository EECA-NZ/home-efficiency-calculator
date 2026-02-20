"""
Script for generating scatter plots of methane plans based on the tariff data.

The script reads the tariff data CSV file, filters the data based on various criteria,
and generates scatter plots of the filtered data for each EDB.

Note: we do not have spatial data for the EDB subregions where certain plans are
available. We approximate the methane plans available for each postcode by mapping
postcode to EDB and selecting an optimal plan from a subset of plans offered in the
EDB region (ignoring tariffs for rural / small capacity / low density network locations
and minimizing cost for a model household). See the docstring for the function called
filter_methane_plans in methane_plan_helpers.py for more details about the filtering
applied.

In principle we could be more specific by using boundaries of network regions, but this
would require more detailed spatial data than we currently have access to.
"""

import logging

from resources.plan_choice_helpers.data_loading import load_tariff_data
from resources.plan_choice_helpers.general_helpers import (
    clear_output_dir,
    generate_pdf_from_png,
    plot_subset,
)
from resources.plan_choice_helpers.methane_plan_helpers import filter_methane_plans
from resources.postcode_lookup_tables.geo_utils import load_and_transform_shapefile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOCAL_TARIFF_DATA_PATH = "../supplementary_data/tariff_data/tariffDataReport_251203.csv"
EDB_REGION_SHAPEFILE = "../supplementary_data/EDB_Boundaries/EDBBoundaries.shp"
OUTPUT_DIR = "bynetwork"


def main():
    """
    Main function to process the methane tariff data and plot the results.
    """
    my_df = load_tariff_data(LOCAL_TARIFF_DATA_PATH)

    my_df = filter_methane_plans(my_df)

    my_edb_boundaries_gdf = load_and_transform_shapefile(EDB_REGION_SHAPEFILE)
    my_edb_boundaries_gdf.loc[
        my_edb_boundaries_gdf["name"] == "CentraLines Ltd", "name"
    ] = "Centralines Ltd"

    clear_output_dir(OUTPUT_DIR)

    for my_edb in sorted(my_edb_boundaries_gdf["name"].unique()):
        if my_edb == "Stewart Island Electrical Supply Authority":
            continue
        logger.info("Processing EDB: %s", my_edb)
        plot_subset(
            my_df, my_edb, hue_column="Network location names", output_dir=OUTPUT_DIR
        )

    generate_pdf_from_png(OUTPUT_DIR, f"{OUTPUT_DIR}/{OUTPUT_DIR}.pdf")


if __name__ == "__main__":
    main()
