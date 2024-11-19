"""
General helper functions used across both electricity plan
and natural gas plan analysis.
"""

import logging
import os

import img2pdf
import pandas as pd

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
