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
CURRENCY = "EUR"
ROOM_COUNTS = {"Standard Double": 1, "Twin Room": 1, "Family Room": 1, "Superior Double": 1}
BASE_RATES = {"Standard Double": 35.0, "Twin Room": 36.0, "Family Room": 40.0, "Superior Double": 42.0}
MAX_GUESTS = {"Standard Double": 2, "Twin Room": 2, "Family Room": 4, "Superior Double": 2}
ROOMS = {
    f"SYN-{room_type[:3].upper()}-{number:02d}": room_type
    for room_type, count in ROOM_COUNTS.items()
    for number in range(1, count + 1)
}
CHANNELS = ("Direct", "Online travel agency", "Travel agent")
STATUSES = ("Completed", "Cancelled")
SEASON_BY_MONTH = {
    1: "Low", 2: "Low", 3: "Low", 4: "Shoulder",
    5: "Shoulder", 6: "High", 7: "High", 8: "High",
    9: "High", 10: "Shoulder", 11: "Low", 12: "Low",
}
SEASON_ORDER = ["Low", "Shoulder", "High"]
