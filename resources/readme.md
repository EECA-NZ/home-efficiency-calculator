# Data Analysis

This folder contains scripts and data for various analyses relating to climate zones, electricity plans, and methane plans. Below is an overview of the necessary files within the `supplementary_data` folder and instructions on how to run the analysis scripts.

## Supplementary Data

Ensure the following datasets are available in the `supplementary_data` folder:

- **EDB Boundaries** - Obtained from an internal EECA dataset (RETA).
- **Postcode Boundaries** - Obtained from NZ Post.
- **NZ River Geography** - Obtained from LINZ.
- **Territorial Authority Boundaries** - Obtained from Statistics NZ.
- **Tariff Dataset** - Provided to EECA by Powerswitch.

### Directory Structure
```
supplementary_data/
├── EDB_Boundaries
│   ├── EDBBoundaries.cpg
│   ├── EDBBoundaries.dbf
│   ├── EDBBoundaries.prj
│   ├── EDBBoundaries.shp
│   └── EDBBoundaries.shx
├── PNF_V2024Q2_V01
│   ├── 001pnftechguide.pdf
│   ├── Change_History.csv
│   ├── PN_V2024Q2V01_LOBBIES.dat
│   ├── PN_V2024Q2V01_LOBBIES.dbf
│   ├── PN_V2024Q2V01_LOBBIES.id
│   ├── PN_V2024Q2V01_LOBBIES.map
│   ├── PN_V2024Q2V01_LOBBIES.prj
│   ├── PN_V2024Q2V01_LOBBIES.shp
│   ├── PN_V2024Q2V01_LOBBIES.shx
│   ├── PN_V2024Q2V01_LOBBIES.tab
│   ├── PN_V2024Q2V01_LOBBIES_NZTM.dat
│   ├── PN_V2024Q2V01_LOBBIES_NZTM.dbf
│   ├── PN_V2024Q2V01_LOBBIES_NZTM.id
│   ├── PN_V2024Q2V01_LOBBIES_NZTM.map
│   ├── PN_V2024Q2V01_LOBBIES_NZTM.prj
│   ├── PN_V2024Q2V01_LOBBIES_NZTM.shp
│   ├── PN_V2024Q2V01_LOBBIES_NZTM.shx
│   ├── PN_V2024Q2V01_LOBBIES_NZTM.tab
│   ├── PN_V2024Q2V01_POLYGONS.cpg
│   ├── PN_V2024Q2V01_POLYGONS.dat
│   ├── PN_V2024Q2V01_POLYGONS.dbf
│   ├── PN_V2024Q2V01_POLYGONS.id
│   ├── PN_V2024Q2V01_POLYGONS.map
│   ├── PN_V2024Q2V01_POLYGONS.prj
│   ├── PN_V2024Q2V01_POLYGONS.shp
│   ├── PN_V2024Q2V01_POLYGONS.shx
│   ├── PN_V2024Q2V01_POLYGONS.tab
│   ├── PN_V2024Q2V01_POLYGONS_NZTM.cpg
│   ├── PN_V2024Q2V01_POLYGONS_NZTM.dat
│   ├── PN_V2024Q2V01_POLYGONS_NZTM.dbf
│   ├── PN_V2024Q2V01_POLYGONS_NZTM.id
│   ├── PN_V2024Q2V01_POLYGONS_NZTM.map
│   ├── PN_V2024Q2V01_POLYGONS_NZTM.prj
│   ├── PN_V2024Q2V01_POLYGONS_NZTM.shp
│   ├── PN_V2024Q2V01_POLYGONS_NZTM.shx
│   └── PN_V2024Q2V01_POLYGONS_NZTM.tab
├── __init__.py
├── eeca_niwa_climate_boundaries
│   ├── eeca_niwa_climate_boundaries.gpkg
│   └── eeca_niwa_climate_boundaries_metadata.json
├── lds-nz-river-name-lines-pilot-GPKG
│   ├── nz-river-name-lines-pilot.gpkg
│   ├── nz-river-name-lines-pilot.txt
│   └── nz-river-name-lines-pilot.xml
├── statsnz-territorial-authority-2023-clipped-generalised-SHP
│   ├── territorial-authority-2023-clipped-generalised-ISO.pdf
│   ├── territorial-authority-2023-clipped-generalised.cpg
│   ├── territorial-authority-2023-clipped-generalised.dbf
│   ├── territorial-authority-2023-clipped-generalised.prj
│   ├── territorial-authority-2023-clipped-generalised.shp
│   ├── territorial-authority-2023-clipped-generalised.shx
│   ├── territorial-authority-2023-clipped-generalised.txt
│   └── territorial-authority-2023-clipped-generalised.xml
└── tariff_data
    ├── __init__.py
    ├── tariffDataReport_240903.csv
```

## Running Analysis Scripts

To perform the various analyses, navigate to the respective directories and run the Python scripts as outlined below:

```bash
# Generate a geopackage with the climate zone boundaries
cd climate_zone_boundaries
python climate_zone_boundaries.py
cd ..

# Generate lookup tables from postcode to climate zone and edb region
cd postcode_lookup_tables
python create_postcode_to_climate_lookup.py
python create_postcode_to_edb_region_lookup.py
cd ..

# Create summary of available electricity plans by edb region and a looup table selecting one per region
cd electricity_plans
python electricity_plans_analysis.py
python optimal_electricity_plans.py
cd ..

# Create summary of available methane plans by edb region and a lookup table selecting one per region
cd methane_plans
python methane_plans_analysis.py
python optimal_methane_plans.py
cd ..
```

## Output files

The above steps will ultimately update the following CSV files:
* `home-efficiency-calculator-dev/resources/postcode_lookup_tables/output/postcode_to_climate_zone.csv`
* `home-efficiency-calculator-dev/resources/postcode_lookup_tables/output/postcode_to_edb_region.csv`
* `home-efficiency-calculator-dev/resources/electricity_plans/output/selected_electricity_plan_tariffs_by_edb_gst_inclusive.csv`
* `home-efficiency-calculator-dev/resources/methane_plans/output/selected_methane_plan_tariffs_by_edb_gst_inclusive.csv`

Make sure to commit any changes to these files. After updating, return to the root directory and reinstall the package with:
```
python -m pip install .
```
This ensures that the updated versions are loaded into the installed library.