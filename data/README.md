# Data

The raw **CAMELS-AUS v2** archive (~5 GB) is **not** committed to this repository. Only the
small processed table the notebooks actually consume is tracked:

```
data/processed/prec_PET_sf.csv
```

## Basin

| | |
|---|---|
| Gauge ID | 114001A |
| Name | Murray River at Upper Murray |
| Region | North East Coast (Tully–Murray Rivers), QLD |
| Catchment area | 155.4 km² |
| Outlet lat/long | −18.1069, 145.8054 |
| Dataset | CAMELS-AUS v2 |

## Processed file — `processed/prec_PET_sf.csv`

Daily series, **1970-05-28 → 2021-06-30**. Columns:

| Column | Meaning | Units |
|---|---|---|
| `date` | calendar date | — |
| `prec_AGCD` | precipitation (AGCD) | mm/day |
| `prec_SILO` | precipitation (SILO, alternative) | mm/day |
| `PET_morton` | Morton actual ET (used as PET forcing) | mm/day |
| `sf_mmd` | observed streamflow (non-gap-filled); `-99.99` no-data → NaN | mm/day |

GR4J is currently forced with `prec_AGCD` and `PET_morton`; `sf_mmd` is the calibration
target.

## Regenerating the processed file

1. Download **CAMELS-AUS v2** and place it under `data/` in its native layout
   (`01_id_name_metadata/`, `02_location_boundary_area/`, `03_streamflow/`,
   `05_hydrometeorology/`, …). These folders are git-ignored.
2. Run `codes/process_csv.ipynb` — it slices gauge `114001A` from the streamflow, AGCD/SILO
   precipitation, and Morton PET series over the study window and writes
   `data/processed/prec_PET_sf.csv`.

An alternative preparation script, `codes/prepare_basin_data.py`, builds a single paired
table with **Hargreaves PET** and a long-term water-balance QC check
(`data/processed/basin_114001A.csv`). It is not on the current calibration path but is kept
for the planned Hargreaves PET swap.

## Source & attribution

CAMELS-AUS: Fowler et al. Please cite the dataset per its own terms when using these data.
The processed CSV here is a derived slice for a single gauge, provided for reproducibility.
