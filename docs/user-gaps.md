# Who the map is for, and where it let them down

This page is for the team. It says who uses the map, what each of them needs from it, where
the map fell short (October 2026), and which branch fills each gap. Read it before reviewing
the PRs it lists.

## How the map works

`python -m solar_markets.webmap` turns the pipeline outputs into one page, `docs/map.html`:

1. The model's 1 km rasters (solar share, grid share) and the six clue bands are coloured into
   images, one per layer.
2. Every sector (416) gets its numbers: census shares, model estimates, households without light,
   clue values and the three SHAP drivers.
3. Everything is embedded as JSON in `webmap_template.html`, which draws it with Leaflet: one
   layer at a time with its legend, a details card per sector, the top 10 list, search, "My
   location" and a guided tour.

`python -m solar_markets.webmap --from-map` re-renders the page around the data already in it, so
template changes can be built and tested without `data/processed`.

## Who uses it, and what they need

| User | What they decide | What they need from the map |
| --- | --- | --- |
| Funders and results-based financing (RBF) managers | Where grants and subsidies go | Places the market will not reach on its own, a list they can take away, and how far to trust each number |
| Solar and PAYGo companies | Where to sell next | Where unlit homes are, whether solar already sells there, the data in their own tools, and the licence terms |
| REG / EDCL and district planners | Grid or off-grid for each area | Which unlit homes sit close to the grid |
| Energy Access Explorer (EAE) analysts | How to combine our layers with theirs | The GeoTIFF layers and their metadata |
| Field teams | Which sectors to visit, and what to report back | A shortlist, their own location, and a way to send corrections |

## The gaps, and how each is filled

### 0. "My location" gave no answer (bug)

**What users hit.** Clicking the location button showed nothing. The browser's timeout only starts
after permission is given, so a missed or blocked prompt left the button spinning in silence, and
the spinner (a crosshair turning in place) looked still. A phone opening the map from a laptop at
`http://<IP>:8777` can never get a location, because the page is not secure.

**How it is filled** (`fix/webmap-location`):

- "Finding your location…" shows at once, and the button shows a turning arc.
- A blocked permission, an insecure page and an unavailable position each get a message that
  says what to do. The message stays until it is closed.
- A 20 s watchdog answers when the browser never does.

### 1. Who should serve them

**What users hit.** The top 10 mixed jobs for the grid company with jobs for solar companies:

- Nyagatare (#4) is 55% grid-connected and 0.8 km from a line.
- Ruheru (#15) already lights 74% of homes with solar.
- Remote sectors where solar never arrived (Sovu, Kavumu and Rusebeya: 59% unlit, about 7% solar,
  6–7 km from the grid) ranked 39th–119th.

Telling "the market failed to arrive" apart from "the market quietly succeeded" is the core of
the challenge brief, and the map did not show it.

**How it is filled** (`feat/webmap-delivery-route`). Every sector gets a delivery route:

| Route | Rule (`config.yml`, `webmap.routes`) | Who could act | Sectors | Homes without light |
| --- | --- | --- | --- | --- |
| Grid connections | at least 50% of homes on the grid, or people live within 1 km of a line on average | REG / EDCL | 149 | 401,691 |
| Solar market working | otherwise, solar lights at least the national share of homes (13.9%) | Solar and PAYGo companies | 195 | 678,621 |
| Solar market not yet arrived | everything else: little grid, little solar | Funders: RBF, grants, new distributors | 72 | 253,156 |

On the map:

- the **Who should serve them** layer colours each sector by its route;
- the legend gives the homes and sectors on each route;
- every sector card has a "Who should serve these homes" section with the numbers behind its
  route.

The census shares lead (the solar/grid split is estimated, see `LIMITATIONS.md`), and the model
fills in where the census has none. It is a rule of thumb: Gridfinder misses some lines, and the
National Electrification Plan's grid extensions are not in the data.

**Check it.** Open `map.html#layer=route`, then click Nyagatare (grid), Rwimiyaga (solar
working) and Ndaro (not yet arrived).

### 2. Fair ranking

**What users hit.** The only ranking is by number of homes without light, so large sectors lead.
`LIMITATIONS.md` §4 warns about this. A funder looking for places where most homes are dark had
no way to find them.

**How it is filled** (`feat/webmap-fair-ranking`). The priority list in the panel gets two
controls:

- **Rank by:** *Most homes* (the number of homes without light, as before) or *Highest share*
  (the share of a sector's homes without light). By share, Sovu, Kavumu and Rusebeya (59% of
  homes dark) lead instead of ranking 39th–119th.
- **Who should serve them:** all routes, or one route only. A funder can list the 72 sectors where
  the solar market has not arrived. On the route layer, the other sectors fade.

The numbered pins follow the list and show on both the underserved and the route layers. Each
sector card gives both ranks, for example "#139 by number of homes, #10 by share (57%)". The link
keeps the choice, for example `map.html#layer=route&rank=share&route=solar_gap`.
`reports/top_underserved_sectors.csv` gains `unserved_share` and `rank_share` on the next full run.

**Check it.** Open the link above. Sovu, Kavumu and Rusebeya lead the list.

### 3. Download the data

**What users hit.** Nobody can take the data away from the map. The shortlist and the two EAE
GeoTIFF layers exist only on GitHub, and the CC BY-NC licence is not shown where a company would
see it.

**How it is filled** (`feat/webmap-downloads`). A "Take the data with you" section in the panel
offers:

- **Download N sectors (CSV).** Every sector in the priority list, in its order (not only the top
  10). Each row has its route, who could act, both ranks, households, census and model shares,
  the six clues, the model's drivers and a link back to the sector on the map. The file opens in
  Excel and is named after the choice, e.g. `rwanda_priority_sectors_by_share_solar_gap.csv`.
  It is made in the browser from the data already on the page, so it always matches what is shown.
- **The two EAE layers** (GeoTIFF, 0–1, ~1 km), with size and metadata links on GitHub `main`.
- **The licence, in plain words:** CC BY-NC 4.0, free to use with credit but not for commercial
  use, because the Meta wealth index it is built on is non-commercial. Companies are asked to
  check before using it to plan sales.

**Check it.** Choose *Highest share* and *Solar market not yet arrived*, then press "Download 72
sectors (CSV)". The file has 72 rows in the same order as the list.

### 4. How sure are we

**What users hit.** Every sector card says "about 8 points off", even where:

- the census and the model disagree on solar by more than 15 points (46 sectors; Ruheru: census
  74%, model 17%);
- the whole district is off (Nyaruguru, −16.9 points).

The data is from 2022, while the DHS 2025 survey finds solar in 19.6% of homes against 13.9% in
the census. Field teams have no way to report what they find.

**How it is filled** (`feat/webmap-confidence`). Every sector card has a "How sure are we"
section near the top:

- **Usual accuracy**, or **Check on the ground first** with the reasons in plain words. A sector
  is flagged when the census and the model disagree on its solar share by more than 15 points,
  or when the model is off by 8 points or more in its district (`reports/calibration_districts.csv`).
  That flags 75 sectors: 46 where census and model disagree, and 46 in Nyaruguru, Bugesera and
  Rulindo. Thresholds are in `config.yml` (`webmap.confidence`).
- **Accuracy in percent:** every model share comes with its likely range, the estimate ± the
  model's average error in a district it has not seen (8 percentage points for solar, 11 for grid,
  from `reports/cv_results.csv`). So "20% solar" reads "likely 12%–28%". The ranges also appear
  in the card's model estimate, on the solar penetration card, in "About this map" and in the
  CSV (`model_solar_likely_range`, `model_grid_likely_range`). It is not shown as one accuracy
  score: an 8-point error on a 14% share is more than half the value, so a single "92% accurate"
  would overstate the map.
- **Since 2022:** the DHS 2025 survey finds solar in 20% of homes nationally against 14% in the
  census. The note also appears on the solar penetration card and in "About this map".
- **Report a correction** opens a GitHub issue form (`.github/ISSUE_TEMPLATE/field_check.yml`)
  with the sector, layer and map link already filled in. The issue is public and needs a GitHub
  account, and the form asks people to leave out names and phone numbers.

The "Sectors to check first" switch under "On the map" draws dashed borders on the flagged
sectors. The downloaded CSV gains `check_first` and `check_notes` columns.

**Before merging:** Issues are switched off on the fork (`PAZZO123/oseas26-solar-markets-sales-data`),
so the correction link only works once the repository owner turns them on (Settings > General >
Features > Issues). Until then, set `webmap.feedback_url` to `null` to hide the button.

**Check it.** Open Ruheru (`map.html#layer=penetration&sector=2312`): census 74% solar, model 17%,
and Nyaruguru is 17 points off. Then turn on "Sectors to check first".

## Still out of reach

- **Which companies already sell where.** GOGLA keeps company-level data private (the
  three-data-point rule), so the map shows where solar is used, not who sells it.
- **Grid plans.** The National Electrification Plan's grid extensions are not public as data.
- **Ability to pay** beyond the Relative Wealth Index, and productive use (pumps, mills, shops).
- **A Kinyarwanda version** of the page.
- **Offline use.** The page loads Leaflet and the background map from the internet.

## Testing locally

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m solar_markets.webmap --from-map
.venv/bin/python -m http.server 8777 --directory docs
```

Then open <http://localhost:8777/map.html>. On Windows use `.venv/Scripts/python`.
