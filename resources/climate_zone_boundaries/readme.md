## Climate-zone-boundaries

This directory contains a Python script that assembles an approximate boundary for the 18 NIWA climate zones in New Zealand. These are saved as some plot images and a shapefile in the `output` directory.

The climate zones are the ones referred to by the NIWA TMY climate data set. Climate zone boundaries follow territorial authority boundaries except for Rangitikei which is split between Taupo and Manawatu, and Waitaki which is split between Central Otago and Dunedin.

Advice from BRANZ:
    "There's no shape file for the 18 climate areas relating to the 18 NIWA weather file sets.
    Re Waitaki and Rangitikei, here's how we define this in the H1 AS and VM documents:
    Rangitikei District (north of 39°50'S (-39.83)): 4
    Rangitikei District (south of 39°50'S (-39.83)): 3
    Waitaki District (true left of the Otekaike river): 6
    Waitaki District (true right of the Otekaike river): 5"

### Usage
```
python -m venv myenv
myenv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install --upgrade geopandas fiona shapely matplotlib ipython pyproj scikit-image ipython
python -i climate_zone_boundaries.py
```
