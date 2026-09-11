"""Create consistent, presentation-ready figures from analytical tables."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter, StrMethodFormatter
import numpy as np
import pandas as pd

from src.config import FIGURES_DIR, SEASON_ORDER

NAVY = "#17324D"
TEAL = "#167D8D"
GOLD = "#E6A54A"
GRAY = "#64748B"
COLORS = [TEAL, NAVY, GOLD]


def _canvas(title: str, subtitle: str, ylabel: str) -> tuple:
    """Start a labeled chart with restrained typography and generous space."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "axes.edgecolor": "#CBD5E1",
        "axes.labelcolor": NAVY, "xtick.color": GRAY, "ytick.color": GRAY,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white",
    })
    fig, ax = plt.subplots(figsize=(11, 5.5))
    fig.subplots_adjust(left=.10, right=.96, top=.78, bottom=.19)
    fig.text(.10, .93, title, color=NAVY, fontsize=20, fontweight="bold")
    fig.text(.10, .86, subtitle, color=GRAY, fontsize=10)
    fig.text(.10, .035, "SYNTHETIC DATA  •  18-room hotel  •  2023–2025  •  Room revenue in USD", color=GRAY, fontsize=8)
    ax.set_ylabel(ylabel, labelpad=12)
    ax.grid(axis="y", color="#E8EDF2", linewidth=.8)
    ax.set_axisbelow(True)
    return fig, ax


def _save(fig: plt.Figure, name: str) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / f"{name}.png", dpi=160)
    plt.close(fig)


def create_visualizations(bookings: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> None:
    """Write ten charts, all derived from the same validated analysis."""
    monthly = tables["monthly_performance"]
    dates = pd.to_datetime(monthly.index)
    x = np.arange(len(monthly))
    specs = [
        ("revenue", "Monthly room revenue", "Revenue earned on each stay night; cancelled bookings excluded.", "Room revenue (USD)", "monthly_revenue"),
        ("adr", "Average daily rate by month", "Room revenue divided by completed room nights; weighted across room types.", "ADR (USD per sold room night)", "monthly_adr"),
        ("occupancy_rate", "Monthly room occupancy", "Completed room nights divided by 18 rooms × calendar days in each month.", "Occupancy rate", "monthly_occupancy"),
    ]
    for column, title, subtitle, ylabel, name in specs:
        fig, ax = _canvas(title, subtitle, ylabel)
        y = monthly[column].to_numpy()
        ax.plot(x, y, color=TEAL, linewidth=2.5, marker="o", markersize=4)
        ax.fill_between(x, y, color=TEAL, alpha=.08)
        ax.set_xticks(x[::3], dates.strftime("%b %Y")[::3], rotation=35, ha="right")
        ax.set_ylim(bottom=0)
        if column == "occupancy_rate":
            ax.set_ylim(0, 1)
            ax.yaxis.set_major_formatter(PercentFormatter(1))
        else:
            ax.yaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
        _save(fig, name)

    fig, ax = _canvas("Booking volume by arrival month", "Unique bookings by final status; grouped by check-in month, not creation month.", "Number of bookings")
    ax.bar(x, monthly["completed_bookings"], color=TEAL, label="Completed")
    ax.bar(x, monthly["cancelled_bookings"], bottom=monthly["completed_bookings"], color=GOLD, label="Cancelled")
    ax.set_xticks(x[::3], dates.strftime("%b %Y")[::3], rotation=35, ha="right")
    ax.legend(frameon=False, loc="upper right")
    _save(fig, "monthly_bookings")

    room = tables["room_performance"].sort_values("revenue", ascending=False)
    for column, title, subtitle, ylabel, name in [
        ("revenue", "Room revenue by room type", "Inventory: 10 Standard, 5 Deluxe, 3 Family. Revenue share also reflects room count.", "Room revenue (USD)", "room_type_revenue"),
        ("adr", "Achieved ADR by room type", "Completed room revenue divided by sold room nights within each room type.", "ADR (USD per sold room night)", "room_type_adr"),
    ]:
        fig, ax = _canvas(title, subtitle, ylabel)
        bars = ax.bar(room.index, room[column], color=COLORS, width=.55)
        ax.bar_label(bars, labels=[f"${value:,.0f}" for value in room[column]], padding=7, color=NAVY)
        ax.set_ylim(0, room[column].max() * 1.20)
        ax.yaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
        _save(fig, name)

    seasonal = tables["seasonal_performance"].reindex(SEASON_ORDER)
    fig, ax = _canvas(f"{seasonal['occupancy_rate'].idxmax()} leads realized seasonal demand", "Occupancy compares sold room nights with available inventory across all three years.", "Occupancy rate")
    bars = ax.bar(seasonal.index, seasonal["occupancy_rate"], color=[GRAY, TEAL, GOLD, NAVY], width=.55)
    ax.bar_label(bars, labels=[f"{value:.1%}" for value in seasonal["occupancy_rate"]], padding=7, color=NAVY)
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    _save(fig, "seasonal_demand")

    completed = bookings.loc[bookings["booking_status"].eq("Completed")]
    fig, ax = _canvas("How far ahead do guests book?", "Completed bookings; days between booking creation and check-in.", "Completed bookings")
    ax.hist(completed["lead_time"], bins=np.arange(0, 191, 10), color=TEAL, edgecolor="white")
    median = completed["lead_time"].median()
    ax.axvline(median, color=GOLD, linewidth=2, label=f"Median: {median:.0f} days")
    ax.set_xlabel("Booking lead time (days)")
    ax.legend(frameon=False)
    _save(fig, "lead_time_distribution")

    fig, ax = _canvas("Monthly occupancy and achieved ADR", "One point per month; shared synthetic seasonality does not establish a causal pricing effect.", "ADR (USD per sold room night)")
    for season, color in zip(SEASON_ORDER, [GRAY, TEAL, GOLD, NAVY]):
        months = {"Winter": [12, 1, 2], "Spring": [3, 4, 5], "Summer": [6, 7, 8], "Autumn": [9, 10, 11]}[season]
        mask = dates.month.isin(months)
        ax.scatter(monthly.loc[mask, "occupancy_rate"], monthly.loc[mask, "adr"], color=color, label=season, s=60, alpha=.85)
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.yaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
    ax.set_xlabel("Monthly occupancy rate")
    ax.legend(frameon=False, ncol=2)
    _save(fig, "occupancy_vs_adr")

    lead = tables["pricing_by_lead_time"]["adr"].unstack("room_type")
    fig, ax = _canvas("Lead time and achieved room rates", "Weighted ADR by lead-time band and room type; season remains a confounder.", "ADR (USD per sold room night)")
    for room_type, color in zip(lead.columns, COLORS):
        ax.plot(lead.index.astype(str), lead[room_type], marker="o", color=color, linewidth=2, label=room_type)
    ax.yaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
    ax.set_xlabel("Booking lead time")
    ax.legend(frameon=False, ncol=3)
    _save(fig, "lead_time_vs_adr")
