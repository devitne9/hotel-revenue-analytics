"""Shared simulation assumptions and project-relative output paths."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = ROOT / "figures"
START_DATE = pd.Timestamp("2023-01-01")
END_DATE = pd.Timestamp("2026-01-01")  # Exclusive, like a hotel's checkout date.
SEED = 42
CURRENCY = "USD"
ROOM_COUNTS = {"Standard": 10, "Deluxe": 5, "Family": 3}
BASE_RATES = {"Standard": 75.0, "Deluxe": 110.0, "Family": 145.0}
MAX_GUESTS = {"Standard": 2, "Deluxe": 2, "Family": 4}
ROOMS = {
    f"SYN-{room_type[:3].upper()}-{number:02d}": room_type
    for room_type, count in ROOM_COUNTS.items()
    for number in range(1, count + 1)
}
CHANNELS = ("Direct", "Online travel agency", "Travel agent")
STATUSES = ("Completed", "Cancelled")
SEASON_BY_MONTH = {
    1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring",
    5: "Spring", 6: "Summer", 7: "Summer", 8: "Summer",
    9: "Autumn", 10: "Autumn", 11: "Autumn", 12: "Winter",
}
SEASON_ORDER = ["Winter", "Spring", "Summer", "Autumn"]
