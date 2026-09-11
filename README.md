# Guesthouse Revenue & Booking Analytics

**A reproducible Python portfolio project exploring revenue, occupancy, seasonality and pricing for a four-room independent guesthouse using completely synthetic data.**

> This project is a portfolio reconstruction inspired by real hospitality analytics work. All booking records and financial values are synthetic and do not represent the actual guesthouse's confidential data.

![Monthly synthetic guesthouse room revenue](figures/monthly_revenue.png)

## Overview

This project reconstructs the type of booking and revenue analysis I performed as a Data Specialist / Data and Business Analyst in a small hospitality business. The original business data and analytical code are unavailable. The code, dataset and findings here were created for this portfolio; they do not reproduce historical company results or claim measured business impact.

The workflow turns a deliberately imperfect synthetic booking export into validated records, nightly revenue, interpretable KPIs and practical pricing hypotheses. It demonstrates Python, pandas, NumPy, data cleaning, exploratory analysis and communication of business findings.

**Start with:** [the executed notebook](notebooks/hotel_revenue_analysis.ipynb), [key insights](#key-insights), or [the analysis entry point](src/run_analysis.py).

## Business Questions

- When is realized demand strongest, and how consistent is the seasonal pattern?
- Which room types generate the most revenue, and how does their inventory affect that comparison?
- How do ADR and occupancy change across months and seasons?
- How do booking lead times, cancellations and channels vary?
- Which periods warrant testing higher rates or targeted promotions?

## Dataset

The reporting window covers **1 January 2023 through 31 December 2025**. The simulated property is **a four-room independent guesthouse**, with one Standard Double, one Twin Room, one Family Room and one Superior Double. Each physical room contributes one available room night per calendar day: **1,460 per ordinary year**, **1,464 in leap year 2024**, and **4,384 across all three years** (1,096 days × 4 rooms). All financial values are synthetic **EUR**.

The synthetic generator is calibrated to the approximate operating scale of a small four-room guesthouse: roughly **€25,000–€35,000 annual accommodation revenue**, centered near **€30,000**, and **40–60% annual occupancy**. These are simulation targets, not the actual business's confidential figures. Annual revenue is never assigned or rescaled; it is the sum of rates charged for generated completed stay nights.

| Field | Meaning |
|:--|:--|
| `booking_id` | Artificial `SYN-B…` identifier; one booking reserves one room |
| `booking_date` | Creation date; may precede 2023 for early arrivals |
| `check_in`, `check_out` | Arrival and exclusive departure dates |
| `room_id`, `room_type` | Artificial inventory identifier and Standard Double / Twin Room / Family Room / Superior Double category |
| `guests` | Party size within room capacity; some values deliberately missing |
| `nights` | Length of stay, recomputed from departure minus arrival |
| `room_rate` | Fixed nightly room price for the entire stay, in EUR |
| `revenue` | Rate × nights for completed stays; zero for cancellations |
| `booking_channel` | Direct, Online travel agency or Travel agent; generic labels only |
| `booking_status` | Completed or Cancelled |
| `lead_time` | Days between booking creation and arrival |
| `month`, `season`, `weekday`, `is_weekend` | Arrival-based fields added during cleaning |

### How the simulation works

[The generator](src/generate_synthetic_data.py) uses NumPy's random generator with **seed 42**. Each available room receives a daily chance of a potential arrival, with stronger summer and Friday/Saturday demand, lower winter demand, and a high-season preference for the Family Room. Completed stays block that room until checkout, preventing overbooking.

Stay lengths use a bounded Poisson-based distribution; lead times use a bounded lognormal distribution. Base rates are €35 / €36 / €40 / €42 for Standard Double / Twin Room / Family Room / Superior Double. Low / shoulder / high season multipliers are 0.92 / 1.00 / 1.25, with an 8% arrival-weekend premium, 2% annual base-rate increases, modest advance-booking and low-season last-minute discounts, and small random variation. Final nightly quotes stay within €30–€65. Each booking holds its arrival-based nightly quote throughout the stay. Demand varies by month, with a small weekend increase; arrival draws, stay lengths and cancellations produce natural year-to-year differences. Generic channels have different cancellation probabilities. Cancelled bookings are assumed to cancel before arrival and never block inventory; fees are zero.

An independent **seed 43** adds about 1% duplicate rows, 1% missing guest counts, inconsistent category casing/whitespace, and incorrect derived values. The raw file intentionally contains these issues. Cleaning produces [a separate validated dataset](data/cleaned_bookings.csv) and [an audit report](reports/data_quality.json). No downloaded or private dataset is used.

### Assumptions and limits

- Each booking is one room; guest counts are not used to estimate occupancy. Missing guest counts remain unknown.
- All stays lie within the reporting window. Late-December stays are shortened at the end of 2025, creating a small boundary effect; the simulation starts without carry-in stays.
- Room revenue excludes taxes, meals, commissions, operating costs, refunds and cancellation fees. It is **not profit**.
- The guesthouse has no closures, maintenance blocks, no-shows, group bookings or overbooking. Cancellation timestamps and rebooking behavior are not modeled.
- Sold room nights measure **realized demand**. Search traffic, rejected requests and unconstrained demand are unavailable.
- Demand and rates share programmed seasonal drivers. Observed correlations demonstrate analytical techniques; they cannot establish price elasticity or an optimal price.
- Friday and Saturday **stay nights** count as weekends. Demand seasons are **Low: January–March and November–December; Shoulder: April–May and October; High: June–September**.

## KPIs

| KPI | Definition and denominator |
|:--|:--|
| Room revenue | Sum of fixed nightly rates across completed stay nights |
| ADR | Completed room revenue ÷ completed room nights; never an unweighted average of booking rates |
| Occupancy | Completed room nights ÷ (4 × calendar days) for the property; ÷ (1 × calendar days) for each room type |
| RevPAR | Room revenue ÷ available room nights; combines occupancy and ADR |
| Booking volume | Unique bookings, with completed and cancelled counts shown separately |
| Room nights | Sum of nights for completed bookings |
| Average length of stay | Completed room nights ÷ completed bookings |
| Cancellation rate | Cancelled unique bookings ÷ all unique bookings |
| Average lead time | Mean days from creation to arrival for completed bookings |

**Date alignment matters:** revenue, ADR and occupancy use the actual **stay date**. Monthly and annual booking counts use **check-in month/year** and include cancelled bookings separately. A stay from 31 January to 2 February contributes one room night to January and one to February. Annual average stay length uses the full stays of completed bookings arriving that year, even if they cross New Year. Booking-creation-month counts are provided in a separate report; boundary months are incomplete because the dataset is selected by stay dates.

## Analysis

1. **Generate:** simulate three years of bookings with physical room capacity and controlled export issues.
2. **Clean:** normalize categories, remove exact duplicates, validate identifiers/dates/rates/guest counts, and rebuild nights, revenue and lead time. Conflicting IDs or invalid source fields raise errors instead of silently disappearing.
3. **Reshape:** expand completed bookings into room nights and join a full daily inventory calendar, including zero-sale dates.
4. **Analyze:** summarize monthly KPIs, room-type revenue share and RevPAR, calendar-month seasonality, weekdays/weekends, channel cancellation rates, and lead-time/price relationships.
5. **Communicate:** save tidy CSV tables, ten charts and dataset-derived findings. Recommendations are hypotheses for small, monitored tests; no automated pricing model is used.

## Key Insights

This section is refreshed automatically by `python -m src.run_analysis` from the validated data. These findings describe the simulation, not historical results from the real guesthouse.

<!-- RESULTS:START -->

Results for **1 January 2023–31 December 2025**, generated with seed `42`.

| Year | Revenue (EUR) | Occupied room nights | Available room nights | Occupancy | ADR (EUR) | All bookings | Completed | Avg. stay (nights) | Cancellation rate |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 2023 | €29,476.66 | 674 | 1,460 | 46.2% | €43.73 | 264 | 227 | 2.97 | 14.0% |
| 2024 | €30,262.17 | 679 | 1,464 | 46.4% | €44.57 | 274 | 231 | 2.94 | 15.7% |
| 2025 | €31,444.29 | 691 | 1,460 | 47.3% | €45.51 | 254 | 221 | 3.12 | 13.0% |

Revenue and occupied (booked) room nights use stay year and exclude cancellations. Booking counts, average full stay length and cancellation rates use check-in year. 2024 includes leap day.

All 16 validation checks passed; maximum simultaneously occupied rooms: 4. No overlapping completed stays. See [annual results](reports/annual_performance.csv) and [validation checks](reports/validation_checks.json).

| Metric | Result |
|:--|--:|
| Room revenue, all three years | €91,183.12 |
| Unique bookings / completed / cancelled | 792 / 679 / 113 |
| Completed room nights | 2,044 |
| Available room nights | 4,384 |
| ADR | €44.61 |
| Occupancy | 46.6% |
| RevPAR | €20.80 |
| Average completed stay | 3.01 nights |
| Cancellation rate | 14.3% |
| Average lead time, completed bookings | 28.8 days |

- 2025-07 generated the most monthly room revenue (€5,360.52). Revenue is allocated by stay night, including stays crossing month-end.

- High season had the highest occupancy (77.7%) at €49.35 ADR; low season had the lowest (25.4%) at €36.80 ADR.

- The Superior Double generated 27.1% of room revenue (€24,680.15). Compare its 46.3% occupancy and €22.52 RevPAR alongside revenue share; each category contains exactly one physical room.

- 14.3% of unique bookings were cancelled. Completed stays averaged 3.01 nights and were booked 28.8 days ahead.

- Pricing hypothesis: with high season occupancy at 77.7%, test a €2–€3 nightly increase on selected busy dates, keeping trial quotes within the illustrative €30–€65 range, and monitor enquiries, cancellations and RevPAR. The data does not estimate an optimal price or uplift.

- Promotion hypothesis: low season occupancy of 25.4% suggests testing a modest multi-night offer on specific unsold dates, keeping quoted rates at least €30. Evaluate incremental room nights and net revenue after discount and channel costs, which are not modeled here.

- With four rooms, selling one extra room changes daily occupancy by 25 percentage points. Review comparable dates over several weeks and include booking counts before changing prices; one room type is only one physical room.

- Monthly occupancy and ADR have a Pearson correlation of 0.95. Both share an explicitly programmed seasonal pattern; this is descriptive and cannot show that raising prices causes stronger demand.

Cleaning audit: 799 raw rows → 792 unique bookings; 7 duplicate rows removed and 7 missing guest counts retained as unknown. See [the full quality report](reports/data_quality.json) for repaired derived values.

<!-- RESULTS:END -->

## Visualisations

![Monthly occupancy](figures/monthly_occupancy.png)
![Room revenue by type](figures/room_type_revenue.png)
![Seasonal demand](figures/seasonal_demand.png)
![Monthly occupancy versus ADR](figures/occupancy_vs_adr.png)

The [figures folder](figures/) also contains monthly ADR, monthly booking volume, room-type ADR, booking lead-time distribution and lead time versus ADR. Every chart carries a synthetic-data label and explicit units.

## Technologies

- **Python**, **pandas**, **NumPy**: simulation, validation, aggregation and descriptive analysis.
- **matplotlib**: publication-ready PNG charts.
- **Jupyter notebook**, **nbformat**, **nbclient**, **ipykernel**: an executed, reproducible walkthrough.
- **unittest**: checks for accounting reconciliation, date boundaries, capacity, cleaning and reproducibility.

## Repository Structure

```text
hotel-revenue-analytics/
├── README.md
├── requirements.txt
├── requirements-notebook.txt
├── .gitignore
├── data/
│   ├── synthetic_bookings.csv       # Raw synthetic export with deliberate issues
│   └── cleaned_bookings.csv         # Unique, validated synthetic bookings
├── src/
│   ├── config.py                    # Reporting window, seed and fictional inventory
│   ├── generate_synthetic_data.py
│   ├── clean_data.py
│   ├── kpi_analysis.py
│   ├── seasonality_analysis.py
│   ├── pricing_analysis.py
│   ├── validation.py                # Four-room capacity, accounting and scale checks
│   ├── visualizations.py
│   └── run_analysis.py              # Full reproducible workflow
├── notebooks/
│   └── hotel_revenue_analysis.ipynb # Executed narrative and outputs
├── scripts/
│   └── execute_notebook.py
├── reports/                        # CSV tables, KPIs, cleaning audit and findings
├── figures/                        # Ten generated PNG charts
└── tests/
    └── test_analysis.py
```

## Running the Project

Use **Python 3.13** (the tested environment). From a terminal:

```bash
git clone https://github.com/devitne9/hotel-revenue-analytics.git
cd hotel-revenue-analytics
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.run_analysis
python -m unittest discover -s tests -v
```

The pipeline rebuilds the synthetic CSVs, tables (including annual sanity metrics), all ten chart images and the generated results section of this README. It fails if annual scale, four-room capacity, nightly accounting or seasonal validation checks fail; results are saved to `reports/validation_checks.json`. It uses project-relative paths and never reads external business data. Run module commands from the repository root. Direct dependencies are pinned to the versions used to generate the committed outputs.

To re-execute the notebook and save fresh outputs:

```bash
python -m pip install -r requirements-notebook.txt
python scripts/execute_notebook.py
```

Open the notebook in GitHub to read its saved results, or select the `.venv` Python interpreter in a local notebook editor. The notebook works when started from the repository root or the `notebooks` directory. Re-executing it refreshes the charts; the full pipeline also refreshes CSV/JSON reports and README findings.

## Privacy

> This project is a portfolio reconstruction inspired by real hospitality analytics work. All booking records and financial values are synthetic and do not represent the actual guesthouse's confidential data.

All identifiers are artificial and use a `SYN-` prefix. The project has no customer names, emails, phone numbers, addresses, real property identifiers, credentials, API keys, private integration code or original business records. All simulation parameters are illustrative assumptions.
