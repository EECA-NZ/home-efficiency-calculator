"""
This script processes electricity meter usage data to calculate average usage by
hour and breaks down usage between day and night periods. It also visualizes the
usage with Day/Night distinction and saves the plot as a PNG file.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd


def process_usage_data(file_path):
    """
    Processes the electricity meter usage data and returns the filtered data and
    hourly average usage.

    Args:
        file_path (str): Path to the CSV file containing the meter usage data.

    Returns:
        filtered_data (DataFrame): Filtered DataFrame with processed time data.
        hourly_avg_usage (Series): Average kWh usage per hour.
        average_day_night_usage (Series): Average daily usage, Day and Night.
    """
    # Load and process the data
    data = pd.read_csv(file_path)
    data["Date"] = pd.to_datetime(data["Date"], format="%d/%m/%Y")

    # Melt the dataframe so that each half-hour time period becomes a row
    melted_data = pd.melt(data, id_vars=["Date"], var_name="Time", value_name="kWh")

    # Filter rows with valid time values
    valid_time_mask = melted_data["Time"].str.contains(r"^\d{2}:\d{2}", regex=True)
    filtered_data = melted_data.loc[valid_time_mask].copy()  # Make a deep copy

    # Extract hour and determine Day/Night period
    filtered_data["Hour"] = (
        filtered_data["Time"].str.split(" - ").str[0].str[:2].astype(int)
    )
    filtered_data["Period"] = filtered_data["Hour"].apply(
        lambda x: "Night" if x >= 23 or x < 7 else "Day"
    )

    # Group by hour to calculate average kWh usage
    hourly_avg_usage = filtered_data.groupby(["Hour"])["kWh"].mean()

    # Calculate average daily Day/Night usage
    average_day_night_usage = (
        filtered_data.groupby("Period")["kWh"].sum() / filtered_data["Date"].nunique()
    )

    return filtered_data, hourly_avg_usage, average_day_night_usage


def plot_usage(hourly_avg_usage, output_dir):
    """
    Plots the average kWh usage by time of day and highlights Day/Night periods.

    Args:
        hourly_avg_usage (Series): The average kWh usage per hour.
        output_dir (str): The directory where the plot will be saved.
    """
    hours = hourly_avg_usage.index.tolist() + [24]
    hourly_usage_wrapped = hourly_avg_usage.tolist() + [hourly_avg_usage.iloc[0]]

    # Create the 'output' directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Plot the average usage by time of day with Day/Night distinction
    plt.figure(figsize=(10, 6))
    plt.plot(hours, hourly_usage_wrapped, marker="o", label="Average kWh Usage")

    # Add Day/Night shading
    plt.axvspan(0, 7, color="blue", alpha=0.1, label="Night Period")
    plt.axvspan(23, 24, color="blue", alpha=0.1)  # Night period from 23 to 24
    plt.axvspan(7, 23, color="yellow", alpha=0.1, label="Day Period")

    # Set y-limit to start from 0
    _, upper_ylim = plt.ylim()
    plt.ylim(0, upper_ylim)

    # Plot labels and grid
    plt.title("Average Usage by Time of Day")
    plt.xlabel("Hour of Day")
    plt.ylabel("Average kWh Usage")
    plt.grid(True)
    plt.xticks(range(0, 25))  # Include 0 twice for wrapping around
    plt.legend()

    # Save the plot as a PNG file
    output_path = os.path.join(output_dir, "average_usage_day_night.png")
    plt.savefig(output_path)

    # Show the plot
    plt.show()


def main():
    """
    Main function to process the electricity meter usage data and plot the results.
    """
    # Define file paths
    file_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "supplementary_data",
        "meter_usage_data",
        "0000121773TREA0_meter_usage_data_2023-10-17_to_2024-10-14.csv",
    )
    output_dir = os.path.join(os.path.dirname(__file__), "output")

    # Process the data
    filtered_data, hourly_avg_usage, average_day_night_usage = process_usage_data(
        file_path
    )

    # Plot the results
    plot_usage(hourly_avg_usage, output_dir)

    # Print the breakdown of Day and Night usage
    print("Day and Night kWh Usage (Average Daily):")
    print(average_day_night_usage)

    # Optionally, export the results to a CSV for further use
    average_day_night_usage.to_csv(os.path.join(output_dir, "day_night_usage.csv"))

    return filtered_data, hourly_avg_usage, average_day_night_usage


# Call the main function
if __name__ == "__main__":
    my_filtered_data, my_hourly_avg_usage, my_average_day_night_usage = main()
