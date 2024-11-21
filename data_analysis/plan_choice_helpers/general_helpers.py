"""
General helper functions used across both electricity plan
and natural gas plan analysis.
"""

import logging
import os

import img2pdf
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_output_dir(output_dir):
    """
    Attempts to delete all files in the output directory.
    If a file cannot be deleted (e.g., it is open in another process),
    logs an error message indicating the file should be closed.

    Parameters:
    -----------
    output_dir : str
        The directory containing the files to delete.
    """
    for file in os.listdir(output_dir):
        file_path = os.path.join(output_dir, file)
        try:
            os.remove(file_path)
        except PermissionError:
            logger.error(
                "Could not delete %s. Please close the file and try again.", file_path
            )
        except (
            OSError
        ) as os_err:  # Catching specific exception instead of broad Exception
            logger.error("An error occurred while deleting %s: %s", file_path, os_err)


def generate_pdf_from_png(output_dir, output_pdf):
    """
    Generate a PDF from a directory of PNG files.

    Parameters
    ----------
    output_dir : str
        The directory containing the PNG files to convert to PDF.

    output_pdf : str
        The output PDF file to generate.

    Returns
    -------
    None
    """
    png_files = [
        os.path.join(output_dir, file)
        for file in os.listdir(output_dir)
        if file.endswith(".png")
    ]
    img2pdf_logger = logging.getLogger("img2pdf")
    img2pdf_logger.setLevel(logging.ERROR)
    with open(output_pdf, "wb") as f:
        f.write(img2pdf.convert(png_files))
    img2pdf_logger.setLevel(logging.WARNING)
    logger.info("PDF generated: %s", output_pdf)


def save_results_to_csv(results, output_file):
    """
    Save the optimal electricity plans to a CSV file.

    Args:
    results: List of tuples containing EDB, profile, and the optimal plan
    output_file: str, the path to the output CSV file
    """
    rows = []
    for edb, _, best_plan, _ in results:
        rows.append({"EDB": edb, "PlanId": best_plan.name})
    final_df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    final_df.to_csv(output_file, index=False)
    logger.info("Results saved to %s", output_file)


def plot_subset(df, edb=None, hue_column=None, output_dir="scatterplots"):
    """
    Plot an EDB-specific subset of the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing the data to plot.

    edb : str or None, optional
        The EDB name to filter the data by.
        If None, all EDBs are included. Default is None.

    hue_column : str or None, optional
        The column to use for coloring the data points.
        If None, no coloring is applied. Default is None.

    output_dir : str, optional
        The output directory to save the plot image to.
        Default is "scatterplots".

    Returns
    -------
    None
    """
    subset = df.copy()
    if edb is not None:
        subset = subset[subset["EDB"] == edb]
    subset["1/10 x Daily charge"] = subset["Daily charge"] / 10
    scatterplot_vars = [
        "All inclusive",
        "Day",
        "Uncontrolled",
        "Controlled",
        "Night",
        "1/10 x Daily charge",
    ]
    plot_height = 1
    plot_aspect = 2
    if (
        hue_column is not None
        and hue_column in subset.columns
        and subset[hue_column].notnull().any()
    ):
        g = sns.pairplot(
            subset,
            vars=scatterplot_vars,
            hue=hue_column,
            palette="Set1",
            plot_kws={"alpha": 0.6},
            height=plot_height,
            aspect=plot_aspect,
        )
    else:
        g = sns.pairplot(
            subset,
            vars=scatterplot_vars,
            plot_kws={"alpha": 0.6},
            height=plot_height,
            aspect=plot_aspect,
        )
    for ax in g.axes.flatten():
        if ax is not None:
            ax.set_xlim(0, 0.5)
            ax.set_ylim(0, 0.5)
    g.fig.suptitle(edb if edb else "All EDBs", fontsize=16, y=0.98)
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{edb.replace(' ', '_') if edb else 'all'}.png"
    plt.savefig(filename)
    plt.close()
