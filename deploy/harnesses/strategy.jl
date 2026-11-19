using Statistics, LinearAlgebra
wire = stdout
redirect_stdout(stderr) do
    include("/submission/strategy.jl")
end
println(wire, "ready"); flush(wire)
vecin() = parse.(Float64, split(readline(stdin), ','))
while !eof(stdin)
    day = parse(Int, readline(stdin))
    prices = vecin(); portfolio = vecin()
    n = parse(Int, readline(stdin))
    features = Dict{String,Vector{Float64}}()
    for _ in 1:n
        name = readline(stdin)
        features[name] = vecin()
    end
    w = redirect_stdout(stderr) do
        Float64.(on_day(day, features, prices, portfolio))
    end
    println(wire, join(w, ',')); flush(wire)
end
