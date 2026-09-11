# Findings from synthetic four-room guesthouse data (EUR)

| Year | Revenue (EUR) | Occupied room nights | Available room nights | Occupancy | ADR (EUR) | All bookings | Completed | Avg. stay (nights) | Cancellation rate |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 2023 | €29,476.66 | 674 | 1,460 | 46.2% | €43.73 | 264 | 227 | 2.97 | 14.0% |
| 2024 | €30,262.17 | 679 | 1,464 | 46.4% | €44.57 | 274 | 231 | 2.94 | 15.7% |
| 2025 | €31,444.29 | 691 | 1,460 | 47.3% | €45.51 | 254 | 221 | 3.12 | 13.0% |

Revenue and occupied (booked) room nights use stay year and exclude cancellations. Booking counts, average full stay length and cancellation rates use check-in year. 2024 includes leap day.

All four-room capacity and calibration checks passed.

- 2025-07 generated the most monthly room revenue (€5,360.52). Revenue is allocated by stay night, including stays crossing month-end.

- High season had the highest occupancy (77.7%) at €49.35 ADR; low season had the lowest (25.4%) at €36.80 ADR.

- The Superior Double generated 27.1% of room revenue (€24,680.15). Compare its 46.3% occupancy and €22.52 RevPAR alongside revenue share; each category contains exactly one physical room.

- 14.3% of unique bookings were cancelled. Completed stays averaged 3.01 nights and were booked 28.8 days ahead.

- Pricing hypothesis: with high season occupancy at 77.7%, test a €2–€3 nightly increase on selected busy dates, keeping trial quotes within the illustrative €30–€65 range, and monitor enquiries, cancellations and RevPAR. The data does not estimate an optimal price or uplift.

- Promotion hypothesis: low season occupancy of 25.4% suggests testing a modest multi-night offer on specific unsold dates, keeping quoted rates at least €30. Evaluate incremental room nights and net revenue after discount and channel costs, which are not modeled here.

- With four rooms, selling one extra room changes daily occupancy by 25 percentage points. Review comparable dates over several weeks and include booking counts before changing prices; one room type is only one physical room.

- Monthly occupancy and ADR have a Pearson correlation of 0.95. Both share an explicitly programmed seasonal pattern; this is descriptive and cannot show that raising prices causes stronger demand.
