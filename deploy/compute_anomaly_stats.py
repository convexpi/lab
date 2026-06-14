#!/usr/bin/env python3
"""
compute_anomaly_stats.py — Fetch French factor data and write anomaly-stats.json.

Run this to refresh web/public/anomaly-stats.json. The file is committed to
the repo and read by the /anomalies web page at build time. GitHub Actions
runs this monthly so the OOS sample grows automatically.

Usage:
    python deploy/compute_anomaly_stats.py
    python deploy/compute_anomaly_stats.py --no-monthly   # skip sparkline data
    python deploy/compute_anomaly_stats.py --out path/to/anomaly-stats.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from convexpi.lab.anomalies import compute_all


def main():
    p = argparse.ArgumentParser(description="Compute anomaly stats and write JSON")
    p.add_argument(
        "--out",
        default=str(Path(__file__).parent.parent / "web" / "public" / "anomaly-stats.json"),
    )
    p.add_argument("--no-monthly", action="store_true",
                   help="Skip monthly sparkline data (faster)")
    args = p.parse_args()

    print("Fetching French factor data…")
    stats = compute_all(include_monthly=not args.no_monthly)

    payload = {
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        "source":     "Kenneth French Data Library (mba.tuck.dartmouth.edu)",
        "anomalies":  stats,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"Written {len(stats)} anomalies to {out}")

    for s in stats:
        decay_str = f"{s['decay_pct']:+.1f}%" if s['decay_pct'] != 0 else "N/A"
        print(f"  {s['name']:<22} IS={s['is_sharpe']:>6.3f}  "
              f"OOS={s['oos_sharpe']:>6.3f}  decay={decay_str}  [{s['status']}]")


if __name__ == "__main__":
    main()
