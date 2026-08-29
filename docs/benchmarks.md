# Benchmarks

An MT103 carries **exactly one** customer credit transfer. `parse_mt103`
says so and returns a one-element list to match. That single fact decides
the shape of this benchmark.

## There is no batch axis

The obvious benchmark for a loader is throughput as the input grows. Here
that measures nothing, and measures it misleadingly.

Concatenating two MT103s and parsing the result returns **one** record.
The second message is not rejected and no error is raised — it is simply
not there. A curve built that way shows per-message cost falling as the
file grows, which looks like excellent batching and is the opposite: the
cost falls because it is being divided by messages that were never
parsed.

So a migration reading a file of MT103s has to split it into messages
itself and call this once per message. The benchmark asserts this rather
than only describing it: if the loader ever grows multi-message support,
the output says the framing needs revisiting.

## What it measures

```sh
python benches/bench_parse_mt103.py           # full run
python benches/bench_parse_mt103.py --quick   # what CI runs
python benches/bench_parse_mt103.py --json    # machine-readable
```

| case | cost |
| :--- | ---: |
| complete message | ~6.2 µs |
| block-4 envelope (`{4:...-}`) | ~7.3 µs |
| rejected (bad `:32A:`) | ~3.2 µs |

Roughly **150,000–165,000 messages/second**, one call per message.

**Real SWIFT traffic arrives in a block-4 envelope**, so that form is
measured separately; unwrapping it costs about a microsecond more.

**Refusal is cheaper than success.** The mandatory-field check fails
before the field parsers run. A migration exists largely because there
are malformed messages to find, so it meets the rejection path often —
and that is the right way round for it to be the fast one.

## Not a gate

CI runs `--quick`, but not as a timing gate: wall-clock is not comparable
between runners, and a flaky performance gate teaches people to ignore
red. It runs so a benchmark that has stopped compiling against the
current API fails the build rather than rotting into a file that reads as
verified and is not.
