#!/usr/bin/env Rscript
# harness.R — run a student's R strategy over the exported synthetic market and emit a weights
# matrix. Scoring (returns, costs, Sharpe, overfitting, alphas) is done in Python so every language
# is graded identically; this only PRODUCES the weights, mirroring Backtest.run's normalization,
# rebalance cadence and portfolio carry exactly.
#
# Usage: Rscript harness.R <data_dir> <user_code.R> <out_weights.csv> <warmup> <rebalance_every>
# The student's file must define:  on_day <- function(day, features, prices, portfolio) { ...weights... }
#   day        integer, 0-based day index (matches the Python contract)
#   features   named list: feature_name -> numeric vector over stocks (today's cross-section)
#   prices     numeric vector of today's prices over stocks
#   portfolio  numeric vector of current weights before rebalancing
#   returns    numeric vector of target weights (length = number of stocks)

args <- commandArgs(trailingOnly = TRUE)
data_dir <- args[1]; user_path <- args[2]; out_path <- args[3]
warmup <- as.integer(args[4]); rebalance <- as.integer(args[5])

read_mat <- function(p) as.matrix(read.csv(p, header = FALSE))
prices <- read_mat(file.path(data_dir, "prices.csv"))
feat_files <- list.files(file.path(data_dir, "features"), pattern = "\\.csv$")
features_all <- list()
for (f in feat_files) features_all[[sub("\\.csv$", "", f)]] <- read_mat(file.path(data_dir, "features", f))

Tn <- nrow(prices); N <- ncol(prices)
source(user_path)
if (!exists("on_day") || !is.function(on_day))
  stop("Your code must define a function on_day(day, features, prices, portfolio)")

weights <- matrix(0, nrow = Tn, ncol = N)
portfolio <- rep(0, N)
# Python: for t in range(warmup, T-1)  (0-based). R rows are 1-based, so row = t + 1.
for (t0 in warmup:(Tn - 2)) {
  r <- t0 + 1L
  if ((t0 - warmup) %% rebalance == 0) {
    ft <- lapply(features_all, function(m) as.numeric(m[r, ]))
    new_w <- tryCatch(
      as.numeric(on_day(t0, ft, as.numeric(prices[r, ]), portfolio)),
      error = function(e) { message(sprintf("[day %d] strategy error: %s", t0, conditionMessage(e))); portfolio }
    )
    new_w[!is.finite(new_w)] <- 0                 # nan_to_num
    if (length(new_w) != N) new_w <- portfolio    # guard malformed output
    s <- sum(abs(new_w))
    if (s > 1) new_w <- new_w / s                 # normalize to gross leverage 1
  } else {
    new_w <- portfolio
  }
  portfolio <- new_w
  weights[t0 + 2L, ] <- new_w                     # Python weights_history[t+1]
}

write.table(weights, out_path, sep = ",", row.names = FALSE, col.names = FALSE)
