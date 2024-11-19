"""
General helper functions for processing postcodes and spatial data.
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns


def save_results(results, output_csv):
    """
    Save the results to a CSV file.
    """
    print(f"Saving results to {output_csv}...")
    results.to_csv(output_csv, index=False)
    print("Process completed successfully.")


def process_postcodes(
    postcode_gdf,
    overlay_gdf,
    overlay_column,
    result_column_name,
    percentage_column_name,
):
    """
    Process the postcodes to determine overlapping zones
    (e.g., climate zones, EDB regions).

    Returns a DataFrame with results.

    Parameters:
    - postcode_gdf: GeoDataFrame containing postcode geometries.
    - overlay_gdf: GeoDataFrame containing overlay geometries (e.g., climate zones).
    - overlay_column: Column name in overlay_gdf to use for grouping (e.g., 'climate').
    - result_column_name: Name to assign to the overlay column in the results
        (e.g., 'climate_zone').
    - percentage_column_name: Name to assign to the percentage column in the results.

    Returns:
    - results: DataFrame with the main zone assigned to each postcode.
    """
    # Calculate the area of each postcode polygon
    print("Calculating postcode areas...")
    postcode_gdf["postcode_area"] = postcode_gdf.geometry.area
    # Perform spatial overlay to find intersections between postcodes and overlay zones
    print("Performing spatial overlay to find intersections...")
    overlay = gpd.overlay(postcode_gdf, overlay_gdf, how="intersection")
    # Calculate the area of the intersected polygons
    print("Calculating intersection areas...")
    overlay["intersection_area"] = overlay.geometry.area
    # Group by POSTCODE and overlay_column to sum the intersection areas
    print("Grouping and summing intersection areas...")
    area_by_postcode_overlay = (
        overlay.groupby(["POSTCODE", overlay_column])
        .agg({"intersection_area": "sum"})
        .reset_index()
    )
    # Merge the total postcode area
    area_by_postcode = postcode_gdf[["POSTCODE", "postcode_area"]]
    area_by_postcode_overlay = area_by_postcode_overlay.merge(
        area_by_postcode, on="POSTCODE"
    )
    # Calculate the percentage of the postcode area within each overlay zone
    area_by_postcode_overlay["percentage"] = (
        area_by_postcode_overlay["intersection_area"]
        / area_by_postcode_overlay["postcode_area"]
    ) * 100
    # Determine the main overlay zone for each postcode
    print("Determining main zone for each postcode...")
    idx = area_by_postcode_overlay.groupby("POSTCODE")["percentage"].idxmax()
    main_overlay = area_by_postcode_overlay.loc[
        idx, ["POSTCODE", overlay_column, "percentage"]
    ].reset_index(drop=True)
    # Merge the main overlay zone back into the postcode GeoDataFrame
    postcode_gdf = postcode_gdf.merge(main_overlay, on="POSTCODE", how="left")
    # Handle postcodes without an overlay zone assignment
    missing_zones = postcode_gdf[overlay_column].isnull().sum()
    if missing_zones > 0:
        print(
            f"There are {missing_zones} postcodes without {overlay_column} assignments."
        )
        # Assign 'Unknown' to missing overlay zones
        postcode_gdf[overlay_column] = postcode_gdf[overlay_column].fillna("Unknown")
        postcode_gdf["percentage"] = postcode_gdf["percentage"].fillna(0)

    # Analyze the number of postcodes entirely within a single overlay zone
    num_entirely_within = (postcode_gdf["percentage"] >= 99).sum()
    total_postcodes = postcode_gdf["POSTCODE"].nunique()
    print(
        "Number of postcodes entirely within a single zone: ",
        f"{int(num_entirely_within)} out of {total_postcodes}",
    )
    # Prepare the results DataFrame
    results = postcode_gdf[
        [
            "MAIL_TOWN",
            "POSTCODE",
            "ROUND_NAME",
            overlay_column,
            "percentage",
        ]
    ].rename(
        columns={
            overlay_column: result_column_name,
            "percentage": percentage_column_name,
        }
    )
    return results


def plot_histogram(results, percentage_column_name, title, xlabel, figname):
    """
    Plot a histogram of the percentage of each postcode's area in the main zone.

    Parameters:
    - results: DataFrame containing the results to plot.
    - percentage_column_name: Name of the percentage column in the results.
    - title: Title of the histogram plot.
    - xlabel: Label for the x-axis.
    - figname: Filename to save the plot.

    Returns:
    - None
    """
    print("Plotting histogram...")
    plt.figure(figsize=(12, 6))
    sns.histplot(
        data=results,
        x=percentage_column_name,
        bins=50,
        kde=False,
        edgecolor="black",
    )
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Number of Postcodes")
    plt.grid(axis="y")
    plt.tight_layout()
    plt.savefig(figname)
    plt.close()
