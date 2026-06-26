# Example posts

Well-developed, gradable example posts for the ConvexPi showcase — copy their structure for your own.
Each tells a story, defines a `MyStrategy(Strategy)` (so it's leaderboard-eligible), and evaluates it
out of sample. All three are recognizable Quantopian-era strategies, recast on the Lab's synthetic
market.

| Notebook | Strategy |
|---|---|
| `multifactor_long_short.ipynb` | Dollar-neutral value + quality + momentum composite (the flagship long/short format) |
| `short_term_reversal.ipynb` | Weekly mean reversion — long recent losers, short recent winners |
| `low_volatility.ipynb` | Betting against volatility — long low-vol, short high-vol |

Publish any of them at **convexpi.ai/projects/new** by pasting its GitHub URL. Start your own from
[`../template`](../template).
