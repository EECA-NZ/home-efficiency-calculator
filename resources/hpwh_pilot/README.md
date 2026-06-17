This folder contains an interim dataset based on less than 1 year of performance data from heat pump hot water systems.

Use it with:
`.venv/bin/python scripts/hpwh_pilot_hesc_input_calibration.py`

The script uses the `niwa_climate_zone` field for climate-specific HESC inputs, runs the HESC-input grid search, prints old/current/best performance metrics, and writes a per-site comparison CSV to `/tmp/hpwh_pilot_hesc_input_comparison.csv`.

By default, the calibration includes only sites with at least 270 days of data. Use `--min-days-with-data` to run sensitivity checks with a different duration threshold.
