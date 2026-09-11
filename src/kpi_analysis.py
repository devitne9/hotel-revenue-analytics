"""Calculate revenue and occupancy on the nights actually occupied."""

import pandas as pd

from src.config import END_DATE, ROOM_COUNTS, ROOMS, SEASON_BY_MONTH, START_DATE


def build_room_nights(bookings: pd.DataFrame) -> pd.DataFrame:
    """Expand completed stays into one row per occupied room-night.

    Checkout is exclusive. A stay crossing month-end contributes revenue
    and occupancy to both months. Each booking has one fixed nightly rate.
    """
    completed = bookings.loc[bookings["booking_status"].eq("Completed")].copy()
    completed["stay_date"] = [
        pd.date_range(start, end, inclusive="left")
        for start, end in zip(completed["check_in"], completed["check_out"])
    ]
    nightly = completed.explode("stay_date").rename(columns={"room_rate": "nightly_revenue"})
    nightly["stay_date"] = pd.to_datetime(nightly["stay_date"])
    nightly = nightly[["booking_id", "room_id", "room_type", "stay_date", "nightly_revenue"]].reset_index(drop=True)
    if nightly.duplicated(["room_id", "stay_date"]).any():
        raise ValueError("Overlapping completed stays exceed individual room capacity")
    return nightly


def daily_performance(nightly: pd.DataFrame) -> pd.DataFrame:
    """Build a complete room-type/calendar grid, including unsold nights."""
    calendar = pd.MultiIndex.from_product(
        [pd.date_range(START_DATE, END_DATE, inclusive="left"), ROOM_COUNTS],
        names=["stay_date", "room_type"],
    )
    daily = nightly.groupby(["stay_date", "room_type"]).agg(
        revenue=("nightly_revenue", "sum"), room_nights=("booking_id", "size"),
    ).reindex(calendar, fill_value=0).reset_index()
    daily["available_room_nights"] = daily["room_type"].map(ROOM_COUNTS)
    if (daily["room_nights"] > daily["available_room_nights"]).any():
        raise ValueError("Occupied room nights exceed available capacity")
    daily["month"] = daily["stay_date"].dt.to_period("M").astype(str)
    daily["month_number"] = daily["stay_date"].dt.month
    daily["season"] = daily["month_number"].map(SEASON_BY_MONTH)
    daily["day_type"] = daily["stay_date"].dt.dayofweek.isin([4, 5]).map({True: "Weekend", False: "Weekday"})
    return daily


def aggregate_performance(daily: pd.DataFrame, by: str | list[str]) -> pd.DataFrame:
    """Use ratios of sums, never unweighted averages of ADR/occupancy."""
    result = daily.groupby(by, observed=True)[["revenue", "room_nights", "available_room_nights"]].sum()
    result["adr"] = result["revenue"] / result["room_nights"].replace(0, float("nan"))
    result["occupancy_rate"] = result["room_nights"] / result["available_room_nights"]
    result["revpar"] = result["revenue"] / result["available_room_nights"]
    return result


def calculate_kpis(bookings: pd.DataFrame, nightly: pd.DataFrame) -> dict:
    """Summarize completed-stay economics and all-booking cancellation rate."""
    completed = bookings.loc[bookings["booking_status"].eq("Completed")]
    revenue = float(nightly["nightly_revenue"].sum())
    room_nights = len(nightly)
    capacity = (END_DATE - START_DATE).days * len(ROOMS)
    return {
        "total_revenue": round(revenue, 2),
        "total_bookings": len(bookings),
        "completed_bookings": len(completed),
        "cancelled_bookings": int(bookings["booking_status"].eq("Cancelled").sum()),
        "room_nights": room_nights,
        "available_room_nights": capacity,
        "adr": revenue / room_nights if room_nights else None,
        "occupancy_rate": room_nights / capacity,
        "revpar": revenue / capacity,
        "average_length_of_stay": float(completed["nights"].mean()) if len(completed) else None,
        "cancellation_rate": float(bookings["booking_status"].eq("Cancelled").mean()) if len(bookings) else None,
        "average_lead_time": float(completed["lead_time"].mean()) if len(completed) else None,
    }


def monthly_performance(bookings: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Add check-in-month booking counts to stay-month financial results."""
    result = aggregate_performance(daily, "month")
    for status, column in [(None, "total_bookings"), ("Completed", "completed_bookings"), ("Cancelled", "cancelled_bookings")]:
        subset = bookings if status is None else bookings.loc[bookings["booking_status"].eq(status)]
        counts = subset.groupby(subset["check_in"].dt.to_period("M").astype(str)).size()
        result[column] = counts.reindex(result.index, fill_value=0)
    return result


def room_performance(bookings: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Compare room types with capacity-aware occupancy and revenue share."""
    result = aggregate_performance(daily, "room_type")
    result["revenue_share"] = result["revenue"] / result["revenue"].sum()
    completed = bookings.loc[bookings["booking_status"].eq("Completed")]
    result["completed_bookings"] = completed.groupby("room_type").size().reindex(result.index, fill_value=0)
    result["total_bookings"] = bookings.groupby("room_type").size().reindex(result.index, fill_value=0)
    return result
