# Default-market reference

`default_market.npz` records daily cross-sectional means and standard deviations,
plus every stock's final price, for the original default markets (1260 days,
200 stocks, seeds 42, 7 and 2026). It was generated with NumPy 1.26.4 only after
verifying the complete price arrays against the previous SHA-256 prefixes:

| Seed | Original complete-array hash |
| --- | --- |
| 42 | `daf0573a4500d002` |
| 7 | `808b79bb4b7c1353` |
| 2026 | `24b39b7f84fb8d0f` |

Linux NumPy 2.5.5 differs by at most 4.55e-13 in those prices. The regression test
therefore compares these numeric references at 1e-12 relative/absolute tolerance,
and separately requires exact repeatability of the entire price array within a
runtime. Do not regenerate the baseline merely to make a failing test pass;
market behavior changes require deliberate review.
