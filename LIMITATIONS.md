# What this model cannot see

This page covers the two Rwanda layers in `outputs/` (off-grid solar penetration and underserved
solar market, version 0.1, OSEAS 2026 midpoint). The file each number comes from is given in
brackets.

## 1. What it measures, and what it doesn't

- It estimates the share of households whose **main** lighting source is solar (census 2022).
  Households that own a solar lantern but mainly use something else are not counted.
- **The solar labels are themselves partly estimated.** The published sector tables report grid
  and solar together as "electricity". We measure the electrified and unserved shares per
  sector exactly, but split "electrified" into solar and grid with a proxy (electrified minus
  grid-connected, scaled to the published province solar shares). The underserved layer depends
  only on the measured part; the penetration layer depends on the proxy. The census microdata,
  which separates solar per household, removes this step once we have access.
- It says nothing about system size, quality or whether systems still work. A broken solar
  home system still counts as "served" if the household reported it as its main light.
- It covers households only. Productive use (pumps, mills, shops, clinics) is not measured.
- "Underserved" means households with neither grid nor solar as their main light. It does not
  measure ability or willingness to pay.

**Independent check.** The Rwanda DHS 2025 survey (14,427 households, solar asked separately)
agrees with our district pattern: correlation 0.79 for the census solar labels and 0.84 for the
model [`reports/dhs_validation.json`]. Our levels are about 6 points lower, which is three years
of solar growth since the 2022 census (DHS 2025: solar 19.6% nationally).

## 2. Where it will be wrong

- **Inside a sector.** Labels are sector averages (416 sectors). The model never sees a single
  village, so a poor village inside a better-off sector is averaged away, and the 1 km
  pixels can be smoother or more extreme than reality. Pixel predictions re-aggregated to
  sectors differ from the labels by 7.0 pp (solar) and 10.3 pp (grid) on average
  [`reports/reaggregation.csv`].
- **In districts it has not seen.** With whole districts held out, the solar-share error is
  8.0 pp on average (R² 0.21), against 7.6 pp with random splits; for grid share 11.3 pp (R² 0.63)
  [`reports/cv_results.csv`]. Solar use is only weakly predictable from what satellites see, and
  LightGBM does not beat a linear model on it. After calibration, district shares are off by
  4.3 pp on average, worst in **Nyaruguru (−16.9 pp)**, then Bugesera (+9.1 pp), Rulindo (−8.9 pp)
  and Rutsiro (+7.9 pp) [`reports/calibration_districts.csv`]. Predictions there deserve less
  trust; the model pulls unusual districts towards the national pattern.
- **Where nobody lives** the penetration layer is nodata (fewer than 5 people per pixel:
  national parks, lakes).
- **Places unlike any sector:** national parks, wetlands, refugee camps, new settlements built
  after 2022.
- **Places that changed since 2022:** grid extensions and solar campaigns after the census are
  not in the labels.

## 3. Blind spots in the inputs

- Night lights cannot see dim indoor solar lighting. That is why this layer exists, but it also
  means the model leans on proxies (wealth, remoteness, grid distance) rather than direct evidence.
- Inputs come from different years: census 2022, VIIRS 2022, WorldPop 2020, Meta RWI ~2021,
  Gridfinder 2020, travel time 2015.
- The Relative Wealth Index is itself a model estimate, with its own error, and we use the
  nearest point (~2.4 km apart).
- Gridfinder predicts where lines are from night lights and roads. It can miss new or
  low-voltage lines, or include lines that were never built.
- Population grids can misplace rural people, which shifts household counts in the
  underserved layer.
- Calibration currently uses the census national share (13.9%), the same source as the
  labels. It fixes the level of the 1 km map (the shift was small, −0.06 on the logit scale);
  it is not an independent check. GOGLA sales are the planned independent control total.

## 4. Who it might misallocate capital toward or away from

- **Away from** the poorest households in sectors that look served on average.
- **Toward** areas where solar was sold but systems have since failed or been repossessed:
  they look served, so money may skip them when it should not, or flow to the wrong
  neighbours.
- **Away from or toward** areas the grid is about to reach. The model cannot see grid plans,
  so it may prioritise solar where the grid arrives next year, or the reverse.
- **Toward dense and large areas.** The underserved layer counts households, so populous
  pixels and large sectors (e.g. Rwimiyaga and Karangazi in Nyagatare) rank above remote ones
  with a higher unserved *share* but fewer people.
- **Toward or away from high-solar districts** like Nyaruguru, where the model under-predicts
  solar (−16.9 pp) and therefore over-states the unserved gap.
- **Away from** groups the census or population grids undercount: informal settlements,
  mobile and refugee populations.
- **Through the "who should serve them" routes.** The map calls a sector a grid job when at least
  half its homes use the grid or people live within 1 km of a line on average; otherwise its
  solar market counts as working when solar reaches the national share (13.9%). These are rules
  of thumb on sector averages. They rest on the estimated solar/grid split and on Gridfinder lines,
  which can be missing or wrong. They also ignore the National Electrification Plan, so a sector
  marked "solar not yet arrived" may already be due for the grid. Poor villages inside a "grid"
  sector can still be off the grid.

## 5. How to use it responsibly

- Use it to **shortlist** sectors for field verification (`reports/top_underserved_sectors.csv`),
  not to make final funding decisions.
- Combine it with local knowledge: REG/EDCL grid plans, company coverage, district officials.
- Prefer areas where the model and the census agree. Check each priority zone's drivers in the
  web map's details card (click the sector) before acting on it.
- Commercial use is restricted: the layers are CC BY-NC 4.0 because the wealth index input is.
- Re-run with newer survey data when available (EICV7, the next DHS, MTF), and with GOGLA
  calibration.
