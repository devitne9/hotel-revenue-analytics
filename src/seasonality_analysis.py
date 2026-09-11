"""Describe seasonal and weekday patterns with comparable denominators."""

import pandas as pd

from src.config import SEASON_ORDER
from src.kpi_analysis import aggregate_performance


def seasonality_tables(bookings: pd.DataFrame, daily: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return calendar-month, seasonal and weekday/weekend performance."""
    seasonal = aggregate_performance(daily, "season").reindex(SEASON_ORDER)
    counts = bookings.groupby("season").size()
    seasonal["total_bookings"] = counts.reindex(seasonal.index, fill_value=0)
    return {
        "seasonal_performance": seasonal,
        "calendar_month_performance": aggregate_performance(daily, "month_number"),
        "weekday_weekend_performance": aggregate_performance(daily, "day_type"),
    }
