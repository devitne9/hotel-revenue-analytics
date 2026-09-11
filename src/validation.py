"""Fail the portfolio pipeline if four-room accounting or calibration drifts."""

import numpy as np
import pandas as pd

from src.config import END_DATE, ROOM_COUNTS, ROOMS, START_DATE
from src.kpi_analysis import aggregate_performance


def validate_guesthouse(bookings: pd.DataFrame, nightly: pd.DataFrame,
                       daily: pd.DataFrame, annual: pd.DataFrame) -> dict:
    """Validate the canonical synthetic dataset, including each full year.

    Revenue/occupancy ranges are simulation acceptance checks, not accounting
    rules for arbitrary real-world exports. All calendar days remain available.
    """
    calendar = pd.date_range(START_DATE, END_DATE, inclusive="left")
    expected_capacity = pd.Series(4, index=calendar).groupby(calendar.year).sum()
    completed = bookings["booking_status"].eq("Completed")
    expected_revenue = (bookings["room_rate"] * bookings["nights"] * completed).round(2)
    nightly_by_booking = nightly.groupby("booking_id")["nightly_revenue"].sum().reindex(bookings["booking_id"], fill_value=0)
    occupied = nightly.groupby("stay_date")["room_id"].nunique()
    daily_capacity = daily.groupby("stay_date")["available_room_nights"].sum().reindex(calendar)
    seasonal = aggregate_performance(daily, ["year", "season"])
    checks = {
        "exactly_four_physical_rooms": len(ROOMS) == 4 and sum(ROOM_COUNTS.values()) == 4 and set(bookings["room_id"]) == set(ROOMS),
        "valid_room_types": bool(bookings["room_id"].map(ROOMS).eq(bookings["room_type"]).all()),
        "maximum_four_occupied_rooms_per_night": bool(occupied.le(4).all() and nightly.groupby("stay_date").size().le(4).all()),
        "no_overlapping_completed_bookings": not bool(nightly.duplicated(["room_id", "stay_date"]).any()),
        "four_available_room_nights_every_day": bool(daily_capacity.eq(4).all() and len(daily) == len(calendar) * len(ROOM_COUNTS)),
        "correct_annual_capacity": bool(annual.index.equals(expected_capacity.index) and np.array_equal(annual["available_room_nights"], expected_capacity)),
        "annual_revenue_in_target_range": bool(annual["revenue"].between(25_000, 35_000).all()),
        "annual_occupancy_in_target_range": bool(annual["occupancy_rate"].between(.40, .60).all()),
        "nightly_rates_in_guesthouse_range": bool(bookings["room_rate"].between(30, 65).all()),
        "revenue_equals_rate_times_completed_nights": bool(np.allclose(bookings["revenue"], expected_revenue, rtol=0, atol=.005)),
        "nightly_revenue_reconciles_by_booking": bool(np.allclose(nightly_by_booking, bookings["revenue"], rtol=0, atol=.005)),
        "occupied_nights_reconcile": len(nightly) == int(bookings.loc[completed, "nights"].sum()) == int(annual["room_nights"].sum()),
        "annual_revenue_reconciles": bool(np.isclose(annual["revenue"].sum(), bookings["revenue"].sum(), rtol=0, atol=.005)),
        "adr_reconciles": bool(np.allclose(annual["adr"], annual["revenue"] / annual["room_nights"])),
        "occupancy_reconciles": bool(np.allclose(annual["occupancy_rate"], annual["room_nights"] / expected_capacity)),
        "seasonal_pattern_visible_each_year": all(
            seasonal.loc[(year, "High"), "occupancy_rate"] > seasonal.loc[(year, "Shoulder"), "occupancy_rate"] > seasonal.loc[(year, "Low"), "occupancy_rate"]
            and seasonal.loc[(year, "High"), "occupancy_rate"] - seasonal.loc[(year, "Low"), "occupancy_rate"] >= .25
            for year in annual.index
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError("Guesthouse validation failed: " + ", ".join(failed))
    return {
        "all_checks_passed": True,
        "physical_rooms": len(ROOMS),
        "maximum_occupied_rooms_per_night": int(occupied.max()),
        "checks": checks,
    }
