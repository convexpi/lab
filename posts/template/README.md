# ConvexPi post template

A **post** is a Jupyter notebook (Quarto `.qmd` coming later) that demonstrates a strategy or idea.
You keep it in your own GitHub repo — GitHub is the source of truth — and publish it on ConvexPi by
pasting the link. We pin it to a commit, **run it** in a sandbox, render it to a clean blog post, and
show it in the showcase where others can read, upvote, comment, and fork it.

## How to use this template

1. Copy `post.ipynb` into your repo and rename it.
2. Keep the **front-matter** as the first markdown cell:

   ```
   ---
   title: Your post title
   summary: One line shown in the gallery.
   tags: [momentum, equities]
   ---
   ```

3. Write your narrative + runnable code. Make it reproducible:
   - It will be executed top-to-bottom in a clean environment (numpy, pandas, matplotlib, the
     ConvexPi SDK, and a bundled offline dataset are available).
   - Each cell has a time limit; keep heavy compute modest.
   - Use `%matplotlib inline` so your charts are captured.
4. **Optional but encouraged:** define your strategy as a class named `MyStrategy`. Posts that do can
   be scored on the **permanent out-of-sample leaderboard** (we grade the strategy on hidden data —
   your own in-notebook numbers are for the story, the leaderboard number is computed by us).
5. Add an OSS license to your repo, then publish at **convexpi.ai/projects/new**.

## What makes a good post

- A clear question and an honest answer — including when the edge *doesn't* survive out of sample.
- Charts over tables; a short "what I'd try next" so others can fork and extend.
- Links to the paper (its wiki) or library replication you're building on.
