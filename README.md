# Observation-Validated Rainfall–Runoff Modelling with GR4J

A hydrology-first study of GR4J calibration, parameter equifinality, and transferability
in the **Murray River at Upper Murray (gauge 114001A)**, North East Coast, Queensland,
using **CAMELS-AUS v2** observations.

A self-coded GR4J conceptual model is calibrated against observed discharge with standard
hydrologic diagnostics (KGE / NSE / PBIAS), then a multimodal optimizer (RS-SPSO) is used
to probe whether multiple distinct parameter sets calibrate comparably well, and a Klemeš
(1986) differential split-sample test checks how well each set transfers between wet and
dry climatic regimes.

```
CAMELS-AUS  P & PET  ->  GR4J  ->  Qsim  vs  Qobs  ->  KGE objective
                                                       /            \
                                            DE baseline            RS-SPSO
                                                       \            /
                                              multiple parameter sets
                                                          |
                                                  Klemeš validation
```

## Basin

| | |
|---|---|
| Gauge | 114001A — Murray River at Upper Murray |
| Region | North East Coast (Tully–Murray Rivers), QLD |
| Catchment area | 155.4 km² |
| Outlet | −18.107°, 145.805° |
| Dataset | CAMELS-AUS v2 |
| Record used | 1970-05-28 → 2021-06-30 (daily) |
| Forcing | precipitation (AGCD), PET (Morton), streamflow (mm/day) |

> PET currently uses the Morton series that ships with CAMELS-AUS. A Hargreaves PET path
> exists in `codes/prepare_basin_data.py` and is planned to become the primary before the
> final report (see Roadmap).

## Repository layout

```
flood_hydrology_modeling/
├── README.md
├── requirements.txt
├── LICENSE
├── CITATION.cff
├── .gitignore
├── codes/
│   ├── GR4J.ipynb                    # GR4J core: compute_Q (imported as a library)
│   ├── Metric_Calculation.ipynb      # KGE, NSE, PBIAS (imported as a library)
│   ├── rs_spso.py                    # RS-SPSO optimizer (importable library — silent)
│   ├── rs_spso.ipynb                 # RS-SPSO demos, benchmarks, animation
│   ├── prepare_basin_data.py         # alternative prep: Hargreaves PET + water-balance QC
│   ├── 01_process_csv.ipynb          # builds data/processed/prec_PET_sf.csv (active data path)
│   ├── 02_gr4j_calibration.ipynb     # Differential Evolution baseline calibration
│   ├── 03_multimodal_calibration.ipynb  # RS-SPSO multimodal / equifinality search
│   └── 04_klemes_validation.ipynb    # wet<->dry differential split-sample validation
├── data/
│   ├── README.md
│   └── processed/prec_PET_sf.csv     # the only committed data (P, PET, Q for 114001A)
└── docs/
    ├── algorithm_01.md               # RS-SPSO algorithm design notes
    ├── pseudo_code_01.md             # RS-SPSO pseudocode (v2)
    ├── perrin2003.pdf                # GR4J reference (Perrin et al., 2003)
    └── GR4J.png
```

The raw CAMELS-AUS v2 archive (~5 GB) is **not** committed — see `data/README.md` for how
to obtain it and regenerate the processed CSV.

## Method

- **Model** — GR4J (Perrin et al., 2003), four parameters: X1 production-store capacity,
  X2 groundwater exchange, X3 routing-store capacity, X4 unit-hydrograph time. Implemented
  from the governing equations (numba-accelerated) in `GR4J.ipynb`.
- **Objective** — 1 − KGE, with a **730-day (2-year) warm-up** discarded before scoring and
  NaN observation days masked out.
- **Baseline calibration (03)** — SciPy `differential_evolution` over
  X1∈[1,1500], X2∈[−5,5], X3∈[1,500], X4∈[0.5,4], seed 42. Reaches **KGE ≈ 0.87** on the
  calibration period.
- **Multimodal calibration (04)** — RS-SPSO (Respawning Speciation-based PSO) searches the
  normalized `[0,1]⁴` parameter cube — so the species distance treats all four parameters
  fairly rather than being dominated by the wide X1/X3 ranges — for several distinct
  parameter sets that all calibrate well → the equifinality analysis.
- **Klemeš validation (05)** — GR4J is calibrated on the wettest contiguous block of years
  and validated on the driest, and vice-versa; `klemes_warmup` applies a per-split warm-up
  so validation windows do not start with cold stores.

## Running it

```bash
python -m venv venv
# Windows: venv\Scripts\activate   |   macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
jupyter lab            # or: jupyter notebook
```

Notebooks import each other via [`import-ipynb`] (e.g. `from GR4J import compute_Q`), so
**run them from inside `codes/`**. Suggested order: `01_process_csv` → `02` → `03` → `04`.
`GR4J.ipynb` and `Metric_Calculation.ipynb` are libraries and don't need to be run directly.
The RS-SPSO optimizer is imported from the plain module `rs_spso.py` (not the notebook), so
pulling it into a calibration run doesn't execute the notebook's demos — `rs_spso.ipynb` is
kept only for the benchmarks and animation.

## Roadmap

- **Flood-frequency analysis** (annual-maximum Q2…Q100) — planned, not yet implemented.
- **Hargreaves PET** as the primary forcing (currently Morton).
- **PSO vs RS-SPSO** diversity comparison (kept out of the initial release).

## References

- Perrin, C., Michel, C., Andréassian, V. (2003). *Improvement of a parsimonious model for
  streamflow simulation.* Journal of Hydrology, 279, 275–289.
- Gupta, H. V., et al. (2009). *Decomposition of the mean squared error and NSE performance
  criteria* (KGE). Journal of Hydrology, 377, 80–91.
- Klemeš, V. (1986). *Operational testing of hydrological simulation models.* Hydrological
  Sciences Journal, 31, 13–24.
- Fowler, K., et al. CAMELS-AUS dataset.

## License

MIT — see [LICENSE](LICENSE).
