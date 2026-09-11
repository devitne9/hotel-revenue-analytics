"""Normalize an export, validate source fields and rebuild derived metrics."""

import json

import numpy as np
import pandas as pd

from src.config import (
    CHANNELS, DATA_DIR, END_DATE, MAX_GUESTS, REPORTS_DIR, ROOMS,
    SEASON_BY_MONTH, START_DATE, STATUSES,
)

REQUIRED_COLUMNS = [
    "booking_id", "booking_date", "check_in", "check_out", "room_id",
    "room_type", "guests", "nights", "room_rate", "revenue",
    "booking_channel", "booking_status", "lead_time",
]


def clean_bookings(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return validated unique bookings and an auditable cleaning summary.

    Fail on conflicting IDs, invalid dates/rates/categories or impossible
    guest counts instead of silently dropping records. Exact duplicates are
    safe to remove. Nights, revenue and lead time come from source fields.
    """
    missing = set(REQUIRED_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    frame = raw[REQUIRED_COLUMNS].copy()
    report = {"input_rows": len(frame)}
    normalized_cells = 0
    for column, allowed in {
        "room_type": set(ROOMS.values()),
        "booking_channel": CHANNELS,
        "booking_status": STATUSES,
    }.items():
        mapping = {value.casefold(): value for value in allowed}
        normalized = frame[column].astype("string").str.strip().str.casefold().map(mapping)
        if normalized.isna().any():
            raise ValueError(f"Unknown or missing {column}")
        normalized_cells += int(frame[column].ne(normalized).sum())
        frame[column] = normalized
    report["normalized_category_cells"] = normalized_cells
    before = len(frame)
    frame = frame.drop_duplicates().copy()
    report["duplicate_rows_removed"] = before - len(frame)
    if frame["booking_id"].isna().any() or frame["booking_id"].duplicated().any():
        raise ValueError("Missing or conflicting booking IDs")
    if not frame["booking_id"].str.fullmatch(r"SYN-B\d{6}").all():
        raise ValueError("Booking IDs must use the synthetic SYN-B prefix")
    expected_type = frame["room_id"].map(ROOMS)
    if expected_type.isna().any() or not expected_type.eq(frame["room_type"]).all():
        raise ValueError("Unknown synthetic room or mismatched room type")
    for column in ("booking_date", "check_in", "check_out"):
        frame[column] = pd.to_datetime(frame[column], errors="raise")
        if frame[column].isna().any() or not frame[column].eq(frame[column].dt.normalize()).all():
            raise ValueError(f"{column} must contain complete dates without times")
    if (
        (frame["booking_date"] > frame["check_in"]).any()
        or (frame["check_out"] <= frame["check_in"]).any()
        or (frame["check_in"] < START_DATE).any()
        or (frame["check_out"] > END_DATE).any()
    ):
        raise ValueError("Invalid booking chronology or stay outside the reporting window")
    frame["room_rate"] = pd.to_numeric(frame["room_rate"], errors="raise")
    if not np.isfinite(frame["room_rate"]).all() or (frame["room_rate"] <= 0).any():
        raise ValueError("Room rates must be finite and positive")
    guests = pd.to_numeric(frame["guests"], errors="raise")
    known = guests.notna()
    if (
        not np.isfinite(guests[known]).all()
        or (guests[known] % 1 != 0).any()
        or (guests[known] < 1).any()
        or (guests[known] > frame.loc[known, "room_type"].map(MAX_GUESTS)).any()
    ):
        raise ValueError("Guest counts must be whole numbers within room capacity")
    frame["guests"] = guests.astype("Int64")
    report["missing_guests_retained"] = int(guests.isna().sum())
    derived = {
        "nights": (frame["check_out"] - frame["check_in"]).dt.days,
        "lead_time": (frame["check_in"] - frame["booking_date"]).dt.days,
    }
    derived["revenue"] = (
        frame["room_rate"] * derived["nights"] * frame["booking_status"].eq("Completed")
    ).round(2)
    for column, values in derived.items():
        original = pd.to_numeric(frame[column], errors="coerce")
        report[f"{column}_values_rebuilt"] = int((~np.isclose(original, values, equal_nan=False)).sum())
        frame[column] = values
    frame["month"] = frame["check_in"].dt.month
    frame["season"] = frame["month"].map(SEASON_BY_MONTH)
    frame["weekday"] = frame["check_in"].dt.day_name()
    frame["is_weekend"] = frame["check_in"].dt.dayofweek.isin([4, 5])
    frame = frame.sort_values(["check_in", "booking_id"]).reset_index(drop=True)
    report["output_rows"] = len(frame)
    return frame, report


def main() -> None:
    """Clean the generated CSV and persist the quality report."""
    clean, report = clean_bookings(pd.read_csv(DATA_DIR / "synthetic_bookings.csv"))
    clean.to_csv(DATA_DIR / "cleaned_bookings.csv", index=False, date_format="%Y-%m-%d")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "data_quality.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
