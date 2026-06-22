"""
author_replication_wikis.py — hand-authored wikis that bridge papers to runnable code.

Writes full factor wikis for the two replication papers that lack them (industry momentum, time
series momentum) and appends an "Executable replication on ConvexPi" section — with the real
out-of-sample verdicts from the replication benchmark and a link to the in-browser playground — to
the three replication papers that already have wikis (momentum, value, size).

Public, paper/strategy-focused content only (no course-internal material).

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python pipeline/author_replication_wikis.py --dry-run
    ...                                          python pipeline/author_replication_wikis.py
"""
from __future__ import annotations
import argparse, datetime, json, os, sys, urllib.request

URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or ""
KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
PLAYGROUND = "https://convexpi.ai/playground"

# Real numbers from the replication benchmark (replications/results.json).
VERDICTS = {
    "momentum":          dict(pub=1993, is_=0.63, oos=0.38, recent=0.18, tag="ALIVE",
                              note="Still clearly positive out of sample, though roughly 40% of the in-sample Sharpe is gone — and it remains prone to violent crashes (2009)."),
    "value":             dict(pub=1993, is_=0.49, oos=0.21, recent=0.01, tag="DECAYED",
                              note="Over half the in-sample Sharpe is gone, and the last decade is essentially flat — the 2007–2020 value drought."),
    "size":              dict(pub=1981, is_=0.20, oos=-0.02, recent=-0.15, tag="DORMANT",
                              note="Negative out of sample and over the last decade; the premium that was modest to begin with did not survive publication."),
    "industry_momentum": dict(pub=1999, is_=0.47, oos=0.31, recent=0.24, tag="ALIVE",
                              note="Holds up out of sample, in line with cross-sectional momentum — sector-level trends persist."),
    "trend":             dict(pub=2012, is_=0.17, oos=0.48, recent=0.33, tag="ALIVE",
                              note="The out-of-sample Sharpe exceeds the in-sample estimate (this single-asset version benefits from the short post-2012 window and the strong 2020/2022 trends); trend following did not crowd out."),
}


def exec_section(name):
    v = VERDICTS[name]
    rows = (f"| In-sample (pre-{v['pub']}) | {v['is_']:+.2f} |\n"
            f"| Out-of-sample (≥ {v['pub']}) | {v['oos']:+.2f} |\n"
            f"| Last 10 years | {v['recent']:+.2f} |")
    return (
        "## Executable replication on ConvexPi\n\n"
        "This factor is reproduced as runnable, out-of-sample-scored code on real Ken-French data. "
        "Splitting the standard long-short return series at the paper's publication year (the "
        "McLean & Pontiff test) gives:\n\n"
        "| Period | Annualized Sharpe |\n|---|---|\n" + rows + "\n\n"
        f"**Verdict: {v['tag']}.** {v['note']}\n\n"
        f"Run it yourself in the browser — change the split year, the lookback, or the costs — at "
        f"[the ConvexPi playground]({PLAYGROUND}). Nothing is sent to a server.\n"
    )


INDUSTRY_MOMENTUM_WIKI = """\
# Do Industries Explain Momentum?

**Source:** Moskowitz, T. J. & Grinblatt, M. (1999). *Journal of Finance* 54(4), 1249–1290.

## TL;DR
Industries themselves exhibit strong momentum: buying the past-winner industries and shorting the
past-loser industries earns roughly 0.4–0.5% per month. Strikingly, once you control for industry
momentum, much of the individual-stock momentum of Jegadeesh & Titman (1993) weakens — a large part
of "stock momentum" is really momentum in the stock's industry.

## What anomaly it documents
Past industry returns predict future industry returns over horizons of one to twelve months: winning
industries keep winning and losing industries keep losing in the near term. The effect is
cross-sectional (long winners / short losers across industries) and is largest at short horizons,
decaying and eventually reversing over multi-year windows. The authors show industry momentum is
distinct from, and partly subsumes, individual-stock momentum, size, value, and the cross-sectional
dispersion in expected returns.

## How to construct it
- **Universe / building blocks:** value-weighted industry portfolios (the paper uses 20 industries
  built from CRSP; the Ken-French 12- or 49-industry portfolios are the standard public proxy).
- **Sorting variable:** trailing industry return, commonly the past 6 months, skipping the most
  recent week/month to avoid bid-ask bounce and short-term reversal.
- **Portfolio:** long the top-tertile (or top-3) industries, short the bottom; equal-weight the legs.
- **Rebalancing:** monthly; one-month holding period.
- **ConvexPi replication:** the 12 Ken-French industry portfolios, ranked on the trailing 12-month
  return skipping the most recent month, long the top 3 and short the bottom 3, rebalanced monthly.

## Evidence and replication
| Period | Sharpe / return | Source |
|--------|-----------------|--------|
| IS (1963–1995, 1-month industry momentum) | ~0.43%/month, highly significant | this paper |
| OOS (post-1999, ConvexPi 12-industry version) | Sharpe 0.31 (vs 0.47 pre-1999) | ConvexPi benchmark |

Industry momentum survives out of sample with roughly a third of its in-sample Sharpe lost — a
milder decay than the size or value premia, consistent with cross-sectional momentum more broadly
remaining one of the more robust anomalies (McLean & Pontiff, 2016).

## Why it might work
- **Slow information diffusion:** industry-wide news (commodity prices, regulation, demand shocks) is
  incorporated gradually across the sector, so recent industry returns predict near-term returns.
- **Behavioural underreaction** to sector fundamentals, plus delayed sector rotation by investors.
- **Risk-based readings** are weaker here than for value; the effect looks more like mispricing.

## Limitations and risks
- **Turnover and transaction costs:** monthly rebalancing of concentrated sector bets is costly,
  though cheaper than single-name momentum.
- **Crash risk:** like all momentum, vulnerable to sharp reversals after market bottoms (e.g. 2009).
- **Industry definitions matter:** results shift with the number and construction of industries.
- **Crowding:** widely known since publication; sector-rotation products may have compressed the edge.

## Key references
- Jegadeesh, N. & Titman, S. (1993) — *Returns to Buying Winners and Selling Losers* — Journal of Finance
- Moskowitz, T. & Grinblatt, M. (1999) — *Do Industries Explain Momentum?* — Journal of Finance
- Grundy, B. & Martin, J. S. (2001) — *Understanding the Nature of the Risks and the Source of the Rewards to Momentum Investing* — Review of Financial Studies
- Asness, C., Moskowitz, T. & Pedersen, L. (2013) — *Value and Momentum Everywhere* — Journal of Finance
- Daniel, K. & Moskowitz, T. (2016) — *Momentum Crashes* — Journal of Financial Economics
"""

TREND_WIKI = """\
# Time Series Momentum

**Source:** Moskowitz, T. J., Ooi, Y. H. & Pedersen, L. H. (2012). *Journal of Financial Economics*
104(2), 228–250.

## TL;DR
An asset's *own* past 12-month excess return predicts its future return. A strategy that goes long
instruments with positive trailing-year returns and short those with negative returns, each scaled
to a constant volatility, earns a large, diversified Sharpe ratio across 58 futures and forwards —
and crucially delivers positive returns during equity market crises ("crisis alpha").

## What anomaly it documents
Time-series (absolute) momentum is distinct from cross-sectional momentum: it depends only on an
asset's own past return, not its rank against peers. Past 12-month returns positively predict the
next ~1–12 months, after which returns partially reverse — the signature of initial underreaction
followed by delayed overreaction. The effect is remarkably consistent across equity indices, bonds,
commodities, and currencies.

## How to construct it
- **Signal:** the sign of each instrument's past 12-month excess return (long if positive, short if
  negative). Some implementations scale by the return's magnitude or use multiple lookbacks.
- **Position sizing:** scale each position to a target volatility using an ex-ante volatility
  estimate, so no single instrument dominates.
- **Universe:** diversify across asset classes (equity-index, bond, FX, and commodity futures).
- **Rebalancing:** monthly.
- **ConvexPi replication:** a single-asset version on the U.S. equity market — hold the market long
  when its trailing 12-month excess return is positive and short when negative, rebalanced monthly.
  This is a deliberately minimal proxy for the diversified, vol-scaled factor in the paper.

## Evidence and replication
| Period | Sharpe | Source |
|--------|--------|--------|
| IS (1985–2009, diversified TSMOM factor) | ~1.4 gross, strongly positive in 2008 | this paper |
| OOS (post-2012, ConvexPi single-asset market version) | 0.48 (vs 0.17 pre-2012) | ConvexPi benchmark |

The diversified factor's Sharpe is far higher than the single-asset replication because most of
TSMOM's strength comes from diversification across dozens of trends; our minimal market-only version
nonetheless remains positive out of sample. Note the OOS estimate is flattered by the short
post-2012 window and the strong 2020 and 2022 trends.

## Why it might work
- **Underreaction then overreaction:** investors are slow to update to new information, then
  extrapolate, producing trends that persist before reversing.
- **Risk transfer / hedging demand:** speculators earn a premium for absorbing hedgers' positions.
- **Crisis alpha:** trends tend to persist during prolonged drawdowns, so trend following often
  profits when equities fall — a diversification benefit, not just a return source.

## Limitations and risks
- **Whipsaw:** in choppy, trendless, mean-reverting markets the strategy bleeds via repeated reversals.
- **Capacity and costs:** large in liquid futures, but turnover and slippage matter at scale.
- **Robustness debate:** Huang, Li, Wang & Zhou (2019), *Time Series Momentum: Is It There?*, argue
  the effect is statistically fragile once the near-always-long tilt and time-varying means are
  accounted for — a useful caution that the headline result is sensitive to specification.

## Key references
- Moskowitz, T., Ooi, Y. H. & Pedersen, L. (2012) — *Time Series Momentum* — Journal of Financial Economics
- Hurst, B., Ooi, Y. H. & Pedersen, L. (2017) — *A Century of Evidence on Trend-Following Investing* — Journal of Portfolio Management
- Huang, D., Li, J., Wang, L. & Zhou, G. (2019) — *Time Series Momentum: Is It There?* — Journal of Financial Economics
- Asness, C., Moskowitz, T. & Pedersen, L. (2013) — *Value and Momentum Everywhere* — Journal of Finance
"""

# id -> (replication name, full wiki or None to append-only)
TARGETS = {
    "82b16ffe-77e9-4848-b480-217d24d75387": ("industry_momentum", INDUSTRY_MOMENTUM_WIKI),
    "17f64a5c-2ac4-45ce-a749-845160ec21cf": ("trend", TREND_WIKI),
    "76e13803-501e-436e-8086-c41c28f81d17": ("momentum", None),   # existing wiki -> append
    "7a424fef-4cf9-40e7-bffe-9fb9989e9a24": ("value", None),      # FF (1992) cross-section
    "58f71324-cc9c-4048-95cb-78c877b1a7bc": ("size", None),       # Banz (1981)
}


def get_wiki(pid):
    req = urllib.request.Request(
        f"{URL}/rest/v1/papers?select=wiki_markdown&id=eq.{pid}",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"})
    rows = json.loads(urllib.request.urlopen(req).read())
    return rows[0]["wiki_markdown"] if rows else None


def patch(pid, markdown):
    body = json.dumps({
        "wiki_markdown": markdown,
        "wiki_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }).encode()
    req = urllib.request.Request(
        f"{URL}/rest/v1/papers?id=eq.{pid}", data=body, method="PATCH",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}",
                 "Content-Type": "application/json", "Prefer": "return=minimal"})
    urllib.request.urlopen(req).read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not URL or not KEY:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")

    for pid, (name, full) in TARGETS.items():
        section = exec_section(name)
        if full:
            markdown = full.rstrip() + "\n\n" + section
            action = "author full wiki + exec section"
        else:
            existing = get_wiki(pid) or ""
            if "## Executable replication on ConvexPi" in existing:
                print(f"[skip] {name}: already has exec section")
                continue
            markdown = existing.rstrip() + "\n\n" + section
            action = "append exec section to existing wiki"
        print(f"[{name}] {action} ({len(markdown)} chars)")
        if not args.dry_run:
            patch(pid, markdown)
    print("\n(dry run)" if args.dry_run else "\nDone.")


if __name__ == "__main__":
    main()
