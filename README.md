<p align="center">
  <a href="https://github.com/EnAccess/oseas26-solar-markets-sales-data">
    <img
      src="https://drive.google.com/uc?id=1gtL_p7l3HbOcCzc09A7KW5d7B5qn-BDs"
      alt="Identifying solar markets based on sales data"
      width="640"
    >
  </a>
</p>
<p align="center">
    October 26-27 | Open Source in Energy Access Symposium Hackathon | Kigali, Rwanda
</p>

---

# Identifying Solar Markets Based on Sales Data

Build a market-reality layer for the
[Energy Access Explorer (EAE)](https://www.energyaccessexplorer.org) that
distinguishes where the off-grid solar market has failed to arrive from where it
has quietly succeeded.

## Abstract and goal

Grant capital and results-based financing for off-grid solar tend to flow toward
territories that are already commercially viable, because those are the
territories that are visible in the data. Places that remain dark across every
available dataset also remain dark in most funding decisions.

The sector does not lack maps of where energy demand should exist; the Energy
Access Explorer (EAE) already provides these, running multi-criteria analysis on
the fly across normalized demand and supply layers so that planners can reweight
criteria interactively and rank priority areas from their own perspective. What
EAE currently doesn't include is a **market-reality layer**: a view of where the
off-grid solar market has failed to arrive, and a means of distinguishing that
from where it has quietly succeeded. This challenge asks teams to build that layer
for a country of their choice, integrating sales data.

VIIRS and Black Marble have a radiance detection floor well above the emissions of
a solar home system or pico-lantern, which means a village where every household
owns a solar home system registers as dark, and a village with no energy access at
all also registers as dark. The intuitive formulation of this challenge — in which
dense population combined with zero nighttime lights is taken to indicate an
underserved community — will therefore surface precisely those territories where
the off-grid sector has already done its best work. Darkness indicates the absence
of a grid connection, which defines the addressable market for distributed
renewable energy, but it says nothing about whether that market has been served.

Actual penetration must be measured from sources that measure penetration, which
is why georeferenced household survey data (DHS and MICS geo-clusters carrying
solar panel ownership and electricity source, and ESMAP Multi-Tier Framework
surveys carrying explicit Tier 0 to 5 access) forms the backbone of this
challenge. GOGLA sales data is semi-annual, affiliate-reported, and aggregated to
country and product category, with company-level detail held confidential under a
three-data-point rule and no public access to the underlying platform, so it
should be treated as a national control total against which a survey-derived
penetration surface is calibrated — rather than as a pixel-level penetration layer
in its own right.

## Expected outcomes

Three core deliverables (plus an optional prototype):

- **Predictive model of off-grid solar penetration:** an open-source model trained
  on georeferenced survey labels, with blocked cross-validation performance
  reported alongside random cross-validation performance, and feature analysis
  framed as hypotheses rather than findings.
- **EAE-conformant layer:** at least one raster, with values normalized 0 to 1 and
  direction documented, accompanied by metadata covering source, year, method, and
  known limitations.
- **Documentation and limitations statement:** a brief write-up describing the
  datasets used, the modelling approach, the validation methodology, and accuracy
  metrics, together with a one-page statement of what the model cannot see, where
  it will be wrong, and who it would misallocate capital toward.
- **Interactive prototype (optional):** a map in which priority zones are visible,
  inspectable, and traceable back to the layers that produced them.

## Required knowledge

### Stack

- **Python geospatial:** GeoPandas for vector processing; Rasterio / GDAL for
  raster analysis.
- **Machine learning:** Scikit-learn, XGBoost, LightGBM for modelling off-grid
  solar penetration.
- **Geospatial and socio-economic data:** NASA Black Marble; WorldPop or Meta High
  Resolution Settlement Layer for population; Meta Relative Wealth Index via the
  Humanitarian Data Exchange; Gridfinder or OpenStreetMap for grid infrastructure.

#### Solar market and sales data

This is the suggested group that allows a team to distinguish a village the market
has already served from a village it has never reached. Teams are encouraged to
identify more data during the hackathon. Each source is listed with the resolution
it operates at, because that determines the job it can do:

1. **GOGLA Sales and Impact Data:** unit sales by country, region, and product
   category, split between cash and PAYGo, reported semi-annually and annually by
   GOGLA affiliates. Published as public reports with accompanying tables. The
   underlying platform at data.gogla.org is restricted to companies that report
   into it, and a three-data-point rule enforces confidentiality, so
   distributor-level footprints are not obtainable. *Resolution:* national.
   *Job:* control total.
2. **Off-Grid Solar Market Trends Report (GOGLA and ESMAP):** market sizing,
   investment gap, and outlook. *Resolution:* regional and national. *Job:*
   context and sanity check.
3. **GOGLA deals database:** investment flows into off-grid solar companies from
   2012 onward. *Resolution:* company. *Job:* identifying which distributors are
   capitalized to expand into a new territory.
4. **PAYGo PERFORM:** standardized key performance indicators for PAYGo company
   performance, including portfolio quality and repayment. *Resolution:* company,
   aggregated. *Job:* identifying which distributors could absorb and deploy a
   grant.
5. **AMDA Benchmarking Africa's Minigrids:** operational and financial benchmarks
   aggregated across member developers and countries. *Resolution:* operator,
   aggregated. *Job:* context on mini-grid viability.
6. **ENERGYDATA.INFO (ESMAP / World Bank):** open data registry with API access,
   carrying existing and candidate mini-grid project datasets, grid network data,
   and the Africa Electricity Grids Explorer. *Resolution:* point and line
   geometry. *Job:* the only georeferenced market and infrastructure source in
   this group.
7. **Infrastructure data available in Energy Access Explorer.**
8. **National results-based financing and electrification programme records:**
   connection counts and subsidy disbursements published by rural electrification
   agencies and programme administrators. *Resolution:* sub-national where
   available, variable quality. *Job:* validation and ground-truthing.
9. **DHS and MICS geo-clusters, and ESMAP Multi-Tier Framework surveys:**
   household solar panel ownership, electricity source, and Tier 0 to 5 access,
   carried at cluster level with displaced GPS. *Resolution:* point. *Job:* this
   is the only source in the challenge that measures penetration at a location,
   and it is therefore the label.

### Programming languages

- Python
- SQL
- JavaScript / any other for frontend

### Helpful experiences

- Experience with Geospatial Analysis and Remote Sensing using, for example,
  Python, Google Earth Engine, PostGIS, QGIS, GeoJSON, GeoParquet, or spatial SQL.
- Experience with Machine Learning and Predictive Modelling, including feature
  engineering, model evaluation, and validation of spatially autocorrelated data.
- Experience with Data Science and Analytics using Python, Pandas and GeoPandas,
  data cleaning and integration, and statistical analysis.
- Familiarity with household survey microdata, for example DHS, MICS, LSMS, or
  Multi-Tier Framework surveys.
- Knowledge of off-grid solar markets and distribution models, including solar
  home systems, pico-solar, and results-based financing.
- Dashboard and mapping development skills.

## Person of contact supporting this challenge

- Preston Adie

## Getting started

- Questions about this challenge? Join the OSEAS Discord server: <https://community.oseas.org/> — that's where you reach the case givers and mentors, before kickoff and throughout the hackathon. 
- Introduce yourself in the `#introductions` channel and join the relevant
  channels for this challenge.
- Read the documentation:
  - [Energy Access Explorer](https://www.energyaccessexplorer.org)
  - [EAE GitHub](https://github.com/energyaccessexplorer)
  - [EAE Technical Note](https://www.wri.org/research/energy-access-explorer-data-and-methods?ap3c=IGaj6AgspJqgeKwBAGaj6AgmzCZ5Iv70Fr7H6ahniwtFr1FOgg)

---

## Our solution (work in progress)

We are building the market-reality layer for **Rwanda** at 1 km resolution:

1. **Labels:** share of households using off-grid solar for lighting, from the Rwanda
   Population and Housing Census 2022 (sector level), upgraded later to DHS 2019-20 GPS clusters.
2. **Features:** VIIRS night lights, WorldPop population, Meta Relative Wealth Index,
   distance to grid (Gridfinder), travel time to cities and built-up share.
3. **Model:** LightGBM, with random and blocked (by district) cross-validation and SHAP
   feature analysis framed as hypotheses.
4. **Calibration:** logit shift so the national total matches a control total (census now,
   GOGLA sales next).
5. **Outputs:** two EAE-conformant 0-1 rasters (off-grid solar penetration, underserved
   market) with metadata, a limitations statement and an interactive map. The map adds a "who
   should serve them" layer that sorts every sector into grid connections, a working solar
   market, or a solar market not yet arrived.

### Results (midpoint, Rwanda 2022)

| CV scheme | Target | Mean baseline R² | Linear R² | LightGBM R² | LightGBM MAE |
| --- | --- | --- | --- | --- | --- |
| Random 5-fold | solar share | −0.02 | 0.26 | 0.31 | 7.6 pp |
| Blocked by district | solar share | −0.04 | 0.23 | **0.21** | **8.0 pp** |
| Random 5-fold | grid share | −0.01 | 0.62 | 0.67 | 10.5 pp |
| Blocked by district | grid share | −0.02 | 0.61 | **0.63** | **11.3 pp** |

416 sectors, full `reports/cv_results.csv`. Random CV overstates accuracy because neighbouring
sectors are similar; the blocked score is what to expect in a district the model has never
seen. Grid access is predictable from what satellites see; solar use much less so. Under
blocked CV LightGBM does not beat a linear model on solar share, which we report as a finding:
with 416 labels and an estimated solar/grid split, the signal is weak.

After calibration (logit shift −0.06: the model's national level was already close), pixel
predictions averaged back to districts differ from the census by 4.3 pp on average; the worst
district is Nyaruguru (−16.9 pp), whose unusually high solar use (39%) the model under-predicts.

**Feature analysis, as hypotheses (associations in the model, not causes)**
(`reports/feature_importance.png`, `reports/feature_effects.csv`):

- **H1.** Sectors with lower population density and less built-up land have higher predicted
  solar penetration: solar fills in where the grid is thin.
- **H2.** Longer travel time to a city goes with higher predicted solar penetration.
- **H3.** Distance to the grid alone is a weaker signal than density: the most remote pixels
  are not the ones with the most solar, consistent with remote, poor areas being reached by
  neither grid nor solar companies.
- **H4.** Grid share rises with built-up area, night lights, density and wealth, as expected.

**Independent check with the Rwanda DHS 2025 survey** (`python -m solar_markets.validate`,
`reports/dhs_validation.*`). DHS 2025 asked 14,427 households their main type of light, with
solar separate from grid, and is designed for district estimates. Across the 30 districts:

| Compared with DHS 2025 | Correlation r | Rank correlation | Ours − DHS (level) |
| --- | --- | --- | --- |
| Solar share, census labels (estimated solar/grid split) | 0.79 | 0.76 | −6.0 pp |
| Solar share, our calibrated 1 km model | 0.84 | 0.71 | −6.7 pp |
| Grid share, census labels | 0.91 | 0.82 | −6.8 pp |
| Neither grid nor solar, census labels | 0.68 | 0.51 | +12.4 pp |

The district pattern of our solar estimates agrees with an independent survey, which supports
the estimated solar/grid split. The level gap is three years of growth: nationally DHS 2025
finds solar 19.6%, grid 53.9% and neither 26.5%, against 13.9%, 47.1% and 38.5% in the 2022
census. Only district aggregates are written; DHS household data stays in `data/raw`.

### Labels

`python -m solar_markets.labels` builds one row per sector (416) with the share of households
whose main light is grid electricity, solar, an unserved source (kerosene, candles, firewood,
batteries, flashlight, lantern) or other. Two sources, set by `labels.source` in `config.yml`:

- **`census_tables` (current, no login):** the published PHC5 2022 tables, which cover the full
  census (3.3 million households). The sector table reports grid and solar together as
  "electricity", so the **electrified** and **unserved** shares per sector are measured, but the
  **split into solar and grid is estimated**: solar ≈ electrified − grid-connected per sector,
  scaled within each province to the published province solar share (Table 8.12) and capped at
  the electrified share. National result: solar 13.9%, grid 47.1%, unserved 38.5%, matching the
  published national figures.
- **`census` (preferred when available):** the public microdata (10% sample, needs a NISR
  microdata account), which reports solar separately for each household, so no split is
  needed. Switching is one line in `config.yml`.

### Features

`python -m solar_markets.features` builds `data/processed/feature_stack.tif`: one band per
feature on a 30 arc-second grid (~0.93 km, EPSG:4326, 258 x 228 pixels over Rwanda), NaN
outside the country. Earth Engine bands are aggregated on the server onto exactly this grid
and cached in `data/interim/ee_stack.tif`.

| Band | Meaning | Source | Year | Native resolution | Aggregation to 1 km | Model transform | Licence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ntl` | night-time radiance (nW/cm²/sr) | VIIRS annual V2.2 (`NOAA/VIIRS/DNB/ANNUAL_V22`, band `average`) | 2022 | ~460 m | mean | log1p | CC BY 4.0 (EOG) |
| `pop` | people per pixel | WorldPop (`WorldPop/GP/100m/pop`) | 2020 | 100 m | sum | log1p | CC BY 4.0 |
| `travel_min` | minutes to the nearest city | Oxford MAP (`projects/malariaatlasproject/assets/accessibility/accessibility_to_cities/2015_v1_0`) | 2015 | ~1 km | mean | log1p | CC BY 4.0 |
| `built` | share of built-up land | ESA WorldCover v200, class 50 (`ESA/WorldCover/v200`) | 2021 | 10 m | mean | none | CC BY 4.0 |
| `rwi` | Relative Wealth Index | Meta RWI (HDX) | 2021 | ~2.4 km points | nearest point | none | CC BY-NC 4.0 |
| `dist_grid` | km to the nearest grid line | Gridfinder (Zenodo 3628142) | 2020 | vector | distance from pixel centre | log1p | CC BY 4.0 |

Distance to the grid is measured on a raster padded by 30 km, so lines just across the border
count. The training table (`data/processed/train_table.csv`, one row per sector) holds the
**population-weighted mean** of each band inside the sector (plain mean for `pop`), so the
features describe where people live rather than empty land. Sectors smaller than one pixel take
the pixel under their centre. A quick-look of every band is saved to `reports/feature_bands.png`.

### Model and validation

`python -m solar_markets.model` trains one LightGBM regression per target in `config.yml`
(`solar_share` for the penetration layer, `grid_share` for the underserved layer) on the six
features, with `log1p` applied to `ntl`, `pop`, `travel_min` and `dist_grid`.

- **Two cross-validation schemes**, both in `reports/cv_results.csv`: random 5-fold, and
  blocked 5-fold where whole districts are held out together. Neighbouring sectors are similar,
  so random CV is optimistic; the blocked score is what to expect in a district the model has
  never seen. Each scheme compares LightGBM with two baselines (national mean, linear
  regression). `mae_pp` is the mean absolute error in percentage points.
- **Feature analysis as hypotheses:** SHAP values of the final model (`reports/feature_importance.png`,
  `reports/feature_effects.csv`). `direction` `+` means higher values of the feature go with
  higher predictions. This is an association, not a cause.
- **Prediction:** every pixel with all features present, clipped to 0-1, written to
  `outputs/<target>_pred.tif`.
- **Change-of-support check:** pixel predictions averaged back to sectors (population-weighted)
  and compared with the labels (`reports/reaggregation.csv`, `reports/reaggregation.png`).
  Points far from the diagonal show where the 1 km map disagrees with the sector averages it
  was trained on.

### Calibration

`python -m solar_markets.calibrate` scales the predicted solar share so that predicted solar
households (share x population / average household size) add up to a national control total.
Every pixel is shifted by the same constant on the logit scale, so values stay in 0-1 and the
ranking of places is unchanged: calibration changes how much solar the map shows, not where.

- **Target now:** the census national share and average household size computed by the labels
  stage (`reports/labels_summary.json`). Set `calibration.target_share` in `config.yml` to use
  another figure, such as a GOGLA-derived share (the planned upgrade).
- `reports/calibration.json` records the target, household size, totals before and after, and
  the shift (|shift| < 0.3 means the model's level was already close). Calibrated pixels are
  re-aggregated to districts and compared with census district shares
  (`reports/calibration_districts.csv`, MAE in percentage points).

### Output layers (EAE)

`python -m solar_markets.export` writes two Cloud-Optimised GeoTIFFs to `outputs/`, normalised
to 0-1 (1 = high), nodata -9999 outside the country, each with a `.yml` metadata sidecar
(source, year, method, validation, calibration, direction, limitations, licence):

| Layer | File | 1 means | 0 means |
| --- | --- | --- | --- |
| Off-grid solar penetration | `rwa_ogs_penetration_2022_1km.tif` | highest predicted share of households using off-grid solar | no predicted solar use |
| Underserved solar market | `rwa_ogs_underserved_2022_1km.tif` | most households with neither grid nor solar per pixel | none, or nobody lives there |

Unserved households per pixel = households x max(0, 1 - predicted grid share - calibrated solar
share). Normalisation is a robust min-max between the 2nd and 98th percentiles, so a few extreme
pixels do not squash the rest; counts are kept linear so the largest unserved populations stand
out. The penetration layer is nodata where fewer than 5 people live in a pixel (national parks,
lakes): a household share means nothing there. The layers are
licensed CC BY-NC 4.0 because the Meta Relative Wealth Index input is non-commercial.
Quick-looks for the slides are saved to `reports/`.

### Interactive map

`python -m solar_markets.webmap` writes `docs/map.html`, one self-contained page (Leaflet, data
embedded) for desktop and mobile, published with GitHub Pages
(<https://pazzo123.github.io/oseas26-solar-markets-sales-data/map.html>):

- **One layer at a time, with its own legend**: the three results (underserved market, who should
  serve them, solar penetration) and the six clues the model uses (night lights, population,
  wealth, distance to the grid, travel time, built-up area). Legends are in real units; the
  priority pins show on the underserved and route layers.
- **Who should serve them**: each sector is coloured by who could bring light to its unlit homes:
  grid connections (REG/EDCL), a solar market that already works (solar and PAYGo companies), or a
  solar market that has not arrived (funders). The thresholds are in `config.yml`
  (`webmap.routes`). Every sector card has a section explaining its route.
- **Priority list**: rank sectors by the number of homes without light or by their share (so
  small, remote sectors come up), and keep one route only. The numbered pins follow the list,
  and the link keeps the choice, e.g. `map.html#layer=route&rank=share&route=solar_gap`.
- **Take the data with you**: download every sector in the priority list as a CSV that opens in
  Excel (made in the browser, in list order, with a link back to each sector), or the two EAE
  GeoTIFF layers with their metadata. The licence (CC BY-NC 4.0) is stated next to them.
- **How sure are we**: each sector card says "usual accuracy" or "check on the ground first",
  with the reason (census and model disagree by more than 15 points, or the district is off by 8 or
  more; thresholds in `config.yml`, `webmap.confidence`). Every model share shows its likely range
  in percent, e.g. "20% solar, likely 12%–28%" (± the blocked cross-validation error: 8 points for
  solar, 11 for grid). It also notes that DHS 2025 finds more
  solar than the 2022 census. "Report a correction" opens a GitHub issue form with the sector
  filled in, and a switch draws dashed borders on the sectors to check first.
- **Sector details follow the active layer**: its value, the Rwanda median sector and the share of
  sectors below it, how homes are lit (census 2022), the model estimate, the three SHAP drivers,
  and a table of every layer for that sector (click a row to switch the map to it).
- **Search** any of Rwanda's 416 sectors or 30 districts, or coordinates inside Rwanda.
- **My location** finds the sector you are in and opens its overview (the position stays in the
  browser). It always answers: "Finding your location…" at once, then the sector, or what to do
  when location is blocked, unavailable or the page is not secure (a phone opening
  `http://<computer-IP>:8777` gets no location; use the published https map there).
- **Guided tour** on the first visit (remembered in the browser; the ? button reopens it). Its
  buttons fit phones down to 320 px wide. Two of its steps open a real sector card (the one
  already open, or the top priority sector) to explain it, then the map goes back to how it was.
- **Mobile**: search at the top, a summary chip of the current settings, the location button near
  the top, a full-screen settings screen with a back button, and a bottom sheet for details.
- **Shareable links**: the address remembers the layer and sector, e.g.
  `map.html#layer=underserved&sector=5212`.
- Background: Esri grey or satellite imagery, with place names on top (Esri tiles also load when
  the file is opened locally).

The full ranking is in `reports/top_underserved_sectors.csv` and the per-sector table in
`data/processed/sector_summary.gpkg`. The page layout lives in
`src/solar_markets/webmap_template.html`. After changing the template or the layer wording,
`python -m solar_markets.webmap --from-map` rebuilds `docs/map.html` around the rasters and sector
numbers already in it, so it works without `data/processed`.

Who uses the map, what each of them needs, and the gaps we are closing for them are in
[`docs/user-gaps.md`](docs/user-gaps.md).

### Limitations

What the model cannot see, where it will be wrong and who it might misallocate capital toward
is in [`LIMITATIONS.md`](LIMITATIONS.md). Read it before using the layers for decisions.

### Development setup

**Option A: conda (recommended on Windows)**

```bash
conda env create -f environment.yml
conda activate solar-markets
```

**Option B: pip + venv (Python 3.10+)**

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
pip install -e ".[dev]"
```

Then:

```bash
cp .env.example .env                           # set GEE_PROJECT to your Earth Engine project
python -m solar_markets.check_setup            # libraries, config, folders
python -m solar_markets.check_setup --gee      # also connects to Earth Engine
pytest
```

Download the input data as described in [`data/README.md`](data/README.md). Survey microdata
must never be committed.

### Running the pipeline

Each stage reads `config.yml` and writes one output that the next stage reads:

```bash
python -m solar_markets.labels     # data/processed/labels.gpkg
python -m solar_markets.features   # data/processed/feature_stack.tif, train_table.csv
python -m solar_markets.model      # reports/cv_results.csv, outputs/solar_share_pred.tif
python -m solar_markets.calibrate  # outputs/solar_share_calibrated.tif
python -m solar_markets.export     # outputs/rwa_ogs_*.tif + .yml metadata
python -m solar_markets.webmap     # docs/map.html
python -m solar_markets.webmap --from-map   # rebuild docs/map.html only (template changes, no data)
python -m solar_markets.validate   # reports/dhs_validation.* (needs the DHS 2025 file)
```

### Repository layout

```
config.yml               country, year, resolution, features, model settings
src/solar_markets/       one module per pipeline stage + config and setup check
tests/                   config tests; EAE conformance tests for exported layers
data/                    raw / interim / processed (git-ignored, see data/README.md)
outputs/                 final rasters and metadata
reports/                 cross-validation results and figures
docs/                    interactive map (GitHub Pages)
```
