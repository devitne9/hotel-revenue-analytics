"""Accounting and data-integrity tests with independently known outcomes."""

import unittest

import numpy as np
import pandas as pd

from src.clean_data import clean_bookings
from src.config import ROOMS
from src.generate_synthetic_data import generate_bookings, introduce_quality_issues
from src.kpi_analysis import (
    aggregate_performance, build_room_nights, calculate_kpis,
    daily_performance, monthly_performance,
)


def booking(number=1, check_in="2024-01-31", check_out="2024-02-02", rate=100, status="Completed", room_id="SYN-STA-01"):
    """Create a transparent fixture; derived columns deliberately need repair."""
    return {
        "booking_id": f"SYN-B{number:06d}", "booking_date": "2023-12-01",
        "check_in": check_in, "check_out": check_out, "room_id": room_id,
        "room_type": ROOMS[room_id], "guests": 2, "nights": -1,
        "room_rate": rate, "revenue": -1, "booking_channel": "Direct",
        "booking_status": status, "lead_time": -1,
    }


class AccountingTests(unittest.TestCase):
    def test_cross_month_stay_and_exclusive_checkout(self):
        clean, _ = clean_bookings(pd.DataFrame([booking()]))
        nightly = build_room_nights(clean)
        monthly = monthly_performance(clean, daily_performance(nightly))
        self.assertEqual(len(nightly), 2)
        self.assertEqual(monthly.loc["2024-01", "revenue"], 100)
        self.assertEqual(monthly.loc["2024-02", "revenue"], 100)
        self.assertEqual(monthly.loc["2024-01", "completed_bookings"], 1)
        self.assertEqual(monthly.loc["2024-02", "completed_bookings"], 0)
        self.assertNotIn(pd.Timestamp("2024-02-02"), nightly["stay_date"].tolist())

    def test_cancellations_and_weighted_adr(self):
        records = [
            booking(check_in="2024-01-01", check_out="2024-01-02", rate=100),
            booking(2, "2024-01-02", "2024-01-05", rate=200),
            booking(3, "2024-01-02", "2024-01-05", rate=900, status="Cancelled"),
        ]
        clean, _ = clean_bookings(pd.DataFrame(records))
        kpis = calculate_kpis(clean, build_room_nights(clean))
        self.assertEqual(kpis["total_revenue"], 700)
        self.assertEqual(kpis["room_nights"], 4)
        self.assertEqual(kpis["adr"], 175)  # (100 + 3 × 200) / 4, not 150.
        self.assertEqual(kpis["average_length_of_stay"], 2)
        self.assertAlmostEqual(kpis["cancellation_rate"], 1 / 3)
        self.assertEqual(clean.loc[2, "revenue"], 0)

    def test_full_calendar_includes_leap_day_and_unsold_months(self):
        clean, _ = clean_bookings(pd.DataFrame([booking()]))
        nightly = build_room_nights(clean)
        daily = daily_performance(nightly)
        monthly = monthly_performance(clean, daily)
        self.assertEqual(len(monthly), 36)
        self.assertEqual(monthly.loc["2024-02", "available_room_nights"], 29 * 18)
        self.assertEqual(monthly.loc["2023-02", "available_room_nights"], 28 * 18)
        self.assertEqual(monthly["available_room_nights"].sum(), 19728)
        self.assertEqual(monthly.loc["2025-06", "occupancy_rate"], 0)
        self.assertTrue(pd.isna(monthly.loc["2025-06", "adr"]))
        self.assertAlmostEqual(monthly.loc["2024-02", "occupancy_rate"], 1 / (29 * 18))

    def test_overlapping_completed_stays_rejected(self):
        clean, _ = clean_bookings(pd.DataFrame([booking(), booking(2)]))
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            build_room_nights(clean)

    def test_same_day_checkout_and_arrival_are_allowed(self):
        clean, _ = clean_bookings(pd.DataFrame([booking(), booking(2, "2024-02-02", "2024-02-03")]))
        self.assertEqual(len(build_room_nights(clean)), 3)

    def test_all_cancelled_means_zero_occupancy_and_undefined_adr(self):
        clean, _ = clean_bookings(pd.DataFrame([booking(status="Cancelled")]))
        nightly = build_room_nights(clean)
        kpis = calculate_kpis(clean, nightly)
        self.assertEqual(kpis["total_revenue"], 0)
        self.assertEqual(kpis["occupancy_rate"], 0)
        self.assertEqual(kpis["cancellation_rate"], 1)
        self.assertIsNone(kpis["adr"])
        self.assertEqual(daily_performance(nightly)["room_nights"].sum(), 0)


class CleaningTests(unittest.TestCase):
    def test_repairs_preserve_unknown_guests_and_remove_duplicates(self):
        row = booking()
        row.update(room_type=" standard ", booking_status=" completed ", guests=np.nan)
        clean, report = clean_bookings(pd.DataFrame([row, row]))
        self.assertEqual(len(clean), 1)
        self.assertEqual(report["duplicate_rows_removed"], 1)
        self.assertEqual(clean.loc[0, "nights"], 2)
        self.assertEqual(clean.loc[0, "revenue"], 200)
        self.assertEqual(clean.loc[0, "lead_time"], 61)
        self.assertTrue(pd.isna(clean.loc[0, "guests"]))
        self.assertEqual(report["revenue_values_rebuilt"], 1)

    def test_conflicting_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "conflicting"):
            clean_bookings(pd.DataFrame([booking(), booking(rate=200)]))

    def test_invalid_source_fields_rejected(self):
        changes = [
            {"booking_date": "2025-01-01"}, {"check_out": "2024-01-31"},
            {"check_in": "2022-12-31"}, {"check_out": "2026-01-02"},
            {"booking_date": None}, {"room_rate": -10}, {"room_rate": np.inf},
            {"room_type": "Unknown"}, {"booking_status": "Pending"},
            {"guests": 3}, {"guests": 1.5}, {"room_id": "SYN-STA-99"},
            {"booking_id": "REAL-123"},
        ]
        for change in changes:
            with self.subTest(change=change):
                row = booking()
                row.update(change)
                with self.assertRaises(ValueError):
                    clean_bookings(pd.DataFrame([row]))


class SimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.generated = generate_bookings()
        cls.clean, cls.report = clean_bookings(introduce_quality_issues(cls.generated))
        cls.nightly = build_room_nights(cls.clean)

    def test_fixed_seed_reproduces_bookings_and_export_issues(self):
        pd.testing.assert_frame_equal(self.generated, generate_bookings())
        pd.testing.assert_frame_equal(introduce_quality_issues(self.generated), introduce_quality_issues(self.generated))

    def test_cleaning_recovers_original_economics(self):
        canonical, _ = clean_bookings(self.generated)
        columns = [column for column in canonical.columns if column != "guests"]
        pd.testing.assert_frame_equal(canonical[columns], self.clean[columns])

    def test_inventory_and_accounting_reconcile(self):
        daily = daily_performance(self.nightly)
        kpis = calculate_kpis(self.clean, self.nightly)
        self.assertTrue((daily["room_nights"] <= daily["available_room_nights"]).all())
        self.assertFalse(self.nightly.duplicated(["room_id", "stay_date"]).any())
        self.assertAlmostEqual(self.clean["revenue"].sum(), kpis["total_revenue"], places=6)
        for grouping in ["month", "room_type", "season", "day_type"]:
            table = aggregate_performance(daily, grouping)
            self.assertAlmostEqual(table["revenue"].sum(), kpis["total_revenue"], places=6)
            self.assertEqual(table["room_nights"].sum(), kpis["room_nights"])
            self.assertEqual(table["available_room_nights"].sum(), 19728)
            np.testing.assert_allclose(table["adr"] * table["occupancy_rate"], table["revpar"])


if __name__ == "__main__":
    unittest.main()
