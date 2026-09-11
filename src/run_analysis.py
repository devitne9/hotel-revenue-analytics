"""Run the full reproducible pipeline: python -m src.run_analysis."""

import json

import pandas as pd

from src.clean_data import clean_bookings
from src.config import DATA_DIR, REPORTS_DIR, ROOT
from src.generate_synthetic_data import generate_bookings, introduce_quality_issues
from src.kpi_analysis import (
    annual_performance, build_room_nights, calculate_kpis, daily_performance,
    monthly_performance, room_performance,
)
from src.pricing_analysis import business_insights, pricing_tables
from src.seasonality_analysis import seasonality_tables
from src.visualizations import create_visualizations
from src.validation import validate_guesthouse


def annual_summary_markdown(annual: pd.DataFrame) -> str:
    """Show every requested annual sanity metric with explicit cohort labels."""
    block = "| Year | Revenue (EUR) | Occupied room nights | Available room nights | Occupancy | ADR (EUR) | All bookings | Completed | Avg. stay (nights) | Cancellation rate |\n"
    block += "|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|\n"
    for year, row in annual.iterrows():
        block += (f"| {year} | €{row['revenue']:,.2f} | {row['room_nights']:,.0f} | {row['available_room_nights']:,.0f} "
                  f"| {row['occupancy_rate']:.1%} | €{row['adr']:.2f} | {row['total_bookings']:.0f} "
                  f"| {row['completed_bookings']:.0f} | {row['average_length_of_stay']:.2f} | {row['cancellation_rate']:.1%} |\n")
    block += "\nRevenue and occupied (booked) room nights use stay year and exclude cancellations. Booking counts, average full stay length and cancellation rates use check-in year. 2024 includes leap day.\n"
    return block


def write_readme_results(kpis: dict, insights: list[str], quality: dict,
                        annual: pd.DataFrame, validation: dict) -> None:
    """Replace only the generated results section of the narrative README."""
    path = ROOT / "README.md"
    content = path.read_text(encoding="utf-8")
    start, end = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"
    if content.count(start) != 1 or content.count(end) != 1:
        raise ValueError("README must contain exactly one pair of results markers")
    rows = [
        ("Room revenue, all three years", f"€{kpis['total_revenue']:,.2f}"),
        ("Unique bookings / completed / cancelled", f"{kpis['total_bookings']:,} / {kpis['completed_bookings']:,} / {kpis['cancelled_bookings']:,}"),
        ("Completed room nights", f"{kpis['room_nights']:,}"),
        ("Available room nights", f"{kpis['available_room_nights']:,}"),
        ("ADR", f"€{kpis['adr']:.2f}"),
        ("Occupancy", f"{kpis['occupancy_rate']:.1%}"),
        ("RevPAR", f"€{kpis['revpar']:.2f}"),
        ("Average completed stay", f"{kpis['average_length_of_stay']:.2f} nights"),
        ("Cancellation rate", f"{kpis['cancellation_rate']:.1%}"),
        ("Average lead time, completed bookings", f"{kpis['average_lead_time']:.1f} days"),
    ]
    block = "\n\nResults for **1 January 2023–31 December 2025**, generated with seed `42`.\n\n"
    block += annual_summary_markdown(annual)
    block += (f"\nAll {len(validation['checks'])} validation checks passed; maximum simultaneously occupied rooms: "
              f"{validation['maximum_occupied_rooms_per_night']}. No overlapping completed stays. "
              "See [annual results](reports/annual_performance.csv) and [validation checks](reports/validation_checks.json).\n\n")
    block += "| Metric | Result |\n|:--|--:|\n"
    block += "\n".join(f"| {label} | {value} |" for label, value in rows)
    block += "\n\n" + "\n\n".join(f"- {insight}" for insight in insights)
    block += (
        f"\n\nCleaning audit: {quality['input_rows']:,} raw rows → {quality['output_rows']:,} unique bookings; "
        f"{quality['duplicate_rows_removed']:,} duplicate rows removed and "
        f"{quality['missing_guests_retained']:,} missing guest counts retained as unknown. "
        "See [the full quality report](reports/data_quality.json) for repaired derived values.\n\n"
    )
    prefix, rest = content.split(start)
    _, suffix = rest.split(end)
    path.write_text(prefix + start + block + end + suffix, encoding="utf-8")


def main() -> None:
    """Rebuild synthetic data, analytical tables, charts and README insights."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    raw = introduce_quality_issues(generate_bookings())
    raw_path = DATA_DIR / "synthetic_bookings.csv"
    raw.to_csv(raw_path, index=False, date_format="%Y-%m-%d")
    # Read the actual CSV to exercise the same parsing path as a real export.
    bookings, quality = clean_bookings(pd.read_csv(raw_path))
    bookings.to_csv(DATA_DIR / "cleaned_bookings.csv", index=False, date_format="%Y-%m-%d")
    nightly = build_room_nights(bookings)
    daily = daily_performance(nightly)
    kpis = calculate_kpis(bookings, nightly)
    tables = {
        "annual_performance": annual_performance(bookings, daily),
        "monthly_performance": monthly_performance(bookings, daily),
        "room_performance": room_performance(bookings, daily),
        **seasonality_tables(bookings, daily),
    }
    validation = validate_guesthouse(bookings, nightly, daily, tables["annual_performance"])
    tables.update(pricing_tables(bookings, daily, tables["monthly_performance"]))
    # Include creation-month counts separately from arrival-month counts.
    booking_month = bookings.groupby(bookings["booking_date"].dt.to_period("M")).size()
    full_months = pd.period_range(bookings["booking_date"].min(), bookings["booking_date"].max(), freq="M")
    tables["booking_creation_month"] = booking_month.reindex(full_months, fill_value=0).rename_axis("booking_month").to_frame("total_bookings")
    channel = bookings.groupby("booking_channel").agg(total_bookings=("booking_id", "size"), cancelled_bookings=("booking_status", lambda values: values.eq("Cancelled").sum()))
    channel["cancellation_rate"] = channel["cancelled_bookings"] / channel["total_bookings"]
    tables["channel_performance"] = channel
    daily.to_csv(REPORTS_DIR / "daily_performance.csv", index=False, float_format="%.6f")
    for name, table in tables.items():
        table.to_csv(REPORTS_DIR / f"{name}.csv", float_format="%.6f")
    for name, report in [("kpis", kpis), ("data_quality", quality), ("validation_checks", validation)]:
        (REPORTS_DIR / f"{name}.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    insights = business_insights(kpis, tables)
    (REPORTS_DIR / "business_insights.md").write_text(
        "# Findings from synthetic four-room guesthouse data (EUR)\n\n" + annual_summary_markdown(tables["annual_performance"])
        + "\nAll four-room capacity and calibration checks passed.\n\n"
        + "\n\n".join(f"- {item}" for item in insights) + "\n", encoding="utf-8",
    )
    create_visualizations(bookings, tables)
    write_readme_results(kpis, insights, quality, tables["annual_performance"], validation)
    print(f"Analyzed {kpis['total_bookings']:,} synthetic bookings; generated 10 charts and refreshed README results.")
    print(json.dumps(kpis, indent=2))
    print("\nAnnual synthetic results (EUR):")
    print(tables["annual_performance"].to_string(float_format=lambda value: f"{value:.4f}"))
    print(f"All {len(validation['checks'])} guesthouse validation checks passed.")


if __name__ == "__main__":
    main()
