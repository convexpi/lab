#!/usr/bin/env julia
# harness.jl — run a student's Julia strategy over the exported synthetic market and emit a weights
# matrix. Scoring (Sharpe, costs, overfitting, alphas) is done in Python so every language is graded
# identically; this only PRODUCES the weights, mirroring Backtest.run's normalization, rebalance
# cadence and portfolio carry exactly.
#
# Usage: julia harness.jl <data_dir> <user_code.jl> <out_weights.csv> <warmup> <rebalance_every>
# The student's file must define:  on_day(day, features, prices, portfolio) -> Vector
#   day        Int, 0-based day index (matches the Python contract)
#   features   Dict{String,Vector} : feature_name -> today's cross-section over stocks
#   prices     Vector of today's prices over stocks
#   portfolio  Vector of current weights before rebalancing
#   returns    Vector of target weights (length = number of stocks)
using DelimitedFiles

data_dir, user_path, out_path = ARGS[1], ARGS[2], ARGS[3]
warmup = parse(Int, ARGS[4]); rebalance = parse(Int, ARGS[5])

readmat(p) = readdlm(p, ',', Float64)
prices = readmat(joinpath(data_dir, "prices.csv"))
features_all = Dict{String,Matrix{Float64}}()
for f in readdir(joinpath(data_dir, "features"))
    endswith(f, ".csv") || continue
    features_all[replace(f, r"\.csv$" => "")] = readmat(joinpath(data_dir, "features", f))
end

T, N = size(prices)
include(user_path)
@assert isdefined(Main, :on_day) "Your code must define on_day(day, features, prices, portfolio)"

weights = zeros(Float64, T, N)
portfolio = zeros(Float64, N)
# Python: for t in range(warmup, T-1)  (0-based). Julia rows are 1-based, so row = t + 1.
for t0 in warmup:(T - 2)
    r = t0 + 1
    new_w = copy(portfolio)
    if (t0 - warmup) % rebalance == 0
        ft = Dict(nm => vec(m[r, :]) for (nm, m) in features_all)
        try
            new_w = Float64.(on_day(t0, ft, vec(prices[r, :]), copy(portfolio)))
        catch e
            @warn "strategy error" day = t0 err = e
            new_w = copy(portfolio)
        end
        new_w[.!isfinite.(new_w)] .= 0.0            # nan_to_num
        if length(new_w) != N
            new_w = copy(portfolio)                 # guard malformed output
        end
        s = sum(abs.(new_w))
        if s > 1
            new_w = new_w ./ s                      # normalize to gross leverage 1
        end
    end
    global portfolio = new_w
    weights[t0 + 2, :] = new_w                      # Python weights_history[t+1]
end

writedlm(out_path, weights, ',')
