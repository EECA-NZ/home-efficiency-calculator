"""
This script processes river data from a GeoPackage file to extract the longest simple path

Used as a helper script for the climate zone boundaries project.
"""

import itertools
import geopandas as gpd
import networkx as nx
from shapely.geometry import MultiLineString, LineString, Point
from shapely.ops import nearest_points

# Setting a constant for the path to the GeoPackage.
# File downloaded from https://data.linz.govt.nz/layer/103632-nz-river-name-lines-pilot/
GPKG_PATH = "./lds-nz-river-name-lines-pilot-GPKG/nz-river-name-lines-pilot.gpkg"

# pylint: disable=too-many-locals


def simplified_river_path(geometries, extend_to_end_points=None):
    """
    Extracts the longest simple path from a collection of MultiLineString geometries,
    representing parts of a river.
    """
    mygraph = nx.Graph()
    for multi_line in geometries:
        if isinstance(multi_line, MultiLineString):
            for line in multi_line.geoms:
                start, end = tuple(line.coords[0]), tuple(line.coords[-1])
                mygraph.add_edge(start, end, weight=line.length)
        elif isinstance(multi_line, LineString):
            start, end = tuple(multi_line.coords[0]), tuple(multi_line.coords[-1])
            mygraph.add_edge(start, end, weight=multi_line.length)
    endpoints = [node for node, degree in mygraph.degree() if degree == 1]
    if not endpoints:
        return None
    max_length = 0
    best_path = None
    for start, end in itertools.combinations(endpoints, 2):
        try:
            length, path = nx.single_source_dijkstra(
                mygraph, start, end, weight="weight"
            )
            if length > max_length:
                max_length = length
                best_path = path
        except nx.NetworkXNoPath:
            continue
    if best_path:
        extended_path = best_path
        if extend_to_end_points:
            # Convert tuples to Points if not already and extend both endpoints
            start_point, end_point = map(Point, extend_to_end_points)
            path_start, path_end = Point(extended_path[0]), Point(extended_path[-1])
            # Nearest real start and end points
            nearest_start = nearest_points(path_start, start_point)[1]
            nearest_end = nearest_points(path_end, end_point)[1]
            # Extend path at the start and the end
            extended_path = (
                [tuple(nearest_start.coords[0])]
                + extended_path
                + [tuple(nearest_end.coords[0])]
            )
        return LineString([Point(node) for node in extended_path])
    return None


def load_and_process_river(name, extend_to_end_points=None):
    """
    Load river data from a specified GeoPackage and process to find the simplified river path.
    """
    rivers = gpd.read_file(GPKG_PATH)
    river = rivers[rivers["name"] == name]
    return simplified_river_path(river.geometry, extend_to_end_points)


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # Example usage with plotting
    river_path = load_and_process_river("Otekaieke River")

    if river_path:
        fig, ax = plt.subplots(figsize=(10, 6))
        gpd.GeoSeries([river_path]).plot(ax=ax, color="red")  # Plot the simplified path
        ax.set_title("Simplified Path of Otekaieke River")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        plt.show()
