# Streaming observations only; the trusted worker owns scoring and the market.
inp <- file('stdin', 'r')
out <- file('/dev/stdout', 'w')
sink(stderr())  # user diagnostics must not corrupt the decision stream
source('/submission/strategy.R', local = globalenv())
stopifnot(is.function(on_day))
writeLines('ready', out); flush(out)
vec <- function() scan(text=readLines(inp, n=1), sep=',', quiet=TRUE)
repeat {
  day <- readLines(inp, n=1)
  if (!length(day)) break
  prices <- vec(); portfolio <- vec()
  n <- as.integer(readLines(inp, n=1))
  features <- list()
  for (i in seq_len(n)) {
    name <- readLines(inp, n=1)
    features[[name]] <- vec()
  }
  w <- as.numeric(on_day(as.integer(day), features, prices, portfolio))
  writeLines(paste(format(w, digits=17, scientific=TRUE, trim=TRUE), collapse=','), out)
  flush(out)
}
