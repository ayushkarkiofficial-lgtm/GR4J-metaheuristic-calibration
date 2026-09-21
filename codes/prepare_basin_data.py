"""
prepare_basin_data.py  —  Day 1-2 of the "One Basin, Done Right" study.

Turns the raw CAMELS-AUS v2 CSVs into ONE clean, paired daily table
(P, PET, Q) for a single basin: the exact input GR4J consumes.

Steps: load single-basin columns -> replace -99.99 no-data with NaN ->
compute Hargreaves PET from tmax/tmin + catchment latitude -> QC and
water-balance closure -> write data/processed/basin_<ID>.csv.

Run:  python codes/prepare_basin_data.py
Switch basins: change GAUGE_ID below (see basin-selection ranking in the
design spec / commit notes for alternatives, e.g. 108002A, 124002A).
"""
from pathlib import Path
import numpy as np
import pandas as pd

# ---------------------------------------------------------------- config
GAUGE_ID      = "114001A"          # recommended monsoon-analog basin (QLD, snow-free)
PRECIP_SOURCE = "AGCD"             # "AGCD" or "SILO"
NODATA        = -99.99             # CAMELS-AUS missing-value sentinel

ROOT   = Path(__file__).resolve().parents[1]
DATA   = ROOT / "data"
HYDRO  = DATA / "05_hydrometeorology"
OUTDIR = DATA / "processed"
OUTDIR.mkdir(exist_ok=True)

FILES = {
    "Q":    DATA  / "03_streamflow" / "streamflow_mmd.csv",
    "P":    HYDRO / "01_precipitation_timeseries" / f"precipitation_{PRECIP_SOURCE}.csv",
    "tmax": HYDRO / "03_Other" / "AGCD" / "tmax_AGCD.csv",
    "tmin": HYDRO / "03_Other" / "AGCD" / "tmin_AGCD.csv",
    "ET_morton": HYDRO / "02_EvaporativeDemand_timeseries" / "et_morton_actual_SILO.csv",
    "loc":  DATA  / "02_location_boundary_area" / "location_boundary_area.csv",
}


def load_series(path, gauge):
    """Read the date + single-gauge column from a CAMELS-AUS timeseries CSV."""
    df = pd.read_csv(path, usecols=lambda c: c in ("year", "month", "day", gauge))
    if gauge not in df.columns:
        raise KeyError(f"gauge {gauge} not found in {path.name}")
    df.index = pd.to_datetime(df[["year", "month", "day"]])
    s = df[gauge].astype(float)
    return s.where(s > NODATA + 1e-6)          # -99.99 -> NaN


def hargreaves_pet(tmax, tmin, lat_deg):
    """FAO-56 Hargreaves PET (mm/day) from daily tmax/tmin and latitude."""
    tmean = (tmax + tmin) / 2.0
    trange = (tmax - tmin).clip(lower=0)       # guard bad days
    j = tmax.index.dayofyear.to_numpy()
    phi = np.deg2rad(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi / 365 * j)                 # earth-sun distance
    dec = 0.409 * np.sin(2 * np.pi / 365 * j - 1.39)            # solar declination
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1, 1))  # sunset hour angle
    Gsc = 0.0820                                                # MJ m-2 min-1
    Ra = (24 * 60 / np.pi) * Gsc * dr * (
        ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws)
    )                                                           # MJ m-2 day-1
    Ra_mm = 0.408 * Ra                                          # -> mm/day equiv.
    pet = 0.0023 * Ra_mm * (tmean + 17.8) * np.sqrt(trange)
    return pet.clip(lower=0)


def main():
    loc = pd.read_csv(FILES["loc"]).set_index("station_id")
    lat = float(loc.loc[GAUGE_ID, "lat_centroid"])
    area = float(loc.loc[GAUGE_ID, "catchment_area"])

    Q    = load_series(FILES["Q"],    GAUGE_ID)
    P    = load_series(FILES["P"],    GAUGE_ID)
    tmax = load_series(FILES["tmax"], GAUGE_ID)
    tmin = load_series(FILES["tmin"], GAUGE_ID)
    ETm  = load_series(FILES["ET_morton"], GAUGE_ID)  # CAMELS ref PET, cross-check

    PET = hargreaves_pet(tmax, tmin, lat)

    df = pd.DataFrame({"P": P, "PET": PET, "PET_morton": ETm, "Q": Q})
    df.index.name = "date"

    # --- QC / water-balance closure -------------------------------------
    both = df.dropna(subset=["P", "PET", "Q"])
    p_mean, pet_mean, q_mean = both.P.mean(), both.PET.mean(), both.Q.mean()
    runoff_ratio = q_mean / p_mean
    et_implied   = p_mean - q_mean                       # long-term ET (closure)

    print(f"=== Basin {GAUGE_ID}  (lat {lat:.3f}, area {area:.1f} km2) ===")
    print(f"precip source        : {PRECIP_SOURCE}")
    print(f"full span            : {df.index.min().date()} -> {df.index.max().date()}  ({len(df)} days)")
    print(f"paired P/PET/Q days  : {len(both)}  ({100*len(both)/len(df):.1f}% of span)")
    for col in ("P", "PET", "Q"):
        s = df[col]
        print(f"  {col:11s} valid={s.notna().sum():6d}  "
              f"missing={s.isna().sum():5d}  "
              f"min={s.min():.2f} mean={s.mean():.3f} max={s.max():.1f}")
    print("--- long-term water balance (paired days) ---")
    print(f"  P   = {p_mean*365.25:8.1f} mm/yr")
    print(f"  Q   = {q_mean*365.25:8.1f} mm/yr   runoff ratio Q/P = {runoff_ratio:.3f}")
    print(f"  P-Q = {et_implied*365.25:8.1f} mm/yr (implied actual ET)")
    print(f"  PET(Hargreaves) = {pet_mean*365.25:7.1f} mm/yr | "
          f"PET(Morton)= {both.PET_morton.mean()*365.25:7.1f} mm/yr")
    if runoff_ratio > 1:
        print("  !! WARNING: runoff ratio > 1 (P underestimated or wrong basin) ")
    if et_implied < 0:
        print("  !! WARNING: implied ET < 0 (water-balance not closing)")

    out = OUTDIR / f"basin_{GAUGE_ID}.csv"
    df.to_csv(out, float_format="%.4f")
    print(f"\nwrote {out}  ({len(df)} rows, cols={list(df.columns)})")


if __name__ == "__main__":
    main()
