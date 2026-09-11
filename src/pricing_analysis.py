"""Interpretable descriptive pricing comparisons, without causal claims."""

import numpy as np
import pandas as pd

from src.kpi_analysis import aggregate_performance


def pricing_tables(bookings: pd.DataFrame, daily: pd.DataFrame, monthly: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compare achieved prices across seasons, occupancy and lead-time bands.

    Lead-time ADR is weighted by completed room nights. Within-room-type
    season comparisons reduce room-mix distortion, but do not identify
    price elasticity. Sold room nights are a proxy for realized demand.
    """
    completed = bookings.loc[bookings["booking_status"].eq("Completed")].copy()
    completed["lead_time_band"] = pd.cut(
        completed["lead_time"], [-1, 7, 30, 60, np.inf],
        labels=["0–7 days", "8–30 days", "31–60 days", "61+ days"],
    )
    lead_time = completed.groupby(["room_type", "lead_time_band"], observed=True).agg(
        completed_bookings=("booking_id", "size"), room_nights=("nights", "sum"), revenue=("revenue", "sum"),
    )
    lead_time["adr"] = lead_time["revenue"] / lead_time["room_nights"]
    relationships = pd.DataFrame({
        "relationship": ["Monthly occupancy vs ADR", "Monthly sold room nights vs ADR", "Completed booking lead time vs quoted nightly rate"],
        "pearson_r": [
            monthly["occupancy_rate"].corr(monthly["adr"]),
            monthly["room_nights"].corr(monthly["adr"]),
            completed["lead_time"].corr(completed["room_rate"]),
        ],
        "observations": [len(monthly), len(monthly), len(completed)],
    }).set_index("relationship")
    return {
        "pricing_by_season_room": aggregate_performance(daily, ["season", "room_type"]),
        "pricing_by_lead_time": lead_time,
        "pricing_correlations": relationships,
    }


def business_insights(kpis: dict, tables: dict[str, pd.DataFrame]) -> list[str]:
    """Derive specific findings and bounded recommendations from outputs."""
    monthly = tables["monthly_performance"]
    seasonal = tables["seasonal_performance"]
    rooms = tables["room_performance"]
    peak, trough = seasonal["occupancy_rate"].idxmax(), seasonal["occupancy_rate"].idxmin()
    leader = rooms["revenue"].idxmax()
    best_month = monthly["revenue"].idxmax()
    strong = seasonal.loc[peak]
    weak = seasonal.loc[trough]
    observations = [
        f"{best_month} generated the most monthly room revenue (€{monthly.loc[best_month, 'revenue']:,.2f}). Revenue is allocated by stay night, including stays crossing month-end.",
        f"{peak} season had the highest occupancy ({strong['occupancy_rate']:.1%}) at €{strong['adr']:.2f} ADR; {trough.lower()} season had the lowest ({weak['occupancy_rate']:.1%}) at €{weak['adr']:.2f} ADR.",
        f"The {leader} generated {rooms.loc[leader, 'revenue_share']:.1%} of room revenue (€{rooms.loc[leader, 'revenue']:,.2f}). Compare its {rooms.loc[leader, 'occupancy_rate']:.1%} occupancy and €{rooms.loc[leader, 'revpar']:.2f} RevPAR alongside revenue share; each category contains exactly one physical room.",
        f"{kpis['cancellation_rate']:.1%} of unique bookings were cancelled. Completed stays averaged {kpis['average_length_of_stay']:.2f} nights and were booked {kpis['average_lead_time']:.1f} days ahead.",
    ]
    if strong["occupancy_rate"] >= .75:
        observations.append(f"Pricing hypothesis: with {peak.lower()} season occupancy at {strong['occupancy_rate']:.1%}, test a €2–€3 nightly increase on selected busy dates, keeping trial quotes within the illustrative €30–€65 range, and monitor enquiries, cancellations and RevPAR. The data does not estimate an optimal price or uplift.")
    else:
        observations.append(f"Pricing hypothesis: even the strongest season has {strong['occupancy_rate']:.1%} occupancy; investigate unsold dates and room mix before assuming room for a broad price increase.")
    if weak["occupancy_rate"] < .50:
        observations.append(f"Promotion hypothesis: {trough.lower()} season occupancy of {weak['occupancy_rate']:.1%} suggests testing a modest multi-night offer on specific unsold dates, keeping quoted rates at least €30. Evaluate incremental room nights and net revenue after discount and channel costs, which are not modeled here.")
    else:
        observations.append(f"The weakest season still has {weak['occupancy_rate']:.1%} occupancy; inspect individual low-occupancy dates before recommending seasonal discounts.")
    observations.append("With four rooms, selling one extra room changes daily occupancy by 25 percentage points. Review comparable dates over several weeks and include booking counts before changing prices; one room type is only one physical room.")
    correlation = tables["pricing_correlations"].iloc[0]["pearson_r"]
    observations.append(f"Monthly occupancy and ADR have a Pearson correlation of {correlation:.2f}. Both share an explicitly programmed seasonal pattern; this is descriptive and cannot show that raising prices causes stronger demand.")
    return observations
