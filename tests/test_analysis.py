"""Accounting and data-integrity tests with independently known outcomes."""

import unittest

import numpy as np
import pandas as pd

from src.clean_data import clean_bookings
from src.config import ROOM_COUNTS, ROOMS
from src.generate_synthetic_data import generate_bookings, introduce_quality_issues
from src.kpi_analysis import (
    aggregate_performance, annual_performance, build_room_nights, calculate_kpis,
    daily_performance, monthly_performance,
)
from src.validation import validate_guesthouse


def booking(number=1, check_in="2024-01-31", check_out="2024-02-02", rate=40, status="Completed", room_id="SYN-STA-01"):
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
        self.assertEqual(monthly.loc["2024-01", "revenue"], 40)
        self.assertEqual(monthly.loc["2024-02", "revenue"], 40)
        self.assertEqual(monthly.loc["2024-01", "completed_bookings"], 1)
        self.assertEqual(monthly.loc["2024-02", "completed_bookings"], 0)
        self.assertNotIn(pd.Timestamp("2024-02-02"), nightly["stay_date"].tolist())

    def test_cancellations_and_weighted_adr(self):
        records = [
            booking(check_in="2024-01-01", check_out="2024-01-02", rate=30),
            booking(2, "2024-01-02", "2024-01-05", rate=50),
            booking(3, "2024-01-02", "2024-01-05", rate=65, status="Cancelled"),
        ]
        clean, _ = clean_bookings(pd.DataFrame(records))
        kpis = calculate_kpis(clean, build_room_nights(clean))
        self.assertEqual(kpis["total_revenue"], 180)
        self.assertEqual(kpis["room_nights"], 4)
        self.assertEqual(kpis["adr"], 45)  # (30 + 3 × 50) / 4, not 40.
        self.assertEqual(kpis["average_length_of_stay"], 2)
        self.assertAlmostEqual(kpis["cancellation_rate"], 1 / 3)
        self.assertEqual(clean.loc[2, "revenue"], 0)

    def test_full_calendar_includes_leap_day_and_unsold_months(self):
        clean, _ = clean_bookings(pd.DataFrame([booking()]))
        nightly = build_room_nights(clean)
        daily = daily_performance(nightly)
        monthly = monthly_performance(clean, daily)
        self.assertEqual(len(monthly), 36)
        self.assertEqual(monthly.loc["2024-02", "available_room_nights"], 29 * 4)
        self.assertEqual(monthly.loc["2023-02", "available_room_nights"], 28 * 4)
        self.assertEqual(monthly["available_room_nights"].sum(), 4384)
        self.assertEqual(monthly.loc["2025-06", "occupancy_rate"], 0)
        self.assertTrue(pd.isna(monthly.loc["2025-06", "adr"]))
        self.assertAlmostEqual(monthly.loc["2024-02", "occupancy_rate"], 1 / (29 * 4))

    def test_overlapping_completed_stays_rejected(self):
        clean, _ = clean_bookings(pd.DataFrame([booking(), booking(2)]))
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            build_room_nights(clean)

    def test_same_day_checkout_and_arrival_are_allowed(self):
        clean, _ = clean_bookings(pd.DataFrame([booking(), booking(2, "2024-02-02", "2024-02-03")]))
        self.assertEqual(len(build_room_nights(clean)), 3)

    def test_cross_year_stay_uses_stay_year_and_arrival_cohort(self):
        clean, _ = clean_bookings(pd.DataFrame([
            booking(check_in="2023-12-31", check_out="2024-01-03", rate=40),
            booking(2, "2024-02-01", "2024-02-03", status="Cancelled"),
        ]))
        annual = annual_performance(clean, daily_performance(build_room_nights(clean)))
        self.assertEqual(annual.loc[2023, "revenue"], 40)
        self.assertEqual(annual.loc[2024, "revenue"], 80)
        self.assertEqual(annual.loc[2023, "completed_bookings"], 1)
        self.assertEqual(annual.loc[2024, "completed_bookings"], 0)
        self.assertEqual(annual.loc[2023, "average_length_of_stay"], 3)
        self.assertEqual(annual.loc[2024, "cancellation_rate"], 1)
        self.assertEqual(annual.loc[2025, "total_bookings"], 0)

    def test_four_simultaneous_rooms_allowed_fifth_rejected(self):
        rows = [booking(number=i, room_id=room) for i, room in enumerate(ROOMS, 1)]
        clean, _ = clean_bookings(pd.DataFrame(rows))
        nightly = build_room_nights(clean)
        self.assertEqual(nightly.groupby("stay_date").size().max(), 4)
        clean, _ = clean_bookings(pd.DataFrame(rows + [booking(5)]))
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            build_room_nights(clean)
        invalid = pd.DataFrame(rows + [booking(5)])
        invalid.loc[4, "room_id"] = "SYN-FIFTH-01"
        with self.assertRaisesRegex(ValueError, "Unknown synthetic room"):
            clean_bookings(invalid)

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
        row.update(room_type=" standard double ", booking_status=" completed ", guests=np.nan)
        clean, report = clean_bookings(pd.DataFrame([row, row]))
        self.assertEqual(len(clean), 1)
        self.assertEqual(report["duplicate_rows_removed"], 1)
        self.assertEqual(clean.loc[0, "nights"], 2)
        self.assertEqual(clean.loc[0, "revenue"], 80)
        self.assertEqual(clean.loc[0, "lead_time"], 61)
        self.assertTrue(pd.isna(clean.loc[0, "guests"]))
        self.assertEqual(report["revenue_values_rebuilt"], 1)

    def test_conflicting_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "conflicting"):
            clean_bookings(pd.DataFrame([booking(), booking(rate=50)]))

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

    def test_four_room_scale_for_every_year(self):
        daily = daily_performance(self.nightly)
        annual = annual_performance(self.clean, daily)
        self.assertEqual(len(ROOMS), 4)
        self.assertEqual(sum(ROOM_COUNTS.values()), 4)
        self.assertEqual(self.clean["room_id"].nunique(), 4)
        self.assertEqual(annual["available_room_nights"].tolist(), [1460, 1464, 1460])
        self.assertTrue(annual["revenue"].between(25000, 35000).all())
        self.assertTrue(annual["occupancy_rate"].between(.4, .6).all())
        self.assertTrue(self.clean["room_rate"].between(30, 65).all())
        self.assertLessEqual(self.nightly.groupby("stay_date").size().max(), 4)
        self.assertGreater(annual["revenue"].nunique(), 1)
        np.testing.assert_allclose(annual["adr"], annual["revenue"] / annual["room_nights"])
        completed = self.clean["booking_status"].eq("Completed")
        np.testing.assert_allclose(self.clean["revenue"], (self.clean["room_rate"] * self.clean["nights"] * completed).round(2))
        self.assertEqual(annual["total_bookings"].sum(), len(self.clean))
        report = validate_guesthouse(self.clean, self.nightly, daily, annual)
        self.assertTrue(report["all_checks_passed"])
        self.assertTrue(all(report["checks"].values()))

    def test_seasonal_demand_and_rates_remain_visible_each_year(self):
        table = aggregate_performance(daily_performance(self.nightly), ["year", "season"])
        for year in (2023, 2024, 2025):
            with self.subTest(year=year):
                high, low = table.loc[(year, "High")], table.loc[(year, "Low")]
                self.assertGreater(high["occupancy_rate"], .65)
                self.assertLess(low["occupancy_rate"], .4)
                self.assertGreater(high["adr"], low["adr"])

    def test_validation_rejects_capacity_scale_and_accounting_drift(self):
        daily = daily_performance(self.nightly)
        annual = annual_performance(self.clean, daily)
        for column, value, message in [
            ("available_room_nights", 6570, "correct_annual_capacity"),
            ("revenue", 90000, "annual_revenue_in_target_range"),
            ("occupancy_rate", .95, "annual_occupancy_in_target_range"),
            ("adr", 150, "adr_reconciles"),
        ]:
            with self.subTest(column=column):
                bad = annual.copy()
                bad.loc[2023, column] = value
                with self.assertRaisesRegex(ValueError, message):
                    validate_guesthouse(self.clean, self.nightly, daily, bad)
        bad = self.clean.copy()
        bad.loc[0, "revenue"] += 1
        with self.assertRaisesRegex(ValueError, "revenue_equals_rate_times_completed_nights"):
            validate_guesthouse(bad, self.nightly, daily, annual)

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
            self.assertEqual(table["available_room_nights"].sum(), 4384)
            np.testing.assert_allclose(table["adr"] * table["occupancy_rate"], table["revpar"])


if __name__ == "__main__":
    unittest.main()
