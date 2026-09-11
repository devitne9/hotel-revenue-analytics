"""Simulate bookings using invented assumptions; no external data is read."""

import numpy as np
import pandas as pd

from src.config import (
    BASE_RATES, CHANNELS, DATA_DIR, END_DATE, MAX_GUESTS, ROOMS, SEED,
    SEASON_BY_MONTH, START_DATE,
)


def generate_bookings(seed: int = SEED) -> pd.DataFrame:
    """Create capacity-constrained stays for 2023–2025 using a fixed seed.

    Each vacant room gets one potential arrival per day. Cancelled requests
    never consume inventory: cancellations are assumed known before arrival.
    Prices and demand share a seasonal driver, so their correlation is not
    evidence of price elasticity. All identifiers are visibly artificial.
    """
    rng = np.random.default_rng(seed)
    next_available = {room_id: START_DATE for room_id in ROOMS}
    arrival_chance = {
        1: .09, 2: .11, 3: .14, 4: .24, 5: .30, 6: .53,
        7: .60, 8: .58, 9: .40, 10: .24, 11: .11, 12: .13,
    }
    seasonal_price = {"Low": .92, "Shoulder": 1.0, "High": 1.25}
    records = []
    for check_in in pd.date_range(START_DATE, END_DATE, inclusive="left"):
        season = SEASON_BY_MONTH[check_in.month]
        weekend = check_in.dayofweek in (4, 5)  # Friday and Saturday nights.
        for room_id, room_type in ROOMS.items():
            if next_available[room_id] > check_in:
                continue
            chance = arrival_chance[check_in.month] + .07 * weekend
            if room_type == "Family Room":
                chance += .06 if season == "High" else -.03
            if rng.random() >= chance:
                continue
            nights = int(np.clip(1 + rng.poisson(2.5 if season == "High" else 1.6), 1, 9))
            # Keep all stays within the reporting window; document this edge effect.
            nights = min(nights, (END_DATE - check_in).days)
            lead_time = int(np.clip(rng.lognormal(3.35 if season == "High" else 2.7, .8), 0, 180))
            channel = str(rng.choice(CHANNELS, p=[.43, .47, .10]))
            cancellation_probability = {"Direct": .08, "Online travel agency": .19, "Travel agent": .12}[channel]
            cancellation_probability += .04 * (lead_time > 60)
            status = "Cancelled" if rng.random() < cancellation_probability else "Completed"
            advance_discount = .94 if lead_time >= 60 else 1.0
            last_minute_discount = .95 if lead_time <= 3 and season == "Low" else 1.0
            rate = round(
                BASE_RATES[room_type] * seasonal_price[season]
                * (1.08 if weekend else 1.0) * (1 + .02 * (check_in.year - 2023))
                * advance_discount * last_minute_discount * rng.uniform(.94, 1.06), 2,
            )
            # A small guesthouse's quoted rate bounds, never a revenue target.
            rate = float(np.clip(rate, 30.0, 65.0))
            check_out = check_in + pd.Timedelta(days=nights)
            records.append({
                "booking_id": f"SYN-B{len(records) + 1:06d}",
                "booking_date": check_in - pd.Timedelta(days=lead_time),
                "check_in": check_in,
                "check_out": check_out,
                "room_id": room_id,
                "room_type": room_type,
                "guests": int(rng.integers(1, MAX_GUESTS[room_type] + 1)),
                "nights": nights,
                "room_rate": rate,
                "revenue": round(rate * nights, 2) if status == "Completed" else 0.0,
                "booking_channel": channel,
                "booking_status": status,
                "lead_time": lead_time,
            })
            if status == "Completed":
                next_available[room_id] = check_out
    return pd.DataFrame(records)


def introduce_quality_issues(bookings: pd.DataFrame, seed: int = SEED + 1) -> pd.DataFrame:
    """Add reproducible, recoverable export issues for the cleaning exercise.

    Preserve all source dates, rates and statuses. Missing guest counts stay
    unknown after cleaning: they are not needed for room-based KPIs.
    """
    rng = np.random.default_rng(seed)
    raw = bookings.copy()
    n = len(raw)
    for column in ("room_type", "booking_channel", "booking_status"):
        rows = rng.choice(n, size=max(1, n // 50), replace=False)
        raw.loc[rows, column] = raw.loc[rows, column].str.lower().map(lambda value: f" {value} ")
    raw.loc[rng.choice(n, size=max(1, n // 100), replace=False), "guests"] = np.nan
    for column in ("nights", "revenue", "lead_time"):
        rows = rng.choice(n, size=max(1, n // 100), replace=False)
        raw.loc[rows, column] = -1
    duplicates = raw.iloc[rng.choice(n, size=max(1, n // 100), replace=False)]
    return pd.concat([raw, duplicates], ignore_index=True)


def main() -> None:
    """Write a raw synthetic export with controlled quality issues."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw = introduce_quality_issues(generate_bookings())
    raw.to_csv(DATA_DIR / "synthetic_bookings.csv", index=False, date_format="%Y-%m-%d")
    print(f"Generated {len(raw):,} synthetic export rows.")


if __name__ == "__main__":
    main()
